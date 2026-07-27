"""Dashboard — Fase 5 do plano de migração (página piloto).

Reutiliza utils/calculos.py (calcular_acwr_global, cor_acwr) tal como a app
Streamlit usava — a diferença é que os dados vêm agora do Postgres (Fase 4)
em vez de um DataFrame em memória descartado no fim da sessão.

A lógica de alertas/KPIs abaixo é uma extração inicial do motor que vivia
embutido em app_pages/dashboard.py (linhas ~36-326) — cobre ACWR e wellness;
a recomendação do dia (perfil por Dia MD) fica para uma iteração seguinte,
documentada no plano como parte da Fase 5.
"""
import json
from datetime import date

import numpy as np
import pandas as pd

from utils.calculos import calcular_acwr_global, cor_acwr

from app.core.db import get_conn

DB_TO_CANONICAL = {
    "tipo": "Tipo",
    "dia_md": "Dia MD",
    "microciclo_nr": "Microciclo (Nr)",
    "distancia_total_m": "Distância Total (m)",
    "hsr_m": "HSR (m)",
    "sprint_m": "Sprint (m)",
    "acc_n": "Acc (n)",
    "dcc_n": "Dcc (n)",
    "vel_max_kmh": "Vel. Máx (km/h)",
    "pse_sessao": "PSE Sessão",
    "duracao_min": "Duração (min)",
    "carga_interna": "Carga Interna",
    "hooper_index": "Hooper Index",
    "sono": "Sono (1-5)",
    "dor_musc": "Dor Musc. (1-5)",
    "stress": "Stress (1-5)",
    "humor": "Humor (1-5)",
}

METRICAS_RANKING = {
    "Carga Interna":   {"cor": "#e63946", "unit": " UA"},
    "Distância Total (m)": {"cor": "#2563eb", "unit": "m"},
    "HSR (m)":         {"cor": "#f59e0b", "unit": "m"},
    "Sprint (m)":      {"cor": "#dc2626", "unit": "m"},
    "Vel. Máx (km/h)": {"cor": "#8b5cf6", "unit": " km/h"},
}


def _carregar_df_equipa(team_id: str) -> pd.DataFrame:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select gs.*, p.nome as jogador_nome, p.posicao as jogador_posicao
                from gps_sessions gs
                join players p on p.id = gs.player_id
                where gs.team_id = %s
                order by gs.data
                """,
                (team_id,),
            )
            colunas = [c.name for c in cur.description]
            linhas = cur.fetchall()

    if not linhas:
        return pd.DataFrame()

    df = pd.DataFrame(linhas, columns=colunas)
    df = df.rename(columns=DB_TO_CANONICAL)
    df["Jogador"] = df["jogador_nome"]
    df["Posição"] = df["jogador_posicao"]
    df["Data"] = pd.to_datetime(df["data"])

    # extra_metrics (jsonb) → colunas adicionais, para preservar a deteção
    # dinâmica de métricas que get_mets_gps() já suportava na app Streamlit.
    extras = df["extra_metrics"].apply(lambda v: v if isinstance(v, dict) else (json.loads(v) if v else {}))
    if extras.apply(len).sum() > 0:
        df_extras = pd.json_normalize(extras)
        df = pd.concat([df.reset_index(drop=True), df_extras.reset_index(drop=True)], axis=1)

    return df


def obter_dashboard(team_id: str) -> dict:
    df = _carregar_df_equipa(team_id)
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
