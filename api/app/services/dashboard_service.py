"""Dashboard — Fase 5 do plano de migração (página piloto).

Reutiliza utils/calculos.py (calcular_acwr_global, cor_acwr) tal como a app
Streamlit usava — a diferença é que os dados vêm agora do Postgres (Fase 4)
em vez de um DataFrame em memória descartado no fim da sessão.

A lógica de alertas/KPIs abaixo é uma extração inicial do motor que vivia
embutido em app_pages/dashboard.py (linhas ~36-326) — cobre ACWR e wellness;
a recomendação do dia (perfil por Dia MD) fica para uma iteração seguinte,
documentada no plano como parte da Fase 5.
"""
import numpy as np
import pandas as pd

from utils.calculos import calcular_acwr_global, cor_acwr

from app.services.dados_equipa import carregar_df_equipa

METRICAS_RANKING = {
    "Carga Interna":   {"cor": "#e63946", "unit": " UA"},
    "Distância Total (m)": {"cor": "#2563eb", "unit": "m"},
    "HSR (m)":         {"cor": "#f59e0b", "unit": "m"},
    "Sprint (m)":      {"cor": "#dc2626", "unit": "m"},
    "Vel. Máx (km/h)": {"cor": "#8b5cf6", "unit": " km/h"},
}


def obter_dashboard(team_id: str) -> dict:
    df = carregar_df_equipa(team_id)
    if df.empty:
        return {
            "tem_dados": False,
            "kpis": {}, "alertas": [], "rankings": [],
        }

    acwr_dict = calcular_acwr_global(df)

    alertas_criticos, alertas_atencao = [], []
    for jog, dados in acwr_dict.items():
        v = dados["acwr"]
        estado = cor_acwr(v)
        pos = dados.get("posicao", "—")
        item = {"jogador": jog, "posicao": pos, "tipo": "ACWR", "valor": round(float(v), 2), "estado": estado}
        if "RISCO" in estado:
            alertas_criticos.append(item)
        elif "ATENÇÃO" in estado:
            alertas_atencao.append(item)

    if "Hooper Index" in df.columns:
        ultima = df.sort_values("Data").groupby("Jogador").last().reset_index()
        for _, row in ultima.iterrows():
            hi = row.get("Hooper Index")
            if pd.notna(hi) and hi >= 14:
                alertas_criticos.append({
                    "jogador": row["Jogador"], "posicao": row.get("Posição", "—"),
                    "tipo": "Wellness", "valor": float(hi), "estado": "🔴 RISCO",
                })

    mc_recente = int(df["Microciclo (Nr)"].dropna().max()) if "Microciclo (Nr)" in df.columns and df["Microciclo (Nr)"].notna().any() else None
    df_mc = df[df["Microciclo (Nr)"] == mc_recente] if mc_recente is not None else df

    ci_media = float(df_mc["Carga Interna"].mean()) if "Carga Interna" in df_mc.columns and df_mc["Carga Interna"].notna().any() else None
    hooper_media = float(df_mc["Hooper Index"].mean()) if "Hooper Index" in df_mc.columns and df_mc["Hooper Index"].notna().any() else None
    acwr_vals = [d["acwr"] for d in acwr_dict.values() if pd.notna(d["acwr"])]
    acwr_media = float(np.mean(acwr_vals)) if acwr_vals else None

    rankings = []
    for nome_metrica, cfg in METRICAS_RANKING.items():
        if nome_metrica not in df_mc.columns:
            continue
        serie = df_mc.groupby("Jogador")[nome_metrica].mean().dropna().sort_values(ascending=False)
        if serie.empty:
            continue
        rankings.append({
            "metrica": nome_metrica,
            "cor": cfg["cor"],
            "unidade": cfg["unit"],
            "top3": [{"jogador": j, "valor": round(float(v), 1)} for j, v in serie.head(3).items()],
            "bottom3": [{"jogador": j, "valor": round(float(v), 1)} for j, v in serie.tail(3).items()][::-1],
        })

    return {
        "tem_dados": True,
        "microciclo_recente": mc_recente,
        "kpis": {
            "carga_interna_media": round(ci_media, 0) if ci_media is not None else None,
            "acwr_medio": round(acwr_media, 2) if acwr_media is not None else None,
            "hooper_medio": round(hooper_media, 1) if hooper_media is not None else None,
            "em_risco": len(alertas_criticos),
        },
        "alertas": (alertas_criticos + alertas_atencao)[:5],
        "rankings": rankings,
    }
