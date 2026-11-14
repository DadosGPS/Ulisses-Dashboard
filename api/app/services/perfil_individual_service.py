"""Perfil individual — carga de alta velocidade e de aceleração/desaceleração
lida face às capacidades de CADA jogador, a partir do export do STATSports
Sonra (ver utils/sonra.py).

Por jogador, num período:
  • Velocidade: a Vmáx de referência (a do perfil do jogador no Sonra; sem
    ela, o recorde nos dados da app), a melhor % atingida e quantas sessões
    chegaram a ≥ 85 % e ≥ 95 % dessa Vmáx;
  • Zonas de velocidade RELATIVAS do Sonra (metros e entradas por zona). O
    Sonra só exporta os totais por zona: «metros acima de 85 % da Vmáx» são os
    metros das zonas relativas que começam em 85 % — configura-se no Sonra
    (Settings › zonas relativas de velocidade), não aqui;
  • HSR absoluto (> 19,8 km/h) ao lado do relativo;
  • Perfil de acelerações e desacelerações: contagem por zona (1–6), parte nas
    zonas altas (4–6) e máximos.
"""
from __future__ import annotations

import pandas as pd

from utils.calculos import recorde_vmax
from utils.sonra import (
    EXTRA_ACC_MAX,
    EXTRA_DCC_MAX,
    EXTRA_HSR_REL,
    EXTRA_VMAX_JOGADOR,
    ZONAS,
    extra_acc,
    extra_dcc,
    extra_dist_rel,
    extra_entradas_rel,
    nomes_extra,
)

COL_VMAX = "Vel. Máx (km/h)"
PCTS_SESSOES = (85, 95)
ZONAS_ALTAS = (4, 5, 6)
PERIODOS = (7, 28, 0)  # dias; 0 = todos os dados


def _soma(g: pd.DataFrame, col: str) -> float | None:
    if col not in g.columns or g[col].dropna().empty:
        return None
    return round(float(pd.to_numeric(g[col], errors="coerce").sum()), 0)


def _maximo(g: pd.DataFrame, col: str, casas: int = 2) -> float | None:
    if col not in g.columns or g[col].dropna().empty:
        return None
    return round(float(pd.to_numeric(g[col], errors="coerce").max()), casas)


def _zonas(g: pd.DataFrame, nome) -> dict[str, float] | None:
    vals = {str(z): _soma(g, nome(z)) for z in ZONAS}
    return vals if any(v is not None for v in vals.values()) else None


def calcular(df: pd.DataFrame, dias: int = 28) -> dict:
    """Parte pura (testável)."""
    vazio = {"tem_dados": False, "tem_sonra": False, "dias": dias, "de": None, "ate": None,
             "pcts_sessoes": list(PCTS_SESSOES), "zonas_altas": list(ZONAS_ALTAS), "jogadores": []}
    if df is None or df.empty or "Jogador" not in df.columns or "Data" not in df.columns:
        return vazio
    df = df.copy()
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df = df.dropna(subset=["Data", "Jogador"])
    if df.empty:
        return vazio
    ate = df["Data"].max().normalize()
    de = ate - pd.Timedelta(days=dias - 1) if dias and dias > 0 else df["Data"].min().normalize()
    periodo = df[df["Data"] >= de]
    tem_sonra = bool(set(df.columns) & nomes_extra())

    jogadores = []
    for nome, g in periodo.groupby("Jogador"):
        gfull = df[df["Jogador"] == nome]
        # Vmáx de referência: a do perfil Sonra (é a que define as zonas
        # relativas), senão o recorde nos dados da app.
        vref, fonte = None, None
        if EXTRA_VMAX_JOGADOR in gfull.columns and gfull[EXTRA_VMAX_JOGADOR].notna().any():
            vref, fonte = float(pd.to_numeric(gfull[EXTRA_VMAX_JOGADOR], errors="coerce").dropna().iloc[-1]), "sonra"
        elif COL_VMAX in gfull.columns:
            vref, fonte = recorde_vmax(gfull[COL_VMAX]), "recorde"
        picos = pd.to_numeric(g[COL_VMAX], errors="coerce").dropna() if COL_VMAX in g.columns else pd.Series(dtype=float)
        pcts = (picos / vref * 100) if vref else pd.Series(dtype=float)
        posicao = g["Posição"].dropna().iloc[-1] if "Posição" in g.columns and g["Posição"].notna().any() else None

        acc, dcc = _zonas(g, extra_acc), _zonas(g, extra_dcc)

        def parte_alta(zonas):
            if not zonas:
                return None
            total = sum(v or 0 for v in zonas.values())
            return round(sum(zonas[str(z)] or 0 for z in ZONAS_ALTAS) / total * 100, 0) if total else None

        jogadores.append({
            "jogador": nome,
            "posicao": posicao if isinstance(posicao, str) else None,
            "n_sessoes": int(g["Data"].dt.normalize().nunique()),
            "vmax_ref": round(vref, 1) if vref else None,
            "fonte_vmax": fonte if vref else None,
            "melhor_pct": round(float(pcts.max()), 0) if not pcts.empty else None,
            "sessoes_pct": {str(p): int((pcts >= p).sum()) for p in PCTS_SESSOES} if not pcts.empty else None,
            "dist_rel": _zonas(g, extra_dist_rel),
            "entradas_rel": _zonas(g, extra_entradas_rel),
            "hsr_abs": _soma(g, "HSR (m)"),
            "hsr_rel": _soma(g, EXTRA_HSR_REL),
            "acc_zonas": acc,
            "dcc_zonas": dcc,
            "acc_alta_pct": parte_alta(acc),
            "dcc_alta_pct": parte_alta(dcc),
            "acc_max": _maximo(g, EXTRA_ACC_MAX),
            "dcc_max": _maximo(g, EXTRA_DCC_MAX),
        })
    jogadores.sort(key=lambda j: str(j["jogador"]))
    return {**vazio, "tem_dados": bool(jogadores), "tem_sonra": tem_sonra,
            "de": de.date().isoformat(), "ate": ate.date().isoformat(), "jogadores": jogadores}


def obter_perfil_individual(team_id: str, dias: int = 28) -> dict:
    from app.services.dados_equipa import carregar_df_equipa

    return calcular(carregar_df_equipa(team_id), dias if dias in PERIODOS else 28)
