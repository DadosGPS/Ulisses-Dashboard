"""Perfil de velocidade individual — limiares de HSR/sprint ancorados na
velocidade máxima (MSS/Vmáx) de CADA jogador, em vez de um limiar absoluto
igual para todos.

Fundamentação (modelo a duas dimensões, Frontiers 2025; revisão sistemática
Frontiers 2023):
  • HSR metabólico  → até ~70–75% da Vmáx (banda aeróbia; idealmente ancorado
    na MAS, aqui aproximado por % da Vmáx enquanto não há teste de MAS).
  • HSR mecânico    → ~75–90% da Vmáx (banda neuromuscular/locomotora).
  • Sprint          → > 90% da Vmáx individual.
Referência absoluta clássica (para comparar): HSR > 19,8 km/h; Sprint > 25,2 km/h.

Nota: os metros de HSR/Sprint guardados vêm já calculados pelo GPS num limiar
FIXO — por isso aqui individualizamos os LIMIARES (km/h) e classificamos as
sessões pelo pico de velocidade de cada jogador. O recálculo exato dos metros
individualizados exige o export com distância por banda de velocidade.
"""
from __future__ import annotations

import pandas as pd

from app.services.dados_equipa import carregar_df_equipa

# Percentagens por omissão (da Vmáx individual). Configuráveis por query.
PCT_METABOLICO = 70
PCT_MECANICO = 85
PCT_SPRINT = 90

# Referência absoluta clássica (km/h).
ABS_HSR_KMH = 19.8
ABS_SPRINT_KMH = 25.2

COL_VMAX = "Vel. Máx (km/h)"


def _num(v, casas: int = 1) -> float | None:
    if v is None or pd.isna(v):
        return None
    return round(float(v), casas)


def obter_perfil_velocidade(
    team_id: str,
    pct_metabolico: int = PCT_METABOLICO,
    pct_mecanico: int = PCT_MECANICO,
    pct_sprint: int = PCT_SPRINT,
) -> dict:
    base = {
        "tem_dados": False,
        "limiares_pct": {"metabolico": pct_metabolico, "mecanico": pct_mecanico, "sprint": pct_sprint},
        "referencia_absoluta": {"hsr": ABS_HSR_KMH, "sprint": ABS_SPRINT_KMH},
        "jogadores": [],
    }

    df = carregar_df_equipa(team_id)
    if df.empty or COL_VMAX not in df.columns or "Jogador" not in df.columns:
        return base
    if not df[COL_VMAX].notna().any():
        return base

    jogadores: list[dict] = []
    for nome, g in df.groupby("Jogador"):
        vmax_serie = g[COL_VMAX].dropna()
        if vmax_serie.empty:
            continue
        mss = float(vmax_serie.max())
        if mss <= 0:
            continue

        lim_met = mss * pct_metabolico / 100.0
        lim_mec = mss * pct_mecanico / 100.0
        lim_spr = mss * pct_sprint / 100.0

        # Classificação por sessão pelo pico de velocidade do jogador.
        n_sessoes = int(vmax_serie.shape[0])
        n_sprint_ind = int((vmax_serie >= lim_spr).sum())
        n_sprint_abs = int((vmax_serie >= ABS_SPRINT_KMH).sum())

        posicao = g["Posição"].dropna().iloc[-1] if "Posição" in g.columns and g["Posição"].notna().any() else "—"

        jogadores.append({
            "jogador": nome,
            "posicao": posicao,
            "mss_kmh": _num(mss),
            "limiar_metabolico_kmh": _num(lim_met),
            "limiar_mecanico_kmh": _num(lim_mec),
            "limiar_sprint_kmh": _num(lim_spr),
            "n_sessoes": n_sessoes,
            "n_sprint_individual": n_sprint_ind,
            "pct_sprint_individual": _num(n_sprint_ind / n_sessoes * 100, 0) if n_sessoes else None,
            "n_sprint_absoluto": n_sprint_abs,
        })

    # Ordenar por MSS desc (os mais rápidos primeiro).
    jogadores.sort(key=lambda r: (r["mss_kmh"] is None, -(r["mss_kmh"] or 0)))

    return {**base, "tem_dados": bool(jogadores), "jogadores": jogadores}
