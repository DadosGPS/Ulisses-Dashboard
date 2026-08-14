"""Equipa — Fase 6 do plano de migração.

Reutiliza utils/calculos.py (ACWR) tal como o dashboard; acrescenta a
evolução de Carga Interna por microciclo e o perfil de carga externa por
jogador (porta de tabela_carga_colorida em utils/ui_safe.py).
"""
import pandas as pd

from utils.calculos import calcular_acwr_global, calcular_monotonia_strain, cor_acwr

from app.services.dados_equipa import carregar_df_equipa

COLUNAS_CARGA = [
    {"col": "Distância Total (m)", "chave": "distancia_total_m", "label": "Dist. Total (m)", "cor": "#2563eb", "casas": 0},
    {"col": "HSR (m)", "chave": "hsr_m", "label": "HSR (m)", "cor": "#f59e0b", "casas": 0},
    {"col": "Sprint (m)", "chave": "sprint_m", "label": "Sprint (m)", "cor": "#dc2626", "casas": 0},
    {"col": "Acc (n)", "chave": "acc_n", "label": "Acelerações", "cor": "#14b8a6", "casas": 0},
    {"col": "Dcc (n)", "chave": "dcc_n", "label": "Desacelerações", "cor": "#10b981", "casas": 0},
    {"col": "Vel. Máx (km/h)", "chave": "vel_max_kmh", "label": "Vel. Máx (km/h)", "cor": "#8b5cf6", "casas": 1},
]


def obter_equipa(team_id: str, micro_inicio: int | None = None, micro_fim: int | None = None) -> dict:
    df = carregar_df_equipa(team_id)
    if df.empty:
        return {
            "tem_dados": False, "acwr": [], "ci_evolucao": [], "monotonia_evolucao": [],
            "carga_externa_evolucao": {}, "microciclos_disponiveis": [], "load_profile": {"colunas": [], "linhas": []},
        }

    # ACWR por jogador (última sessão válida) — usa sempre o histórico
    # completo, não é afetado pelo intervalo escolhido para os gráficos de
    # evolução (é sempre "o estado agora", não um retrato de uma janela).
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

    tem_microciclo = "Microciclo (Nr)" in df.columns and df["Microciclo (Nr)"].notna().any()
    microciclos_disponiveis = sorted(df["Microciclo (Nr)"].dropna().astype(int).unique().tolist()) if tem_microciclo else []

    # Intervalo de tempo opcional — por omissão mostra a época toda; o
    # utilizador pode escolher uma janela (ex: só o mês de pré-época) nos
    # três gráficos de evolução abaixo (carga interna, monotonia, carga
    # externa por métrica), todos filtrados pelo mesmo intervalo.
    df_intervalo = df
    if tem_microciclo and (micro_inicio is not None or micro_fim is not None):
        lo = micro_inicio if micro_inicio is not None else microciclos_disponiveis[0]
        hi = micro_fim if micro_fim is not None else microciclos_disponiveis[-1]
        df_intervalo = df[(df["Microciclo (Nr)"] >= lo) & (df["Microciclo (Nr)"] <= hi)]

    # Evolução da Carga Interna.
    ci_evolucao = []
    if "Carga Interna" in df_intervalo.columns and tem_microciclo:
        mcs = sorted(df_intervalo["Microciclo (Nr)"].dropna().unique())
        for mc in mcs:
            media = df_intervalo[df_intervalo["Microciclo (Nr)"] == mc]["Carga Interna"].mean()
            if pd.notna(media):
                ci_evolucao.append({"microciclo": int(mc), "carga_interna_media": round(float(media), 0)})

    # Evolução da Monotonia — média da equipa por microciclo.
    monotonia_evolucao = []
    mono = calcular_monotonia_strain(df_intervalo)
    if not mono.empty:
        for mc, g in mono.groupby("Microciclo (Nr)"):
            monotonia_evolucao.append({"microciclo": int(mc), "monotonia_media": round(float(g["Monotonia"].mean()), 2)})
        monotonia_evolucao.sort(key=lambda x: x["microciclo"])

    # Evolução da Carga Externa — um traçado por métrica, mesma janela.
    carga_externa_evolucao: dict[str, list[dict]] = {}
    if tem_microciclo:
        for c in COLUNAS_CARGA:
            if c["col"] not in df_intervalo.columns or not df_intervalo[c["col"]].notna().any():
                continue
            pontos = []
            for mc, g in df_intervalo.dropna(subset=[c["col"]]).groupby("Microciclo (Nr)"):
                pontos.append({"microciclo": int(mc), "valor": round(float(g[c["col"]].mean()), c["casas"])})
            if pontos:
                pontos.sort(key=lambda x: x["microciclo"])
                carga_externa_evolucao[c["chave"]] = pontos

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
        "monotonia_evolucao": monotonia_evolucao,
        "carga_externa_evolucao": carga_externa_evolucao,
        "microciclos_disponiveis": microciclos_disponiveis,
        "load_profile": {
            "colunas": [{"chave": c["chave"], "label": c["label"], "cor": c["cor"], "casas": c["casas"]} for c in colunas_disp],
            "linhas": linhas,
        },
    }
