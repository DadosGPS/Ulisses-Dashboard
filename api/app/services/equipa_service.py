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


def _serie_ci(d: pd.DataFrame) -> list[dict]:
    """Carga Interna média por microciclo, no DataFrame dado."""
    out: list[dict] = []
    if "Carga Interna" not in d.columns or "Microciclo (Nr)" not in d.columns:
        return out
    for mc in sorted(d["Microciclo (Nr)"].dropna().unique()):
        media = d[d["Microciclo (Nr)"] == mc]["Carga Interna"].mean()
        if pd.notna(media):
            out.append({"microciclo": int(mc), "carga_interna_media": round(float(media), 0)})
    return out


def _serie_monotonia(d: pd.DataFrame) -> list[dict]:
    """Monotonia média por microciclo (para um jogador, é a monotonia dele)."""
    out: list[dict] = []
    mono = calcular_monotonia_strain(d)
    if not mono.empty:
        for mc, g in mono.groupby("Microciclo (Nr)"):
            out.append({"microciclo": int(mc), "monotonia_media": round(float(g["Monotonia"].mean()), 2)})
        out.sort(key=lambda x: x["microciclo"])
    return out


def _serie_externa(d: pd.DataFrame) -> dict[str, list[dict]]:
    """Um traçado por métrica de carga externa (média por microciclo)."""
    res: dict[str, list[dict]] = {}
    if "Microciclo (Nr)" not in d.columns:
        return res
    for c in COLUNAS_CARGA:
        if c["col"] not in d.columns or not d[c["col"]].notna().any():
            continue
        pontos = []
        for mc, g in d.dropna(subset=[c["col"]]).groupby("Microciclo (Nr)"):
            pontos.append({"microciclo": int(mc), "valor": round(float(g[c["col"]].mean()), c["casas"])})
        if pontos:
            pontos.sort(key=lambda x: x["microciclo"])
            res[c["chave"]] = pontos
    return res


def obter_equipa(team_id: str, micro_inicio: int | None = None, micro_fim: int | None = None,
                 jogador: str | None = None) -> dict:
    df = carregar_df_equipa(team_id)
    if df.empty:
        return {
            "tem_dados": False, "acwr": [], "acwr_intervalo": {"inicio": None, "fim": None, "n_semanas": 0},
            "acwr_poucas_semanas": False, "ci_evolucao": [], "monotonia_evolucao": [],
            "carga_externa_evolucao": {}, "ci_evolucao_jogador": [], "monotonia_evolucao_jogador": [],
            "carga_externa_evolucao_jogador": {}, "jogadores_disponiveis": [], "jogador_selecionado": None,
            "microciclos_disponiveis": [], "load_profile": {"colunas": [], "linhas": []},
        }

    tem_microciclo = "Microciclo (Nr)" in df.columns and df["Microciclo (Nr)"].notna().any()
    microciclos_disponiveis = sorted(df["Microciclo (Nr)"].dropna().astype(int).unique().tolist()) if tem_microciclo else []

    # Intervalo de semanas (microciclos) escolhido — por omissão a época toda.
    # Governa TODA a página Época: o ACWR e os gráficos de evolução usam o mesmo
    # intervalo, para o utilizador ter a certeza de que semanas está a ver.
    df_intervalo = df
    if tem_microciclo and (micro_inicio is not None or micro_fim is not None):
        lo = micro_inicio if micro_inicio is not None else microciclos_disponiveis[0]
        hi = micro_fim if micro_fim is not None else microciclos_disponiveis[-1]
        df_intervalo = df[(df["Microciclo (Nr)"] >= lo) & (df["Microciclo (Nr)"] <= hi)]

    # ACWR por jogador (última sessão válida) — calculado SÓ com as semanas do
    # intervalo escolhido. Como a carga crónica (EWMA ~4 semanas) precisa de
    # histórico, sinalizamos quando o intervalo tem poucas semanas.
    micros_no_intervalo = (
        sorted(df_intervalo["Microciclo (Nr)"].dropna().astype(int).unique().tolist())
        if tem_microciclo else []
    )
    acwr_dict = calcular_acwr_global(df_intervalo)
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

    acwr_intervalo = {
        "inicio": micros_no_intervalo[0] if micros_no_intervalo else None,
        "fim": micros_no_intervalo[-1] if micros_no_intervalo else None,
        "n_semanas": len(micros_no_intervalo),
    }
    acwr_poucas_semanas = bool(tem_microciclo and 0 < len(micros_no_intervalo) < 4)

    # Evolução da equipa (média por microciclo) — a referência de fundo.
    ci_evolucao = _serie_ci(df_intervalo) if tem_microciclo else []
    monotonia_evolucao = _serie_monotonia(df_intervalo) if tem_microciclo else []
    carga_externa_evolucao = _serie_externa(df_intervalo) if tem_microciclo else {}

    # Jogador selecionado (opcional) — sobrepõe a evolução individual à média da
    # equipa, para se ver este atleta vs o coletivo. A média esconde picos e
    # quedas individuais, que é precisamente o que interessa na monitorização.
    jogadores_disponiveis = sorted(df["Jogador"].dropna().unique().tolist()) if "Jogador" in df.columns else []
    jogador_selecionado = jogador if (jogador and jogador in jogadores_disponiveis) else None

    ci_evolucao_jogador: list[dict] = []
    monotonia_evolucao_jogador: list[dict] = []
    carga_externa_evolucao_jogador: dict[str, list[dict]] = {}
    if jogador_selecionado and tem_microciclo:
        dj = df_intervalo[df_intervalo["Jogador"] == jogador_selecionado]
        ci_evolucao_jogador = _serie_ci(dj)
        monotonia_evolucao_jogador = _serie_monotonia(dj)
        carga_externa_evolucao_jogador = _serie_externa(dj)

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
        "acwr_intervalo": acwr_intervalo,
        "acwr_poucas_semanas": acwr_poucas_semanas,
        "ci_evolucao": ci_evolucao,
        "monotonia_evolucao": monotonia_evolucao,
        "carga_externa_evolucao": carga_externa_evolucao,
        "ci_evolucao_jogador": ci_evolucao_jogador,
        "monotonia_evolucao_jogador": monotonia_evolucao_jogador,
        "carga_externa_evolucao_jogador": carga_externa_evolucao_jogador,
        "jogadores_disponiveis": jogadores_disponiveis,
        "jogador_selecionado": jogador_selecionado,
        "microciclos_disponiveis": microciclos_disponiveis,
        "load_profile": {
            "colunas": [{"chave": c["chave"], "label": c["label"], "cor": c["cor"], "casas": c["casas"]} for c in colunas_disp],
            "linhas": linhas,
        },
    }
