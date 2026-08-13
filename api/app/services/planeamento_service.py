"""Planeamento — Fase 7b do plano de migração (Treino vs Jogo).

Porta a lógica de "% vs Jogo" de app_pages/planeamento.py: para cada tipo de
Dia MD, compara a média de cada métrica de treino com a média das sessões
de Jogo (Tipo == "Jogo") — mesma referência que os alertas semáforo usavam
no Streamlit (utils/ui_safe.py::tabela_semaforo).
"""
import pandas as pd

from app.services.dados_equipa import carregar_df_equipa

METRICAS_TVJ = ["Distância Total (m)", "HSR (m)", "Sprint (m)", "Carga Interna"]

ORDEM_DIA_MD = ["MD-5", "MD-4", "MD-3", "MD-2", "MD-1", "MD", "MD+1", "MD+2"]


def _referencia_jogo(jogos: pd.DataFrame, metricas_disp: list[str]) -> dict[str, float]:
    # Média por sessão de jogo (soma por jogador+data, depois média entre
    # jogos) — equivalente à "média de jogos" do Streamlit.
    referencia = {}
    for met in metricas_disp:
        media_jogo = jogos.groupby("Data")[met].mean().mean()
        if pd.notna(media_jogo) and media_jogo > 0:
            referencia[met] = round(float(media_jogo), 1)
    return referencia


def obter_planeamento(team_id: str, jogador: str | None = None) -> dict:
    df = carregar_df_equipa(team_id)
    if df.empty or "Tipo" not in df.columns or "Dia MD" not in df.columns:
        return {"tem_dados": False, "tem_jogos": False, "referencia": {}, "dias": [], "metricas": [], "individual": False}

    metricas_disp = [m for m in METRICAS_TVJ if m in df.columns and df[m].notna().any()]
    if not metricas_disp:
        return {"tem_dados": True, "tem_jogos": False, "referencia": {}, "dias": [], "metricas": [], "individual": False}

    df_jogador = df[df["Jogador"] == jogador] if jogador else df

    # Referência individualizada: os jogos DESTE jogador — permite ver se
    # está a atingir a SUA própria intensidade de jogo habitual (não a da
    # equipa), útil sobretudo num plano de reintegração pós-lesão. Cai para
    # a referência da equipa se o jogador não tiver jogos suficientes
    # registados (ex: reforço recente).
    individual = False
    jogos = df_jogador[df_jogador["Tipo"] == "Jogo"] if jogador else df[df["Tipo"] == "Jogo"]
    referencia = _referencia_jogo(jogos, metricas_disp) if not jogos.empty else {}
    if jogador and referencia:
        individual = True
    elif jogador:
        jogos = df[df["Tipo"] == "Jogo"]
        referencia = _referencia_jogo(jogos, metricas_disp)

    if not referencia:
        return {"tem_dados": True, "tem_jogos": False, "referencia": {}, "dias": [], "metricas": metricas_disp, "individual": False}

    treinos = df_jogador[df_jogador["Tipo"] != "Jogo"]
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

    return {
        "tem_dados": True,
        "tem_jogos": True,
        "referencia": referencia,
        "dias": linhas,
        "metricas": [m for m in metricas_disp if m in referencia],
        "individual": individual,
    }
