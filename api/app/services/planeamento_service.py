"""Planeamento — Fase 7b do plano de migração (Treino vs Jogo).

Porta a lógica de "% vs Jogo" de app_pages/planeamento.py: para cada tipo de
Dia MD, compara a média de cada métrica de treino com a média das sessões
de Jogo (Tipo == "Jogo") — mesma referência que os alertas semáforo usavam
no Streamlit (utils/ui_safe.py::tabela_semaforo).
"""
import pandas as pd

from app.services.dados_equipa import carregar_df_equipa
from app.services.referencia_jogo import FONTE_MEDIA_90, FONTE_PICO, mascara_jogo, referencias_jogo

METRICAS_TVJ = ["Distância Total (m)", "HSR (m)", "Sprint (m)", "Acc (n)", "Dcc (n)", "Carga Interna"]

ORDEM_DIA_MD = ["MD-5", "MD-4", "MD-3", "MD-2", "MD-1", "MD", "MD+1", "MD+2"]


def _referencia_jogo(jogos: pd.DataFrame, metricas_disp: list[str], jogador: str | None = None) -> dict[str, float]:
    """Referência de jogo por métrica (ver referencia_jogo): média por 90' dos
    últimos jogos completos. Equipa = média das referências dos jogadores; com
    `jogador`, só a referência própria (vazio se ele não tiver jogos completos,
    para o chamador cair na da equipa)."""
    referencia = {}
    for met in metricas_disp:
        refs = referencias_jogo(jogos, met)
        if jogador is not None:
            r = refs.get(jogador)
            if r and r["fonte"] in (FONTE_MEDIA_90, FONTE_PICO) and r["valor"] > 0:
                referencia[met] = round(r["valor"], 1)
            continue
        proprios = [r["valor"] for r in refs.values() if r["fonte"] in (FONTE_MEDIA_90, FONTE_PICO)]
        if proprios:
            referencia[met] = round(float(sum(proprios) / len(proprios)), 1)
    return referencia


def obter_planeamento(team_id: str, jogador: str | None = None) -> dict:
    df = carregar_df_equipa(team_id)
    if df.empty or "Tipo" not in df.columns or "Dia MD" not in df.columns:
        return {"tem_dados": False, "tem_jogos": False, "referencia": {}, "dias": [], "evolucao_semanal": [], "metricas": [], "individual": False}

    metricas_disp = [m for m in METRICAS_TVJ if m in df.columns and df[m].notna().any()]
    if not metricas_disp:
        return {"tem_dados": True, "tem_jogos": False, "referencia": {}, "dias": [], "evolucao_semanal": [], "metricas": [], "individual": False}

    df_jogador = df[df["Jogador"] == jogador] if jogador else df

    # Referência individualizada: os jogos DESTE jogador — permite ver se
    # está a atingir a SUA própria intensidade de jogo habitual (não a da
    # equipa), útil sobretudo num plano de reintegração pós-lesão. Cai para
    # a referência da equipa se o jogador não tiver jogos suficientes
    # registados (ex: reforço recente).
    individual = False
    e_jogo = mascara_jogo(df)
    jogos = df[e_jogo]
    referencia = _referencia_jogo(jogos, metricas_disp, jogador) if not jogos.empty else {}
    if jogador and referencia:
        individual = True
    elif jogador:
        referencia = _referencia_jogo(jogos, metricas_disp)

    if not referencia:
        return {"tem_dados": True, "tem_jogos": False, "referencia": {}, "dias": [], "evolucao_semanal": [], "metricas": metricas_disp, "individual": False}

    treinos = df_jogador[~e_jogo.loc[df_jogador.index]]
    dias_presentes = [d for d in ORDEM_DIA_MD if d in treinos["Dia MD"].dropna().unique()]

    linhas = []
    for dia in dias_presentes:
        sub_dia = treinos[treinos["Dia MD"] == dia]
        valores_pct = {}
        for met in metricas_disp:
            if met not in referencia:
                continue
            media_dia = sub_dia.groupby("Data")[met].mean().mean()
            if pd.notna(media_dia):
                valores_pct[met] = round(float(media_dia) / referencia[met] * 100, 0)
        linhas.append({"dia_md": dia, "valores": valores_pct})

    # Evolução semanal — para cada microciclo, a carga total dessa semana
    # (soma de todos os dias de treino) em % de UM jogo — ex: 300% = a
    # equipa fez o equivalente a 3 jogos de distância total nessa semana.
    # É o que permite responder "o deload que planeei realmente aconteceu?":
    # basta comparar a semana atual com a anterior neste gráfico.
    evolucao_semanal = []
    if "Microciclo (Nr)" in treinos.columns and treinos["Microciclo (Nr)"].notna().any():
        for mc in sorted(treinos["Microciclo (Nr)"].dropna().unique()):
            sub_mc = treinos[treinos["Microciclo (Nr)"] == mc]
            valores_pct = {}
            for met in metricas_disp:
                if met not in referencia:
                    continue
                semanal_por_jogador = sub_mc.groupby("Jogador")[met].sum()
                if semanal_por_jogador.empty:
                    continue
                media_semanal = float(semanal_por_jogador.mean())
                valores_pct[met] = round(media_semanal / referencia[met] * 100, 0)
            if valores_pct:
                evolucao_semanal.append({"microciclo": int(mc), "valores": valores_pct})

    return {
        "tem_dados": True,
        "tem_jogos": True,
        "referencia": referencia,
        "dias": linhas,
        "evolucao_semanal": evolucao_semanal,
        "metricas": [m for m in metricas_disp if m in referencia],
        "individual": individual,
    }
