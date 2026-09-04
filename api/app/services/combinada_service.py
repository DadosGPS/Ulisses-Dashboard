"""Análise combinada — carga externa × interna (brief secção 13).

Cruza, por jogador, um indicador de carga externa (distância total) com a
carga interna, classificando cada jogador num de quatro quadrantes face à
mediana da equipa. São FLAGS DE MONITORIZAÇÃO, não diagnósticos de lesão:
ajudam o preparador a decidir onde olhar, não substituem o seu julgamento.
"""
from __future__ import annotations

import pandas as pd

from utils.calculos import calcular_acwr_global

from app.services.dados_equipa import carregar_df_equipa

EIXO_EXTERNO = {"col": "Distância Total (m)", "label": "Distância Total", "unidade": "m"}
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


def _num(v, casas=0):
    if v is None or pd.isna(v):
        return None
    return round(float(v), casas)


def _flag(ext_alto: bool, int_alto: bool) -> str:
    return f"Ext {'↑' if ext_alto else '↓'} · Int {'↑' if int_alto else '↓'}"


def obter_combinada(team_id: str, microciclo: int | None = None, dia_md: str | None = None) -> dict:
    vazio = {"tem_dados": False, "jogadores": [], "mediana_externo": None, "mediana_interno": None}
    df = carregar_df_equipa(team_id)
    if df.empty or EIXO_EXTERNO["col"] not in df.columns:
        return vazio

    eixo_interno = _escolher_eixo_interno(df)
    if eixo_interno is None:
        return vazio

    if microciclo is not None and "Microciclo (Nr)" in df.columns:
        df = df[df["Microciclo (Nr)"] == microciclo]
    if dia_md and "Dia MD" in df.columns:
        df = df[df["Dia MD"] == dia_md]
    if df.empty:
        return vazio

    acwr = calcular_acwr_global(df)

    linhas = []
    for jogador, g in df.groupby("Jogador"):
        ext = g[EIXO_EXTERNO["col"]].mean() if g[EIXO_EXTERNO["col"]].notna().any() else None
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

    for l in linhas:
        ext_alto = l["externo"] >= med_ext
        int_alto = l["interno"] >= med_int
        l["flag_ext"] = "alto" if ext_alto else "baixo"
        l["flag_int"] = "alto" if int_alto else "baixo"
        l["flag"] = _flag(ext_alto, int_alto)
        l["externo"] = _num(l["externo"], 0)
        l["interno"] = _num(l["interno"], 1 if eixo_interno["col"] == "PSE Sessão" else 0)

    linhas.sort(key=lambda r: r["jogador"].lower())

    return {
        "tem_dados": True,
        "eixo_externo": {"label": EIXO_EXTERNO["label"], "unidade": EIXO_EXTERNO["unidade"]},
        "eixo_interno": {"label": eixo_interno["label"], "unidade": eixo_interno["unidade"]},
        "mediana_externo": _num(med_ext, 0),
        "mediana_interno": _num(med_int, 1 if eixo_interno["col"] == "PSE Sessão" else 0),
        "jogadores": linhas,
    }
