"""Análise combinada — carga externa × interna (brief secção 13).

Cruza, por jogador, um indicador de carga externa (escolhido no seletor;
por defeito acelerações + desacelerações) com a carga interna, classificando cada jogador num de quatro quadrantes face à
mediana da equipa. São FLAGS DE MONITORIZAÇÃO, não diagnósticos de lesão:
ajudam o preparador a decidir onde olhar, não substituem o seu julgamento.
"""
from __future__ import annotations

import pandas as pd

from utils.calculos import calcular_acwr_global

from app.services.dados_equipa import carregar_df_equipa

# Eixos externos que o preparador pode escolher. «cols» são somadas por sessão;
# «por_min» divide pela duração da sessão e compara-se com a PSE (intensidade
# com intensidade), para a duração não dominar o gráfico.
EIXOS_EXTERNOS = {
    "accdcc": {"cols": ["Acc (n)", "Dcc (n)"], "label": "Acc + Dcc", "unidade": "n", "por_min": False},
    "accdcc_min": {"cols": ["Acc (n)", "Dcc (n)"], "label": "Acc + Dcc por minuto", "unidade": "n/min", "por_min": True},
    "hsr": {"cols": ["HSR (m)"], "label": "HSR", "unidade": "m", "por_min": False},
    "sprint": {"cols": ["Sprint (m)"], "label": "Sprint", "unidade": "m", "por_min": False},
    "distancia": {"cols": ["Distância Total (m)"], "label": "Distância Total", "unidade": "m", "por_min": False},
    "distancia_min": {"cols": ["Distância Total (m)"], "label": "Distância por minuto", "unidade": "m/min", "por_min": True},
}
EIXO_PADRAO = "accdcc"
COL_DURACAO = "Duração (min)"
# Eixo interno preferido: Carga Interna (PSE × Duração). Muitas equipas só
# registam a PSE (sem duração), pelo que a Carga Interna não pode ser derivada
# e a página aparecia vazia. Nesse caso, cai para a PSE da sessão — continua a
# ser um indicador de carga interna válido.
EIXO_INTERNO = {"col": "Carga Interna", "label": "Carga Interna", "unidade": "UA"}
EIXO_INTERNO_FALLBACK = {"col": "PSE Sessão", "label": "PSE", "unidade": "/10"}


def _escolher_eixo_interno(df) -> dict | None:
    """Devolve o eixo interno com dados neste df (Carga Interna ou, em falta, PSE)."""
    for eixo in (EIXO_INTERNO, EIXO_INTERNO_FALLBACK):
        if eixo["col"] in df.columns and df[eixo["col"]].notna().any():
            return eixo
    return None


def _serie_externa(df: pd.DataFrame, chave: str) -> pd.Series | None:
    """Valor do eixo externo por sessão (NaN onde não há dados), ou None se o
    eixo não se pode calcular com estes dados."""
    eixo = EIXOS_EXTERNOS[chave]
    cols = eixo["cols"]
    if not all(c in df.columns and df[c].notna().any() for c in cols):
        return None
    v = df[cols].sum(axis=1, min_count=len(cols))
    if eixo["por_min"]:
        if COL_DURACAO not in df.columns:
            return None
        dur = pd.to_numeric(df[COL_DURACAO], errors="coerce")
        v = v / dur.where(dur > 0)
    return v if v.notna().any() else None


def eixos_disponiveis(df: pd.DataFrame) -> list[dict]:
    return [{"chave": k, "label": e["label"], "unidade": e["unidade"]}
            for k, e in EIXOS_EXTERNOS.items() if _serie_externa(df, k) is not None]


def _num(v, casas=0):
    if v is None or pd.isna(v):
        return None
    return round(float(v), casas)


def _flag(ext_alto: bool, int_alto: bool) -> str:
    return f"Ext {'↑' if ext_alto else '↓'} · Int {'↑' if int_alto else '↓'}"


def obter_combinada(team_id: str, microciclo: int | None = None, dia_md: str | None = None,
                    eixo: str | None = None) -> dict:
    vazio = {"tem_dados": False, "jogadores": [], "mediana_externo": None, "mediana_interno": None, "eixos": []}
    df = carregar_df_equipa(team_id)
    if df.empty:
        return vazio
    eixos = eixos_disponiveis(df)
    vazio["eixos"] = eixos
    if not eixos:
        return vazio
    chaves = [e["chave"] for e in eixos]
    chave = eixo if eixo in chaves else (EIXO_PADRAO if EIXO_PADRAO in chaves else chaves[0])
    eixo_externo = EIXOS_EXTERNOS[chave]

    # Por minuto compara-se com a PSE (intensidade); senão com a Carga Interna.
    eixo_interno = None
    if eixo_externo["por_min"] and "PSE Sessão" in df.columns and df["PSE Sessão"].notna().any():
        eixo_interno = EIXO_INTERNO_FALLBACK
    eixo_interno = eixo_interno or _escolher_eixo_interno(df)
    if eixo_interno is None:
        return vazio

    if microciclo is not None and "Microciclo (Nr)" in df.columns:
        df = df[df["Microciclo (Nr)"] == microciclo]
    if dia_md and "Dia MD" in df.columns:
        df = df[df["Dia MD"] == dia_md]
    if df.empty:
        return vazio

    acwr = calcular_acwr_global(df)
    df = df.assign(_externo=_serie_externa(df, chave))

    linhas = []
    for jogador, g in df.groupby("Jogador"):
        ext = g["_externo"].mean() if g["_externo"].notna().any() else None
        interno = g[eixo_interno["col"]].mean() if g[eixo_interno["col"]].notna().any() else None
        if ext is None or interno is None:
            continue
        posicao = g["Posição"].dropna().iloc[0] if "Posição" in g.columns and g["Posição"].notna().any() else "—"
        info_acwr = acwr.get(jogador, {})
        v_acwr = info_acwr.get("acwr")
        linhas.append({
            "jogador": jogador,
            "posicao": posicao,
            "externo": float(ext),
            "interno": float(interno),
            "acwr": round(float(v_acwr), 2) if v_acwr is not None and pd.notna(v_acwr) else None,
        })

    if not linhas:
        return vazio

    med_ext = float(pd.Series([l["externo"] for l in linhas]).median())
    med_int = float(pd.Series([l["interno"] for l in linhas]).median())

    casas_ext = 2 if chave == "accdcc_min" else (1 if eixo_externo["por_min"] else 0)
    for l in linhas:
        ext_alto = l["externo"] >= med_ext
        int_alto = l["interno"] >= med_int
        l["flag_ext"] = "alto" if ext_alto else "baixo"
        l["flag_int"] = "alto" if int_alto else "baixo"
        l["flag"] = _flag(ext_alto, int_alto)
        l["externo"] = _num(l["externo"], casas_ext)
        l["interno"] = _num(l["interno"], 1 if eixo_interno["col"] == "PSE Sessão" else 0)

    linhas.sort(key=lambda r: r["jogador"].lower())

    return {
        "tem_dados": True,
        "eixo": chave,
        "eixos": eixos,
        "eixo_externo": {"label": eixo_externo["label"], "unidade": eixo_externo["unidade"]},
        "eixo_interno": {"label": eixo_interno["label"], "unidade": eixo_interno["unidade"]},
        "mediana_externo": _num(med_ext, casas_ext),
        "mediana_interno": _num(med_int, 1 if eixo_interno["col"] == "PSE Sessão" else 0),
        "jogadores": linhas,
    }
