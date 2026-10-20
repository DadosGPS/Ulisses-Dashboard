"""Regresso ao jogo (return-to-play) — planos por etapas, avaliados
automaticamente a partir do GPS.

Cada etapa define metas POR SESSÃO em % da referência de jogo do jogador
ANTES da lesão (média por 90' dos últimos jogos completos — ver
referencia_jogo; a velocidade máxima usa o recorde pré-lesão). Uma etapa fica
cumprida quando `sessoes_por_etapa` sessões, depois de concluída a anterior,
atingem TODAS as metas definidas dessa etapa. As etapas avançam por ordem:
uma sessão que já cumpriria uma etapa posterior só conta para a atual.
"""
from __future__ import annotations

import json

import pandas as pd

from app.core.db import get_conn
from app.services.referencia_jogo import mascara_jogo, referencias_jogo

METRICAS_RTP = [
    # chave na etapa, coluna, rótulo, é pico?
    ("pct_distancia", "Distância Total (m)", "Distância", False),
    ("pct_hsr", "HSR (m)", "HSR", False),
    ("pct_sprint", "Sprint (m)", "Sprint", False),
    ("pct_vmax", "Vel. Máx (km/h)", "Vel. máx", True),
]

# Progressão por omissão (editável em cada plano). Valores por sessão, em % da
# referência de jogo pré-lesão; None = esta métrica não é exigida na etapa.
ETAPAS_PADRAO = [
    {"nome": "Reintegração", "pct_distancia": 50, "pct_hsr": 30, "pct_sprint": None, "pct_vmax": None},
    {"nome": "Volume", "pct_distancia": 75, "pct_hsr": 50, "pct_sprint": 30, "pct_vmax": 80},
    {"nome": "Intensidade", "pct_distancia": 90, "pct_hsr": 75, "pct_sprint": 60, "pct_vmax": 90},
    {"nome": "Exigência de jogo", "pct_distancia": 100, "pct_hsr": 100, "pct_sprint": 90, "pct_vmax": 95},
]
SESSOES_POR_ETAPA = 2

MSG_MIGRACAO = (
    "A tabela dos planos de regresso ao jogo ainda não existe. Aplica a migração "
    "supabase/migrations/0007_planos_rtp.sql no SQL Editor do Supabase."
)


def _limpar_etapas(etapas: list[dict] | None) -> list[dict]:
    limpas = []
    for i, e in enumerate(etapas or []):
        nova = {"nome": str(e.get("nome") or f"Etapa {i + 1}")[:60]}
        for chave, *_ in METRICAS_RTP:
            v = e.get(chave)
            try:
                nova[chave] = None if v in (None, "") else max(0.0, min(200.0, float(v)))
            except (TypeError, ValueError):
                nova[chave] = None
        if e.get("notas"):
            nova["notas"] = str(e["notas"])[:300]
        limpas.append(nova)
    return limpas


def _referencias_pre_lesao(df: pd.DataFrame, jogador: str, inicio: pd.Timestamp) -> dict[str, dict]:
    """Referência de jogo de cada métrica com os dados ANTERIORES ao início do
    plano (jogador sem jogos completos → mediana da posição)."""
    antes = df[df["Data"] < inicio]
    jogos = antes[mascara_jogo(antes)]
    pos = antes.loc[antes["Jogador"] == jogador, "Posição"].dropna() if "Posição" in antes.columns else pd.Series(dtype=object)
    alvo = {jogador: pos.iloc[-1] if not pos.empty and isinstance(pos.iloc[-1], str) else ""}
    refs: dict[str, dict] = {}
    for chave, col, _, pico in METRICAS_RTP:
        if col not in antes.columns:
            continue
        if pico:  # recorde pré-lesão em qualquer sessão
            serie = antes.loc[antes["Jogador"] == jogador, col].dropna()
            if not serie.empty and serie.max() > 0:
                refs[chave] = {"valor": float(serie.max()), "fonte": "recorde"}
            continue
        r = referencias_jogo(jogos, col, jogadores=alvo).get(jogador)
        if r and r["valor"] > 0:
            refs[chave] = {"valor": r["valor"], "fonte": r["fonte"]}
    return refs


def avaliar_plano(df: pd.DataFrame, jogador: str, data_inicio: str, etapas: list[dict],
                  sessoes_por_etapa: int = SESSOES_POR_ETAPA) -> dict:
    """Parte pura (testável): progresso do plano a partir das sessões."""
    etapas = _limpar_etapas(etapas)
    vazio_ref = {"referencias": {}, "sessoes": [], "etapas": [], "etapa_atual": None, "concluido": False, "progresso_pct": 0}
    if df is None or df.empty or "Jogador" not in df.columns or not etapas:
        return {**vazio_ref, "etapas": [{**e, "estado": "pendente"} for e in etapas]}
    df = df.copy()
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    inicio = pd.Timestamp(data_inicio)
    refs = _referencias_pre_lesao(df, jogador, inicio)

    sess = df[(df["Jogador"] == jogador) & (df["Data"] >= inicio)].sort_values("Data")
    cols = [c for _, c, _, _ in METRICAS_RTP if c in sess.columns]
    if cols:
        sess = sess.dropna(subset=cols, how="all")
    e_jogo = mascara_jogo(sess) if not sess.empty else pd.Series(dtype=bool)

    def pcts(row) -> dict[str, float | None]:
        out = {}
        for chave, col, _, _ in METRICAS_RTP:
            ref = refs.get(chave)
            v = row.get(col)
            out[chave] = round(float(v) / ref["valor"] * 100, 0) if ref and pd.notna(v) else None
        return out

    def cumpre(p: dict, etapa: dict) -> bool:
        metas = [(k, etapa[k]) for k, *_ in METRICAS_RTP if etapa.get(k) is not None]
        return bool(metas) and all(p.get(k) is not None and p[k] >= meta for k, meta in metas)

    estado_etapas = [{**e, "estado": "pendente", "sessoes_cumpridas": 0, "data_conclusao": None,
                      "melhor": {k: None for k, *_ in METRICAS_RTP}} for e in etapas]
    atual = 0
    lista_sessoes = []
    for idx, row in sess.iterrows():
        p = pcts(row)
        etapa_sessao = None
        if atual < len(estado_etapas):
            e = estado_etapas[atual]
            for k in p:
                if p[k] is not None and (e["melhor"][k] is None or p[k] > e["melhor"][k]):
                    e["melhor"][k] = p[k]
            if cumpre(p, e):
                e["sessoes_cumpridas"] += 1
                etapa_sessao = atual
                if e["sessoes_cumpridas"] >= max(1, int(sessoes_por_etapa)):
                    e["estado"] = "concluida"
                    e["data_conclusao"] = row["Data"].strftime("%Y-%m-%d")
                    atual += 1
        lista_sessoes.append({
            "data": row["Data"].strftime("%Y-%m-%d"),
            "dia_md": row.get("Dia MD") if isinstance(row.get("Dia MD"), str) else None,
            "jogo": bool(e_jogo.loc[idx]) if idx in e_jogo.index else False,
            "pct": p,
            "conta_para_etapa": etapa_sessao + 1 if etapa_sessao is not None else None,
        })
    if atual < len(estado_etapas):
        estado_etapas[atual]["estado"] = "atual"

    n = len(estado_etapas)
    progresso = (atual + (estado_etapas[atual]["sessoes_cumpridas"] / max(1, sessoes_por_etapa) if atual < n else 0)) / n * 100
    return {
        "referencias": {k: {"valor": round(r["valor"], 1), "fonte": r["fonte"]} for k, r in refs.items()},
        "sessoes": lista_sessoes[-12:][::-1],
        "etapas": estado_etapas,
        "etapa_atual": atual + 1 if atual < n else None,
        "concluido": atual >= n,
        "progresso_pct": round(progresso, 0),
    }


# ── Persistência ─────────────────────────────────────────────────────────────
def _tabela_existe() -> bool:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.planos_rtp')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


def listar_planos(team_id: str) -> dict:
    from app.services.dados_equipa import carregar_df_equipa
    from app.services.estado_service import listar_estados

    jogadores = [j for j in listar_estados(team_id) if j.get("ativo")]
    base = {
        "etapas_padrao": ETAPAS_PADRAO,
        "sessoes_por_etapa_padrao": SESSOES_POR_ETAPA,
        "metricas": [{"chave": k, "label": l} for k, _, l, _ in METRICAS_RTP],
        "jogadores": [{"player_id": j["player_id"], "nome": j["nome"], "estado": j["estado"],
                       "estado_desde": j["estado_desde"]} for j in jogadores],
    }
    if not _tabela_existe():
        return {**base, "disponivel": False, "motivo": MSG_MIGRACAO, "planos": [], "sugestoes": []}

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select r.id, r.player_id, p.nome, r.lesao_id, r.data_inicio, r.etapas,
                       r.sessoes_por_etapa, r.estado, r.notas
                from planos_rtp r join players p on p.id = r.player_id
                where r.team_id = %s and r.estado <> 'cancelado'
                order by (r.estado = 'ativo') desc, r.data_inicio desc
                """,
                (team_id,),
            )
            linhas = cur.fetchall()

    df = carregar_df_equipa(team_id)
    planos = []
    for (pid, player_id, nome, lesao_id, inicio, etapas, n_sess, estado, notas) in linhas:
        etapas = etapas if isinstance(etapas, list) else json.loads(etapas or "[]")
        avaliacao = avaliar_plano(df, nome, inicio.isoformat(), etapas, n_sess)
        planos.append({
            "id": str(pid), "player_id": str(player_id), "jogador": nome,
            "lesao_id": str(lesao_id) if lesao_id else None,
            "data_inicio": inicio.isoformat(), "sessoes_por_etapa": n_sess,
            "estado": estado, "notas": notas, **avaliacao,
        })
    com_plano = {p["player_id"] for p in planos if p["estado"] == "ativo"}
    sugestoes = [j for j in base["jogadores"] if j["estado"] in ("em_recuperacao", "lesionado") and j["player_id"] not in com_plano]
    return {**base, "disponivel": True, "motivo": None, "planos": planos, "sugestoes": sugestoes}


def criar_plano(team_id: str, player_id: str, data_inicio: str, etapas: list[dict] | None,
                sessoes_por_etapa: int | None, lesao_id: str | None, notas: str | None) -> dict:
    if not _tabela_existe():
        return {"ok": False, "erro": MSG_MIGRACAO}
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into planos_rtp (team_id, player_id, lesao_id, data_inicio, etapas, sessoes_por_etapa, notas)
                select %s, p.id, %s, %s, %s::jsonb, %s, %s from players p where p.id = %s and p.team_id = %s
                returning id
                """,
                (team_id, lesao_id or None, data_inicio, json.dumps(_limpar_etapas(etapas or ETAPAS_PADRAO)),
                 int(sessoes_por_etapa or SESSOES_POR_ETAPA), notas, player_id, team_id),
            )
            row = cur.fetchone()
    return {"ok": bool(row), "id": str(row[0]) if row else None}


def atualizar_plano(team_id: str, plano_id: str, etapas: list[dict] | None = None,
                    sessoes_por_etapa: int | None = None, estado: str | None = None,
                    notas: str | None = None, data_inicio: str | None = None) -> dict:
    if not _tabela_existe():
        return {"ok": False, "erro": MSG_MIGRACAO}
    if estado is not None and estado not in ("ativo", "concluido", "cancelado"):
        return {"ok": False, "erro": "Estado inválido."}
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update planos_rtp set
                    etapas = coalesce(%s::jsonb, etapas),
                    sessoes_por_etapa = coalesce(%s, sessoes_por_etapa),
                    estado = coalesce(%s, estado),
                    notas = coalesce(%s, notas),
                    data_inicio = coalesce(%s::date, data_inicio),
                    atualizado_em = now()
                where id = %s and team_id = %s
                returning id
                """,
                (json.dumps(_limpar_etapas(etapas)) if etapas is not None else None,
                 int(sessoes_por_etapa) if sessoes_por_etapa else None, estado, notas, data_inicio or None,
                 plano_id, team_id),
            )
            row = cur.fetchone()
    return {"ok": bool(row)}
