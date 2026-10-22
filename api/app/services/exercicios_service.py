"""Biblioteca de exercícios da academia e previsão da carga de uma sessão.

Cada exercício tem a carga típica POR MINUTO (por jogador): a mediana das
vezes em que foi registado no GPS (folha de exercícios importada, tabela
exercises), ou, sem GPS, os valores escritos à mão. Planear uma sessão =
escolher exercícios e minutos; a carga prevista é a soma de (por minuto × minutos).
"""
from __future__ import annotations

import re
import statistics
import unicodedata
from datetime import date

from app.core.db import get_conn

CATEGORIAS = ["Aquecimento", "Rondo", "Posse", "Jogo reduzido", "Jogo condicionado", "Finalização",
              "Transições", "Bolas paradas", "Físico / velocidade", "Prevenção", "Recuperação", "Outro"]
# chave → (coluna na tabela exercises, rótulo, unidade)
METRICAS = {
    "distancia": ("distancia_total_m", "Distância", "m"),
    "hsr": ("hsr_m", "HSR", "m"),
    "sprint": ("sprint_m", "Sprint", "m"),
    "acc": ("acc_n", "Acelerações", "n"),
    "dcc": ("dcc_n", "Desacelerações", "n"),
}
MSG_MIGRACAO = "A biblioteca de exercícios precisa da migração 0019 — é aplicada automaticamente no próximo deploy."


# ── Cálculos puros ───────────────────────────────────────────────────────────
def chave_nome(nome: str | None) -> str:
    """Nome normalizado para ligar a biblioteca aos registos do GPS."""
    s = unicodedata.normalize("NFKD", str(nome or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def estatisticas_gps(registos: list[dict]) -> dict:
    """Registos de um exercício (cada um: duracao_min, métricas, data, pse) →
    n, última data, duração mediana e mediana por minuto de cada métrica."""
    validos = [r for r in registos if r.get("duracao_min") and float(r["duracao_min"]) > 0]
    if not validos:
        return {"n": 0}
    por_min = {}
    for k, (col, _, _) in METRICAS.items():
        vals = [float(r[col]) / float(r["duracao_min"]) for r in validos if r.get(col) is not None]
        if vals:
            por_min[k] = round(statistics.median(vals), 2)
    pses = [float(r["pse"]) for r in validos if r.get("pse") is not None]
    datas = [r["data"] for r in validos if r.get("data")]
    return {
        "n": len(validos),
        "ultima": max(datas).isoformat() if datas else None,
        "duracao_min": round(statistics.median(float(r["duracao_min"]) for r in validos), 0),
        "por_min": por_min,
        "pse": round(statistics.median(pses), 1) if pses else None,
    }


def por_minuto_efetivo(gps: dict | None, manual: dict | None) -> tuple[dict, str | None]:
    """Valores por minuto usados na previsão: GPS se houver, senão os manuais."""
    if gps and gps.get("n") and gps.get("por_min"):
        return gps["por_min"], "gps"
    manual = {k: float(v) for k, v in (manual or {}).items() if k in METRICAS and v not in (None, "")}
    return (manual, "manual") if manual else ({}, None)


def prever(itens: list[dict], biblioteca: dict[str, dict]) -> dict:
    """Carga prevista por jogador de uma lista [{nome|id, minutos}]."""
    total = {k: 0.0 for k in METRICAS}
    sem_dados = []
    minutos = 0
    for it in itens:
        ex = biblioteca.get(it.get("id") or "") or biblioteca.get(chave_nome(it.get("nome")))
        mins = float(it.get("minutos") or 0)
        minutos += mins
        if not ex or not ex.get("por_min"):
            sem_dados.append(it.get("nome") or "?")
            continue
        for k, v in ex["por_min"].items():
            total[k] += v * mins
    return {"minutos": round(minutos), "carga": {k: round(v, 0) for k, v in total.items()}, "sem_dados": sem_dados}


# ── Base de dados ────────────────────────────────────────────────────────────
def disponivel() -> bool:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.exercicios_biblioteca') is not null")
                return bool(cur.fetchone()[0])
    except Exception:
        return False


def _academia(cur, user_id: str) -> str:
    cur.execute("select academia_id::text from academia_membros where user_id = %s order by academia_id limit 1", (user_id,))
    r = cur.fetchone()
    if not r:
        raise PermissionError("Ainda não pertences a nenhuma academia.")
    return r[0]


def _equipas_da_academia(cur, academia_id: str) -> list[str]:
    cur.execute("select id::text from teams where academia_id = %s", (academia_id,))
    return [r[0] for r in cur.fetchall()]


def _registos_gps(cur, team_ids: list[str]) -> dict[str, dict]:
    """{chave_nome: {"nome", "categoria", "registos": [...]}} dos exercícios do GPS."""
    if not team_ids:
        return {}
    cur.execute(
        """select exercicio, categoria, data, duracao_min::float, distancia_total_m::float, hsr_m::float, sprint_m::float,
                  acc_n::float, dcc_n::float, pse_exercicio::float
           from exercises where team_id = any(%s::uuid[]) and exercicio is not null""",
        (team_ids,),
    )
    out: dict[str, dict] = {}
    for nome, cat, d, dur, dist, hsr, spr, acc, dcc, pse in cur.fetchall():
        k = chave_nome(nome)
        if not k:
            continue
        g = out.setdefault(k, {"nome": str(nome).strip(), "categorias": [], "registos": []})
        if cat:
            g["categorias"].append(cat)
        g["registos"].append({"data": d, "duracao_min": dur, "distancia_total_m": dist, "hsr_m": hsr,
                              "sprint_m": spr, "acc_n": acc, "dcc_n": dcc, "pse": pse})
    return out


def _biblioteca(cur, academia_id: str, team_ids: list[str]) -> list[dict]:
    cur.execute(
        """select id::text, nome, categoria, descricao, formato, espaco, duracao_min, manual, atualizado_em
           from exercicios_biblioteca where academia_id = %s order by lower(nome)""",
        (academia_id,),
    )
    guardados = cur.fetchall()
    gps = _registos_gps(cur, team_ids)
    lista = []
    vistos = set()
    for i, nome, cat, desc, fmt, esp, dur, manual, _ in guardados:
        k = chave_nome(nome)
        vistos.add(k)
        g = gps.get(k)
        est = estatisticas_gps(g["registos"]) if g else {"n": 0}
        pm, fonte = por_minuto_efetivo(est, manual)
        lista.append({"id": i, "nome": nome, "categoria": cat, "descricao": desc, "formato": fmt, "espaco": esp,
                      "duracao_min": dur, "manual": manual or {}, "gps": est, "por_min": pm, "fonte": fonte, "guardado": True})
    for k, g in gps.items():
        if k in vistos:
            continue
        est = estatisticas_gps(g["registos"])
        cat = statistics.mode(g["categorias"]) if g["categorias"] else None
        lista.append({"id": None, "nome": g["nome"], "categoria": cat if cat in CATEGORIAS else None, "descricao": None,
                      "formato": None, "espaco": None, "duracao_min": None, "manual": {}, "gps": est,
                      "por_min": est.get("por_min", {}), "fonte": "gps" if est.get("n") else None, "guardado": False})
    lista.sort(key=lambda x: (not x["guardado"], chave_nome(x["nome"])))
    return lista


def listar(user_id: str, team_id: str | None = None) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            academia_id = _academia(cur, user_id)
            equipas = _equipas_da_academia(cur, academia_id)
            if team_id:
                if team_id not in equipas:
                    raise PermissionError("Esta equipa não pertence à tua academia.")
                equipas = [team_id]
            lista = _biblioteca(cur, academia_id, equipas)
    return {"disponivel": True, "categorias": CATEGORIAS,
            "metricas": [{"chave": k, "label": l, "unidade": u} for k, (_, l, u) in METRICAS.items()],
            "exercicios": lista}


def _validar(dados: dict) -> dict:
    nome = (dados.get("nome") or "").strip()
    if not nome:
        raise ValueError("Indica o nome do exercício.")
    cat = (dados.get("categoria") or "").strip() or None
    if cat and cat not in CATEGORIAS:
        raise ValueError("Categoria inválida.")
    dur = dados.get("duracao_min")
    dur = int(dur) if dur not in (None, "") else None
    if dur is not None and not 1 <= dur <= 180:
        raise ValueError("A duração vai de 1 a 180 minutos.")
    manual = {}
    for k, v in (dados.get("manual") or {}).items():
        if k in METRICAS and v not in (None, ""):
            f = float(v)
            if f < 0 or f > 500:
                raise ValueError("Os valores por minuto têm de estar entre 0 e 500.")
            manual[k] = round(f, 2)
    txt = lambda c, n: ((dados.get(c) or "").strip()[:n] or None)
    return {"nome": nome[:80], "categoria": cat, "descricao": txt("descricao", 600), "formato": txt("formato", 40),
            "espaco": txt("espaco", 40), "duracao_min": dur, "manual": manual}


def criar(user_id: str, dados: dict) -> dict:
    import json

    import psycopg2

    d = _validar(dados)
    with get_conn() as conn:
        with conn.cursor() as cur:
            academia_id = _academia(cur, user_id)
            try:
                cur.execute(
                    """insert into exercicios_biblioteca (academia_id, nome, categoria, descricao, formato, espaco, duracao_min, manual, criado_por)
                       values (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s) returning id::text""",
                    (academia_id, d["nome"], d["categoria"], d["descricao"], d["formato"], d["espaco"], d["duracao_min"],
                     json.dumps(d["manual"]), user_id),
                )
            except psycopg2.errors.UniqueViolation:
                raise ValueError(f"Já existe o exercício «{d['nome']}» na biblioteca.")
            return {"ok": True, "id": cur.fetchone()[0]}


def atualizar(user_id: str, ex_id: str, dados: dict) -> dict:
    import json

    import psycopg2

    d = _validar(dados)
    with get_conn() as conn:
        with conn.cursor() as cur:
            academia_id = _academia(cur, user_id)
            try:
                cur.execute(
                    """update exercicios_biblioteca set nome = %s, categoria = %s, descricao = %s, formato = %s, espaco = %s,
                              duracao_min = %s, manual = %s::jsonb, atualizado_em = now()
                       where id = %s and academia_id = %s returning id""",
                    (d["nome"], d["categoria"], d["descricao"], d["formato"], d["espaco"], d["duracao_min"],
                     json.dumps(d["manual"]), ex_id, academia_id),
                )
            except psycopg2.errors.UniqueViolation:
                raise ValueError(f"Já existe o exercício «{d['nome']}» na biblioteca.")
            if not cur.fetchone():
                raise PermissionError("Exercício não encontrado.")
    return {"ok": True}


def apagar(user_id: str, ex_id: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            academia_id = _academia(cur, user_id)
            cur.execute("delete from exercicios_biblioteca where id = %s and academia_id = %s returning id", (ex_id, academia_id))
            if not cur.fetchone():
                raise PermissionError("Exercício não encontrado.")
    return {"ok": True}


def mapa_para_previsao(user_id: str, team_id: str) -> dict[str, dict]:
    """{id ou chave_nome: exercício} para prever a carga das sessões de uma equipa."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            academia_id = _academia(cur, user_id)
            lista = _biblioteca(cur, academia_id, _equipas_da_academia(cur, academia_id))
    out = {}
    for e in lista:
        out[chave_nome(e["nome"])] = e
        if e["id"]:
            out[e["id"]] = e
    return out


__all__ = ["CATEGORIAS", "listar", "criar", "atualizar", "apagar", "prever", "mapa_para_previsao", "date"]
