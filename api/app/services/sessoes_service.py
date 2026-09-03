"""Sessões — lista de sessões reais a partir de gps_sessions.

Cada sessão = uma combinação (Data, Tipo). Agrega o plantel presente e os
totais de carga da equipa nessa sessão. Reutiliza carregar_df_equipa.
"""
from __future__ import annotations

import pandas as pd

from app.services.dados_equipa import carregar_df_equipa


def _num(v, casas=0):
    if v is None or pd.isna(v):
        return None
    return round(float(v), casas)


def listar_sessoes(
    team_id: str,
    limite: int = 200,
    jogador: str | None = None,
    microciclo: int | None = None,
    dia_md: str | None = None,
) -> dict:
    df = carregar_df_equipa(team_id)
    if df.empty or "Data" not in df.columns:
        return {"tem_dados": False, "sessoes": []}

    df = df.copy()
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df = df.dropna(subset=["Data"])
    if jogador and "Jogador" in df.columns:
        df = df[df["Jogador"] == jogador]
    if microciclo is not None and "Microciclo (Nr)" in df.columns:
        df = df[df["Microciclo (Nr)"] == microciclo]
    if dia_md and "Dia MD" in df.columns:
        df = df[df["Dia MD"] == dia_md]
    if df.empty:
        return {"tem_dados": False, "sessoes": []}

    tem_tipo = "Tipo" in df.columns
    chaves = ["Data", "Tipo"] if tem_tipo else ["Data"]

    sessoes = []
    for chave, g in df.groupby(chaves):
        data = chave[0] if isinstance(chave, tuple) else chave
        tipo = (chave[1] if isinstance(chave, tuple) else None) or "—"
        sessoes.append({
            "data": pd.Timestamp(data).strftime("%Y-%m-%d"),
            "tipo": tipo,
            "dia_md": g["Dia MD"].dropna().iloc[0] if "Dia MD" in g.columns and g["Dia MD"].notna().any() else "—",
            "microciclo": int(g["Microciclo (Nr)"].dropna().iloc[0]) if "Microciclo (Nr)" in g.columns and g["Microciclo (Nr)"].notna().any() else None,
            "n_jogadores": int(g["Jogador"].nunique()),
            "duracao_min": _num(g["Duração (min)"].max()) if "Duração (min)" in g.columns else None,
            "distancia_total_m": _num(g["Distância Total (m)"].sum()) if "Distância Total (m)" in g.columns else None,
            "hsr_m": _num(g["HSR (m)"].sum()) if "HSR (m)" in g.columns else None,
            "sprint_m": _num(g["Sprint (m)"].sum()) if "Sprint (m)" in g.columns else None,
            "carga_interna_media": _num(g["Carga Interna"].mean()) if "Carga Interna" in g.columns else None,
        })

    sessoes.sort(key=lambda s: (s["data"], s["tipo"]), reverse=True)
    return {"tem_dados": True, "sessoes": sessoes[:limite]}
