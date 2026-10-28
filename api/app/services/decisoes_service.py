"""Registo de decisões do staff face aos sinais (ver alertas_service).

Para cada sinal de um jogador num dia, o preparador físico regista o que fez:
reduzir a carga, ajustar o plano, manter, ou ignorar o aviso. Uma decisão por
jogador, dia e sinal (registar de novo substitui).

O resumo responde à pergunta que dá sentido aos alertas: «quando a app avisou,
o que fizemos, e o que aconteceu a seguir?». Por sinal: quantas decisões de
cada tipo, quantas vezes o jogador teve uma lesão nos SEGUIMENTO_DIAS dias
seguintes e quantas vezes o mesmo sinal voltou a ser decidido nesse período.
É descritivo (poucos casos, sem grupo de controlo), mas é o que permite, com
o tempo, ver se um limiar avisa demasiado ou de menos.
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta

import pandas as pd

from app.core.db import get_conn

DECISOES = ("reduzir", "ajustar", "manter", "ignorar")
SEGUIMENTO_DIAS = 14
MSG_MIGRACAO = (
    "O registo de decisões precisa da migração supabase/migrations/0021_decisoes.sql "
    "(aplica-se sozinha no próximo deploy, ou no SQL Editor do Supabase)."
)
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def disponivel() -> bool:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.decisoes') is not null")
                return bool(cur.fetchone()[0])
    except Exception:
        return False


def registar(team_id: str, user_id: str | None, jogador: str, player_id: str | None, dia: str,
             sinal: str, decisao: str, detalhe: dict | None = None, nota: str | None = None) -> dict:
    if decisao not in DECISOES:
        raise ValueError(f"Decisão inválida: use {', '.join(DECISOES)}.")
    if not jogador or not sinal:
        raise ValueError("Falta o jogador ou o sinal.")
    pid = player_id if player_id and _UUID.match(player_id) else None
    nota = (nota or "").strip()[:500] or None
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into decisoes (team_id, player_id, jogador, data, sinal, detalhe, decisao, nota, criado_por)
                values (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                on conflict (team_id, jogador, data, sinal) do update set
                    decisao = excluded.decisao, nota = excluded.nota, detalhe = excluded.detalhe,
                    criado_por = excluded.criado_por, criado_em = now()
                returning id
                """,
                (team_id, pid, jogador, dia, sinal, json.dumps(detalhe or {}, default=str), decisao, nota, user_id),
            )
            return {"id": str(cur.fetchone()[0]), "decisao": decisao}


def apagar(team_id: str, decisao_id: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("delete from decisoes where id = %s and team_id = %s", (decisao_id, team_id))
            return {"removidas": cur.rowcount}


def _ler(team_id: str, desde: date | None) -> pd.DataFrame:
    cols = ["id", "jogador", "player_id", "data", "sinal", "decisao", "nota", "detalhe", "criado_em"]
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"select {', '.join(cols)} from decisoes where team_id = %s and (%s::date is null or data >= %s::date) order by data desc, jogador",
                (team_id, desde, desde),
            )
            return pd.DataFrame(cur.fetchall(), columns=cols)


def listar(team_id: str, desde: str | None = None) -> dict:
    if not disponivel():
        return {"disponivel": False, "motivo": MSG_MIGRACAO, "decisoes": []}
    df = _ler(team_id, date.fromisoformat(desde) if desde else None)
    out = []
    for r in df.itertuples(index=False):
        out.append({"id": str(r.id), "jogador": r.jogador, "player_id": str(r.player_id) if r.player_id else None,
                    "data": r.data.isoformat(), "sinal": r.sinal, "decisao": r.decisao, "nota": r.nota,
                    "acao": (r.detalhe or {}).get("acao") if isinstance(r.detalhe, dict) else None})
    return {"disponivel": True, "motivo": None, "decisoes": out}


# ── Resumo (parte pura, testável) ────────────────────────────────────────────
def resumir(decisoes: pd.DataFrame, lesoes: pd.DataFrame, hoje: date, dias: int = SEGUIMENTO_DIAS) -> dict:
    """`decisoes`: jogador, data, sinal, decisao. `lesoes`: jogador, data_inicio.

    Só entram no seguimento as decisões com pelo menos `dias` dias (antes disso
    ainda não se sabe o que aconteceu); as mais recentes contam como «em curso».
    """
    vazio = {"seguimento_dias": dias, "total": 0, "sinais": []}
    if decisoes is None or decisoes.empty:
        return vazio
    d = decisoes.copy()
    d["data"] = pd.to_datetime(d["data"]).dt.date
    les = lesoes.copy() if lesoes is not None and not lesoes.empty else pd.DataFrame(columns=["jogador", "data_inicio"])
    les["data_inicio"] = pd.to_datetime(les["data_inicio"]).dt.date
    lesoes_por = {j: sorted(g["data_inicio"]) for j, g in les.groupby("jogador")}

    linhas = []
    for sinal, g in d.groupby("sinal"):
        por_decisao = {k: int((g["decisao"] == k).sum()) for k in DECISOES}
        fechadas = g[g["data"] <= hoje - timedelta(days=dias)]
        com_lesao = 0
        repetido = 0
        por_decisao_lesao = {k: 0 for k in DECISOES}
        for r in fechadas.itertuples(index=False):
            fim = r.data + timedelta(days=dias)
            if any(r.data < x <= fim for x in lesoes_por.get(r.jogador, [])):
                com_lesao += 1
                por_decisao_lesao[r.decisao] += 1
            mesmos = g[(g["jogador"] == r.jogador) & (g["data"] > r.data) & (g["data"] <= fim)]
            if not mesmos.empty:
                repetido += 1
        linhas.append({
            "sinal": sinal, "n": int(len(g)), "por_decisao": por_decisao,
            "em_seguimento": int(len(g) - len(fechadas)), "fechadas": int(len(fechadas)),
            "lesao_seguinte": com_lesao, "lesao_por_decisao": por_decisao_lesao, "repetido": repetido,
        })
    linhas.sort(key=lambda x: -x["n"])
    return {"seguimento_dias": dias, "total": int(len(d)), "sinais": linhas}


# ── Calibração dos limiares com os dados do clube ────────────────────────────
# Sinal → (limiar que o controla, passo, sentido que torna o aviso mais raro,
# nome para o staff). Um aviso que o staff ignora quase sempre, sem lesões a
# seguir, está a gastar atenção: sugere-se torná-lo mais raro. Um aviso que,
# quando ignorado, foi seguido de lesões, sugere-se manter (ou apertar).
LIMIAR_DO_SINAL = {
    "acwr": ("acwr_alto", 0.1, +1, "ACWR (atenção)"),
    "hsr_baixo": ("hsr_semana_baixo", 0.05, -1, "HSR semana — baixo"),
    "sprint_baixo": ("sprint_semana_baixo", 0.05, -1, "Sprint semana — baixo"),
    "hsr_alto": ("hsr_semana_alto", 0.05, +1, "HSR semana — elevado"),
    "sprint_alto": ("sprint_semana_alto", 0.05, +1, "Sprint semana — elevado"),
    "hooper": ("hooper_subida_alto", 1.0, +1, "Subida do Hooper (atenção)"),
    "cmj": ("cmj_queda_alto", 1.0, +1, "Queda do CMJ (atenção)"),
    "vmax": ("velocidade_queda_sustentada", 2.0, +1, "Velocidade abaixo do recorde"),
    "sem_dados": ("dias_sem_dados", 2.0, +1, "Dias sem dados"),
}
MIN_FECHADAS = 8
IGNORADO_ALTO = 0.7


def sugerir(linha: dict, limites: dict) -> dict | None:
    """Sugestão de calibração para um sinal do resumo (ou None)."""
    regra = LIMIAR_DO_SINAL.get(linha["sinal"])
    if not regra or linha.get("fechadas", 0) < MIN_FECHADAS:
        return None
    chave, passo, sentido, nome = regra
    atual = limites.get(chave)
    if atual is None:
        return None
    n = linha["n"] or 1
    ignorado = linha["por_decisao"].get("ignorar", 0) + linha["por_decisao"].get("manter", 0)
    les_ign = linha.get("lesao_por_decisao", {}).get("ignorar", 0) + linha.get("lesao_por_decisao", {}).get("manter", 0)
    if ignorado / n >= IGNORADO_ALTO and linha.get("lesao_seguinte", 0) == 0:
        novo = round(atual + sentido * passo, 2)
        return {"tipo": "tornar_raro", "limiar": chave, "nome": nome, "atual": atual, "sugerido": novo,
                "texto": f"Mantido ou ignorado em {ignorado} de {n} vezes, sem lesões nos {SEGUIMENTO_DIAS} dias seguintes: "
                         f"experimentar {nome} de {atual:g} para {novo:g}."}
    if les_ign >= 2:
        return {"tipo": "levar_a_serio", "limiar": chave, "nome": nome, "atual": atual, "sugerido": atual,
                "texto": f"{les_ign} lesões nos {SEGUIMENTO_DIAS} dias seguintes depois de o aviso ser mantido ou ignorado: "
                         f"manter {nome} em {atual:g} e agir quando aparece."}
    return None


def obter_resumo(team_id: str, limites: dict | None = None) -> dict:
    if not disponivel():
        return {"disponivel": False, "motivo": MSG_MIGRACAO, "seguimento_dias": SEGUIMENTO_DIAS, "total": 0, "sinais": []}
    dec = _ler(team_id, None)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select p.nome, l.data_inicio from lesoes l join players p on p.id = l.player_id where l.team_id = %s",
                (team_id,),
            )
            les = pd.DataFrame(cur.fetchall(), columns=["jogador", "data_inicio"])
    out = resumir(dec, les, date.today())
    if limites:
        for linha in out["sinais"]:
            linha["sugestao"] = sugerir(linha, limites)
    return {"disponivel": True, "motivo": None, **out}
