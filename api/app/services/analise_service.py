"""Análise — substitui o antigo "Dashboard" (reestruturação pedida pelo
utilizador). Foco em carga semanal/diária e monotonia/strain corretos
(ver utils/calculos.calcular_monotonia_strain), não em ACWR/alertas.
"""
import pandas as pd

from utils.calculos import DIAS_MD_ORDEM, calcular_monotonia_strain

from app.services.dados_equipa import carregar_df_equipa


def obter_analise(team_id: str, microciclo: int | None = None, dia_md: str | None = None) -> dict:
    df = carregar_df_equipa(team_id)
    if df.empty:
        return {"tem_dados": False}

    tem_microciclo = "Microciclo (Nr)" in df.columns and df["Microciclo (Nr)"].notna().any()
    microciclos_disponiveis = sorted(df["Microciclo (Nr)"].dropna().astype(int).unique().tolist()) if tem_microciclo else []
    mc_recente = microciclos_disponiveis[-1] if microciclos_disponiveis else None
    mc_selecionado = microciclo if (microciclo is not None and microciclo in microciclos_disponiveis) else mc_recente
    df_semana = df[df["Microciclo (Nr)"] == mc_selecionado] if mc_selecionado is not None else df

    dias_md_disponiveis = []
    if "Dia MD" in df_semana.columns:
        presentes = set(df_semana["Dia MD"].dropna().unique().tolist())
        dias_md_disponiveis = [d for d in DIAS_MD_ORDEM if d in presentes]
    dia_md_selecionado = dia_md if dia_md in dias_md_disponiveis else None

    # Base de cálculo do KPI principal, do máximo/mínimo e do ranking: com
    # "Todos os dias" é a carga semanal total por atleta (soma); com um dia
    # específico escolhido, é a carga desse dia por atleta (soma também,
    # para cobrir o caso raro de 2 sessões no mesmo dia) — o pedido do
    # utilizador é explícito quanto a isto não poder ser "média por sessão".
    df_base = df_semana if not dia_md_selecionado else df_semana[df_semana["Dia MD"] == dia_md_selecionado]
    carga_por_atleta = (
        df_base.dropna(subset=["Carga Interna", "Jogador"]).groupby("Jogador")["Carga Interna"].sum()
        if "Carga Interna" in df_base.columns else pd.Series(dtype=float)
    )

    carga_interna_media = float(carga_por_atleta.mean()) if not carga_por_atleta.empty else None

    carga_maxima = carga_minima = None
    if not carga_por_atleta.empty:
        carga_maxima = {"jogador": carga_por_atleta.idxmax(), "valor": round(float(carga_por_atleta.max()), 0)}
        carga_minima = {"jogador": carga_por_atleta.idxmin(), "valor": round(float(carga_por_atleta.min()), 0)}

    ranking_carga = [
        {"jogador": j, "valor": round(float(v), 0)}
        for j, v in carga_por_atleta.sort_values(ascending=False).items()
    ]

    # Carga e PSE médias por dia — sempre a semana inteira (dá contexto ao
    # microciclo mesmo quando um dia específico está selecionado no filtro).
    carga_por_dia, pse_por_dia = [], []
    if "Dia MD" in df_semana.columns:
        if "Carga Interna" in df_semana.columns:
            media_dia = df_semana.dropna(subset=["Carga Interna", "Dia MD"]).groupby("Dia MD")["Carga Interna"].mean()
            carga_por_dia = [
                {"dia_md": d, "carga_media": round(float(media_dia[d]), 0)}
                for d in dias_md_disponiveis if d in media_dia.index
            ]
        if "PSE Sessão" in df_semana.columns:
            media_pse = df_semana.dropna(subset=["PSE Sessão", "Dia MD"]).groupby("Dia MD")["PSE Sessão"].mean()
            pse_por_dia = [
                {"dia_md": d, "pse_media": round(float(media_pse[d]), 1)}
                for d in dias_md_disponiveis if d in media_pse.index
            ]

    # Monotonia/Strain são sempre conceitos semanais — não fazem sentido
    # para um único dia, por isso ignoram o filtro de Dia MD.
    monotonia_media = strain_medio = None
    mono = calcular_monotonia_strain(df_semana)
    if not mono.empty:
        monotonia_media = round(float(mono["Monotonia"].mean()), 2)
        strain_medio = round(float(mono["Strain"].mean()), 0)

    return {
        "tem_dados": True,
        "microciclo_recente": mc_recente,
        "microciclo_selecionado": mc_selecionado,
        "microciclos_disponiveis": microciclos_disponiveis,
        "dia_md_selecionado": dia_md_selecionado,
        "dias_md_disponiveis": dias_md_disponiveis,
        "carga_interna_media": round(carga_interna_media, 0) if carga_interna_media is not None else None,
        "carga_maxima": carga_maxima,
        "carga_minima": carga_minima,
        "carga_por_dia": carga_por_dia,
        "pse_por_dia": pse_por_dia,
        "monotonia_media": monotonia_media,
        "strain_medio": strain_medio,
        "ranking_carga": ranking_carga,
    }
