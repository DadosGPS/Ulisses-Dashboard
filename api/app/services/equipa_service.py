"""Equipa — Fase 6 do plano de migração.

Reutiliza utils/calculos.py (ACWR) tal como o dashboard; acrescenta a
evolução de Carga Interna por microciclo e o perfil de carga externa por
jogador (porta de tabela_carga_colorida em utils/ui_safe.py).
"""
import pandas as pd

from utils.calculos import calcular_acwr_global, cor_acwr

from app.services.dados_equipa import carregar_df_equipa

COLUNAS_CARGA = [
    {"col": "Distância Total (m)", "chave": "distancia_total_m", "label": "Dist. Total (m)", "cor": "#2563eb", "casas": 0},
    {"col": "HSR (m)", "chave": "hsr_m", "label": "HSR (m)", "cor": "#f59e0b", "casas": 0},
    {"col": "Sprint (m)", "chave": "sprint_m", "label": "Sprint (m)", "cor": "#dc2626", "casas": 0},
    {"col": "Acc (n)", "chave": "acc_n", "label": "Acelerações", "cor": "#14b8a6", "casas": 0},
    {"col": "Dcc (n)", "chave": "dcc_n", "label": "Desacelerações", "cor": "#10b981", "casas": 0},
    {"col": "Vel. Máx (km/h)", "chave": "vel_max_kmh", "label": "Vel. Máx (km/h)", "cor": "#8b5cf6", "casas": 1},
]


def obter_equipa(team_id: str) -> dict:
    df = carregar_df_equipa(team_id)
    if df.empty:
        return {"tem_dados": False, "acwr": [], "ci_evolucao": [], "load_profile": {"colunas": [], "linhas": []}}

    # ACWR por jogador (última sessão válida)
    acwr_dict = calcular_acwr_global(df)
    acwr_rows = []
    for jog, info in acwr_dict.items():
        v = info["acwr"]
        acwr_rows.append({
            "jogador": jog,
            "posicao": info.get("posicao", "—"),
            "acwr": round(float(v), 2) if pd.notna(v) else None,
            "estado": cor_acwr(v),
        })
    acwr_rows.sort(key=lambda r: (r["acwr"] is None, -(r["acwr"] or 0)))

    # Evolução da Carga Interna — últimos 6 microciclos
    ci_evolucao = []
    if "Carga Interna" in df.columns and "Microciclo (Nr)" in df.columns:
        mcs = sorted(df["Microciclo (Nr)"].dropna().unique())[-6:]
        for mc in mcs:
            media = df[df["Microciclo (Nr)"] == mc]["Carga Interna"].mean()
            if pd.notna(media):
                ci_evolucao.append({"microciclo": int(mc), "carga_interna_media": round(float(media), 0)})

    # Perfil de carga externa — colunas disponíveis nesta equipa
    colunas_disp = [c for c in COLUNAS_CARGA if c["col"] in df.columns and df[c["col"]].notna().any()]
    linhas = []
    if colunas_disp:
        agg = df.groupby("Jogador")[[c["col"] for c in colunas_disp]].mean()
        agg = agg.sort_values(colunas_disp[0]["col"], ascending=False)
        for jogador, row in agg.iterrows():
            valores = {}
            for c in colunas_disp:
                v = row[c["col"]]
                valores[c["chave"]] = round(float(v), c["casas"]) if pd.notna(v) else None
            linhas.append({"jogador": jogador, "valores": valores})

    return {
        "tem_dados": True,
        "acwr": acwr_rows,
        "ci_evolucao": ci_evolucao,
        "load_profile": {
            "colunas": [{"chave": c["chave"], "label": c["label"], "cor": c["cor"], "casas": c["casas"]} for c in colunas_disp],
            "linhas": linhas,
        },
    }
