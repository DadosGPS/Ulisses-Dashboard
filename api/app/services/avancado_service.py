"""Avançado — Fase 8 do plano de migração (Z-Score).

Reutiliza utils/calculos.py::zscore_serie tal como a app Streamlit
(app_pages/avancado.py) — compara cada jogador à média da equipa no
microciclo mais recente, em desvios-padrão.
"""
import pandas as pd

from utils.calculos import zscore_serie

from app.services.dados_equipa import carregar_df_equipa

METRICAS_ZSCORE = ["Carga Interna", "Distância Total (m)", "HSR (m)", "Sprint (m)", "Vel. Máx (km/h)"]


def obter_avancado(team_id: str) -> dict:
    df = carregar_df_equipa(team_id)
    if df.empty:
        return {"tem_dados": False, "microciclo": None, "metricas": []}

    mc_recente = int(df["Microciclo (Nr)"].dropna().max()) if "Microciclo (Nr)" in df.columns and df["Microciclo (Nr)"].notna().any() else None
    df_mc = df[df["Microciclo (Nr)"] == mc_recente] if mc_recente is not None else df

    resultado_metricas = []
    for metrica in METRICAS_ZSCORE:
        if metrica not in df_mc.columns or not df_mc[metrica].notna().any():
            continue
        medias = df_mc.groupby("Jogador")[metrica].mean().dropna()
        if len(medias) < 2:
            continue
        zscores = zscore_serie(medias).sort_values(ascending=False)
        resultado_metricas.append({
            "metrica": metrica,
            "jogadores": [
                {"jogador": j, "valor": round(float(medias[j]), 1), "zscore": round(float(z), 2)}
                for j, z in zscores.items()
            ],
        })

    return {"tem_dados": True, "microciclo": mc_recente, "metricas": resultado_metricas}
