"""Resumo da sessão — modelo 5W+1H.

Baseado no curso "O Uso do GPS no Futebol — Dos Dados à Ação" (S. Querido):
dados brutos só viram comunicação útil quando ganham Contexto (o Dia MD em
que aconteceram) e Significado (comparação com sessões semelhantes) — não
apenas quando são mostrados como números soltos. Este módulo aplica a
técnica 5W+1H (Who/What/Where/When/Why/How) à sessão mais recente, com
comparação real à média histórica de sessões do mesmo tipo de Dia MD.

Substitui/porta o "PERFIL_DIA_MD" e a lógica de recomendação que viviam
embutidos em app_pages/dashboard.py (linhas ~200-230) na app Streamlit.
"""
import pandas as pd

# Foco/intensidade típicos por dia do microciclo — mesma tabela que a app
# Streamlit usava para gerar as recomendações do dia.
PERFIL_DIA_MD = {
    "MD-5": {"foco": "carga física elevada", "intensidade": "alta"},
    "MD-4": {"foco": "trabalho técnico-tático", "intensidade": "média"},
    "MD-3": {"foco": "jogos reduzidos competitivos", "intensidade": "alta"},
    "MD-2": {"foco": "manutenção de velocidade e ativação", "intensidade": "média"},
    "MD-1": {"foco": "ativação neuromuscular pré-jogo", "intensidade": "baixa"},
    "MD": {"foco": "jogo oficial", "intensidade": "máxima"},
    "MD+1": {"foco": "recuperação ativa", "intensidade": "recuperação"},
    "MD+2": {"foco": "regeneração e mobilidade", "intensidade": "baixa"},
}

METRICAS_RESUMO = ["Carga Interna", "Distância Total (m)", "HSR (m)", "Sprint (m)"]


def gerar_resumo_5w1h(df: pd.DataFrame) -> dict | None:
    if df.empty or "Data" not in df.columns or "Jogador" not in df.columns:
        return None

    ultima_data = df["Data"].dropna().max()
    if pd.isna(ultima_data):
        return None

    sessao = df[df["Data"] == ultima_data]
    if sessao.empty:
        return None

    dia_md = None
    if "Dia MD" in sessao.columns:
        moda = sessao["Dia MD"].dropna().mode()
        dia_md = moda.iloc[0] if not moda.empty else None
    perfil = PERFIL_DIA_MD.get(dia_md, {})

    jogadores = sorted(j for j in sessao["Jogador"].dropna().unique().tolist())

    # O quê / Como — comparação com a média histórica de sessões do MESMO
    # tipo de Dia MD (não a média geral), para que a % faça sentido: uma
    # sessão MD-1 nunca deve ser comparada a uma MD-3.
    comparacoes = []
    for metrica in METRICAS_RESUMO:
        if metrica not in sessao.columns:
            continue
        valor_sessao = sessao[metrica].mean()
        if pd.isna(valor_sessao):
            continue

        if dia_md and "Dia MD" in df.columns:
            historico = df[(df["Dia MD"] == dia_md) & (df["Data"] != ultima_data)][metrica]
        else:
            historico = df[df["Data"] != ultima_data][metrica] if metrica in df.columns else pd.Series(dtype=float)
        media_hist = historico.mean() if not historico.empty else None
        media_hist = float(media_hist) if media_hist is not None and pd.notna(media_hist) else None

        variacao_pct = None
        if media_hist and media_hist > 0:
            variacao_pct = round((float(valor_sessao) - media_hist) / media_hist * 100, 0)

        comparacoes.append({
            "metrica": metrica,
            "valor": round(float(valor_sessao), 1),
            "media_historica": round(media_hist, 1) if media_hist is not None else None,
            "variacao_pct": variacao_pct,
        })

    return {
        "data": ultima_data.date().isoformat(),
        "dia_md": dia_md,
        "who": {"n_jogadores": len(jogadores), "jogadores": jogadores},
        "where": "Jogo oficial" if dia_md == "MD" else "Sessão de treino",
        "why": perfil.get("foco", "monitorização de carga"),
        "how": perfil.get("intensidade", "—"),
        "what": comparacoes,
    }
