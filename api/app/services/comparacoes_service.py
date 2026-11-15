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


def _filtrar(df: pd.DataFrame, microciclo: int | None, dia_md: str | None) -> pd.DataFrame:
    if microciclo is not None and "Microciclo (Nr)" in df.columns:
        df = df[df["Microciclo (Nr)"] == microciclo]
    if dia_md and "Dia MD" in df.columns:
        df = df[df["Dia MD"] == dia_md]
    return df


# Métricas que NÃO se dividem por minuto (picos e índices).
SEM_POR_MINUTO = {"hooper_index"}
MIN_MINUTOS_JOGO = 30


def _por_minuto(m: dict) -> bool:
    return not m.get("peak") and m["chave"] not in SEM_POR_MINUTO


def _resumo_por_jogador(df: pd.DataFrame, metricas: list[dict], por_minuto: bool = False) -> list[dict]:
    """Média por jogador de cada métrica (por sessão; ou por minuto, se pedido)."""
    resumo = []
    dur = "Duração (min)"
    for jogador, g in df.groupby("Jogador"):
        posicao = g["Posição"].dropna().iloc[-1] if "Posição" in g.columns and g["Posição"].notna().any() else "—"
        valores: dict[str, float | None] = {}
        for m in metricas:
            col = m["col"]
            if col not in g.columns or not g[col].notna().any():
                valores[m["chave"]] = None
                continue
            serie = pd.to_numeric(g[col], errors="coerce")
            if m.get("peak"):
                valores[m["chave"]] = _num(serie.max(), m["casas"])
            elif por_minuto and _por_minuto(m):
                if dur not in g.columns:
                    valores[m["chave"]] = None
                    continue
                d = pd.to_numeric(g[dur], errors="coerce")
                ok = serie.notna() & (d > 0)
                valores[m["chave"]] = _num(serie[ok].sum() / d[ok].sum(), 2) if ok.any() else None
            else:
                valores[m["chave"]] = _num(serie.mean(), m["casas"])
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


def _contexto(df: pd.DataFrame, contexto: str, ultimos: int | None) -> pd.DataFrame:
    """jogos (só com ≥ 30 min jogados) · treinos · todos; e/ou só os últimos N microciclos."""
    from app.services.referencia_jogo import mascara_jogo
    if ultimos and "Microciclo (Nr)" in df.columns and df["Microciclo (Nr)"].notna().any():
        mcs = sorted(df["Microciclo (Nr)"].dropna().unique())[-ultimos:]
        df = df[df["Microciclo (Nr)"].isin(mcs)]
    if contexto in ("jogos", "treinos") and not df.empty:
        e_jogo = mascara_jogo(df)
        if contexto == "jogos":
            df = df[e_jogo]
            if "Duração (min)" in df.columns:
                df = df[pd.to_numeric(df["Duração (min)"], errors="coerce").fillna(0) >= MIN_MINUTOS_JOGO]
        else:
            df = df[~e_jogo]
            if "Tipo" in df.columns:
                df = df[df["Tipo"] != "Ginásio"]
    return df


def obter_comparacao_jogadores(team_id: str, microciclo: int | None = None, dia_md: str | None = None,
                               contexto: str = "todos", por_minuto: bool = False, ultimos: int | None = None) -> dict:
    vazio = {"tem_dados": False, "metricas": [], "jogadores": [], "benchmark": {}, "contexto": contexto, "por_minuto": por_minuto}
    df = carregar_df_equipa(team_id)
    if df.empty or "Jogador" not in df.columns:
        return vazio
    df = _contexto(_filtrar(df, microciclo, dia_md), contexto, ultimos)
    if df.empty:
        return vazio

    metricas = _metricas_disponiveis(df)
    if contexto == "jogos":   # bem-estar não diz nada sobre o jogo em si
        metricas = [m for m in metricas if m["chave"] != "hooper_index"]
    jogadores = _resumo_por_jogador(df, metricas, por_minuto)
    jogadores.sort(key=lambda r: r["jogador"].lower())

    # Benchmark = média da equipa (média das médias por jogador).
    benchmark: dict[str, float | None] = {}
    for m in metricas:
        vals = [j["valores"][m["chave"]] for j in jogadores if j["valores"].get(m["chave"]) is not None]
        benchmark[m["chave"]] = _num(sum(vals) / len(vals), 2 if por_minuto and _por_minuto(m) else m["casas"]) if vals else None

    defs = _defs(metricas)
    for d, m in zip(defs, metricas):
        d["peak"] = bool(m.get("peak"))
        if por_minuto and _por_minuto(m):
            d["unidade"] = f"{d['unidade']}/min" if d["unidade"] else "/min"
            d["casas"] = 2
    return {"tem_dados": True, "metricas": defs, "jogadores": jogadores, "benchmark": benchmark,
            "contexto": contexto, "por_minuto": por_minuto}


def obter_comparacao_posicoes(team_id: str, microciclo: int | None = None, dia_md: str | None = None) -> dict:
    df = carregar_df_equipa(team_id)
    if df.empty or "Posição" not in df.columns:
        return {"tem_dados": False, "metricas": [], "posicoes": [], "benchmark": {}}
    df = _filtrar(df, microciclo, dia_md)
    if df.empty:
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
