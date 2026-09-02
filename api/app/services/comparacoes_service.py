"""Comparações — por posição e entre jogadores.

Reutiliza carregar_df_equipa() e as definições de métrica de carga externa,
acrescentando as métricas internas mais úteis para contexto. Base de cálculo:
média por jogador ao longo de toda a época (cada jogador pesa igual), o que
torna a comparação por posição justa independentemente de quantas sessões
cada um fez.
"""
from __future__ import annotations

import pandas as pd

from app.services.carga_externa_service import METRICAS
from app.services.dados_equipa import carregar_df_equipa

# Métricas internas incluídas para contexto (a carga externa continua a ser a
# protagonista, mas comparar sem carga interna esconde metade da história).
METRICAS_INTERNAS: list[dict] = [
    {"chave": "carga_interna", "col": "Carga Interna", "label": "Carga Interna", "unidade": "UA", "cor": "#e63946", "casas": 0, "peak": False},
    {"chave": "hooper_index",  "col": "Hooper Index",  "label": "Hooper",        "unidade": "",   "cor": "#3498db", "casas": 1, "peak": False},
]

TODAS = METRICAS + METRICAS_INTERNAS


def _num(v, casas: int) -> float | None:
    if v is None or pd.isna(v):
        return None
    return round(float(v), casas)


def _resumo_por_jogador(df: pd.DataFrame, metricas: list[dict]) -> list[dict]:
    """Média por jogador (época toda) de cada métrica disponível."""
    resumo = []
    for jogador, g in df.groupby("Jogador"):
        posicao = g["Posição"].dropna().iloc[0] if "Posição" in g.columns and g["Posição"].notna().any() else "—"
        valores: dict[str, float | None] = {}
        for m in metricas:
            col = m["col"]
            if col in g.columns and g[col].notna().any():
                valores[m["chave"]] = _num(g[col].max() if m.get("peak") else g[col].mean(), m["casas"])
            else:
                valores[m["chave"]] = None
        resumo.append({
            "jogador": jogador,
            "posicao": posicao,
            "n_sessoes": int(g["Data"].nunique()) if "Data" in g.columns else int(len(g)),
            "valores": valores,
        })
    return resumo


def _metricas_disponiveis(df: pd.DataFrame) -> list[dict]:
    return [m for m in TODAS if m["col"] in df.columns and df[m["col"]].notna().any()]


def _defs(metricas: list[dict]) -> list[dict]:
    return [{"chave": m["chave"], "label": m["label"], "unidade": m["unidade"], "cor": m["cor"], "casas": m["casas"]} for m in metricas]


def obter_comparacao_jogadores(team_id: str) -> dict:
    df = carregar_df_equipa(team_id)
    if df.empty or "Jogador" not in df.columns:
        return {"tem_dados": False, "metricas": [], "jogadores": [], "benchmark": {}}

    metricas = _metricas_disponiveis(df)
    jogadores = _resumo_por_jogador(df, metricas)
    jogadores.sort(key=lambda r: r["jogador"].lower())

    # Benchmark = média da equipa (média das médias por jogador).
    benchmark: dict[str, float | None] = {}
    for m in metricas:
        vals = [j["valores"][m["chave"]] for j in jogadores if j["valores"].get(m["chave"]) is not None]
        benchmark[m["chave"]] = _num(sum(vals) / len(vals), m["casas"]) if vals else None

    return {"tem_dados": True, "metricas": _defs(metricas), "jogadores": jogadores, "benchmark": benchmark}


def obter_comparacao_posicoes(team_id: str) -> dict:
    df = carregar_df_equipa(team_id)
    if df.empty or "Posição" not in df.columns:
        return {"tem_dados": False, "metricas": [], "posicoes": [], "benchmark": {}}

    metricas = _metricas_disponiveis(df)
    por_jogador = _resumo_por_jogador(df, metricas)

    # Agregar por posição: média das médias por jogador (cada jogador pesa igual).
    grupos: dict[str, list[dict]] = {}
    for j in por_jogador:
        grupos.setdefault(j["posicao"], []).append(j)

    posicoes = []
    for posicao, jogs in grupos.items():
        valores: dict[str, float | None] = {}
        for m in metricas:
            vals = [j["valores"][m["chave"]] for j in jogs if j["valores"].get(m["chave"]) is not None]
            valores[m["chave"]] = _num(sum(vals) / len(vals), m["casas"]) if vals else None
        posicoes.append({
            "posicao": posicao,
            "n_jogadores": len(jogs),
            "n_sessoes": int(sum(j["n_sessoes"] for j in jogs)),
            "valores": valores,
        })
    posicoes.sort(key=lambda r: r["posicao"])

    # Benchmark global (média das médias por jogador) para referência.
    benchmark: dict[str, float | None] = {}
    for m in metricas:
        vals = [j["valores"][m["chave"]] for j in por_jogador if j["valores"].get(m["chave"]) is not None]
        benchmark[m["chave"]] = _num(sum(vals) / len(vals), m["casas"]) if vals else None

    return {"tem_dados": True, "metricas": _defs(metricas), "posicoes": posicoes, "benchmark": benchmark}
