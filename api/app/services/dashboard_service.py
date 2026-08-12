"""Dashboard — Fase 5 do plano de migração (página piloto).

Reutiliza utils/calculos.py (calcular_acwr_global, cor_acwr) tal como a app
Streamlit usava — a diferença é que os dados vêm agora do Postgres (Fase 4)
em vez de um DataFrame em memória descartado no fim da sessão.

A lógica de alertas/KPIs abaixo é uma extração do motor que vivia embutido
em app_pages/dashboard.py (linhas ~36-326) — cobre ACWR e wellness. O
"resumo_5w1h" substitui a recomendação do dia por uma versão estruturada
segundo o modelo 5W+1H (ver app/services/resumo_5w1h.py).
"""
import numpy as np
import pandas as pd

from utils.calculos import calcular_acwr_global, cor_acwr

from app.services.dados_equipa import carregar_df_equipa
from app.services.resumo_5w1h import PERFIL_DIA_MD, gerar_resumo_5w1h

METRICAS_RANKING = {
    "Carga Interna":   {"cor": "#e63946", "unit": " UA"},
    "Distância Total (m)": {"cor": "#2563eb", "unit": "m"},
    "HSR (m)":         {"cor": "#f59e0b", "unit": "m"},
    "Sprint (m)":      {"cor": "#dc2626", "unit": "m"},
    "Vel. Máx (km/h)": {"cor": "#8b5cf6", "unit": " km/h"},
}


def obter_dashboard(team_id: str, microciclo: int | None = None, dia_md: str | None = None) -> dict:
    df = carregar_df_equipa(team_id)
    if df.empty:
        return {
            "tem_dados": False,
            "kpis": {}, "alertas": [], "rankings": [],
        }

    # ACWR usa sempre o histórico completo (EWMA por sessão) — só o resto do
    # dashboard (KPIs, rankings) é que fica limitado ao microciclo escolhido.
    acwr_dict = calcular_acwr_global(df)

    tem_microciclo = "Microciclo (Nr)" in df.columns and df["Microciclo (Nr)"].notna().any()
    microciclos_disponiveis = sorted(df["Microciclo (Nr)"].dropna().astype(int).unique().tolist()) if tem_microciclo else []
    mc_recente = microciclos_disponiveis[-1] if microciclos_disponiveis else None
    mc_selecionado = microciclo if (microciclo is not None and microciclo in microciclos_disponiveis) else mc_recente
    df_mc = df[df["Microciclo (Nr)"] == mc_selecionado] if mc_selecionado is not None else df

    # Dias MD disponíveis — ordem fixa (MD-5 ... MD ... MD+2), não alfabética,
    # e só os que realmente existem nos dados desta equipa.
    dias_md_disponiveis = []
    if "Dia MD" in df.columns:
        presentes = set(df["Dia MD"].dropna().unique().tolist())
        dias_md_disponiveis = [d for d in PERFIL_DIA_MD if d in presentes]
    dia_md_selecionado = dia_md if dia_md in dias_md_disponiveis else None
    if dia_md_selecionado:
        df_mc = df_mc[df_mc["Dia MD"] == dia_md_selecionado]

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

    if "Hooper Index" in df_mc.columns:
        ultima = df_mc.sort_values("Data").groupby("Jogador").last().reset_index()
        for _, row in ultima.iterrows():
            hi = row.get("Hooper Index")
            if pd.notna(hi) and hi >= 14:
                alertas_criticos.append({
                    "jogador": row["Jogador"], "posicao": row.get("Posição", "—"),
                    "tipo": "Wellness", "valor": float(hi), "estado": "🔴 RISCO",
                })

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
        "microciclo_selecionado": mc_selecionado,
        "microciclos_disponiveis": microciclos_disponiveis,
        "dia_md_selecionado": dia_md_selecionado,
        "dias_md_disponiveis": dias_md_disponiveis,
        "kpis": {
            "carga_interna_media": round(ci_media, 0) if ci_media is not None else None,
            "acwr_medio": round(acwr_media, 2) if acwr_media is not None else None,
            "hooper_medio": round(hooper_media, 1) if hooper_media is not None else None,
            "em_risco": len(alertas_criticos),
        },
        "alertas": (alertas_criticos + alertas_atencao)[:5],
        "rankings": rankings,
        # Usa sempre o histórico completo (não df_mc) — a comparação "média
        # histórica de sessões semelhantes" precisa de todas as semanas para
        # fazer sentido, não só da semana escolhida no seletor.
        "resumo_5w1h": gerar_resumo_5w1h(df),
    }
