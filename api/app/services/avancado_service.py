"""Avançado — Fase 8 do plano de migração (Z-Score).

Reutiliza utils/calculos.py::zscore_serie tal como a app Streamlit
(app_pages/avancado.py) — compara cada jogador aos seus pares no
microciclo mais recente, em desvios-padrão.

Benchmarking por posição: comparar um central a um extremo pela média da
equipa toda distorce o sinal (têm perfis de carga muito diferentes). Por
isso, sempre que há pelo menos 2 jogadores com a mesma posição e dados
nessa métrica, o z-score é calculado dentro do grupo de posição — só cai
para a equipa toda quando a posição é desconhecida ou não há peers
suficientes para um desvio-padrão fazer sentido.
"""
import pandas as pd

from utils.calculos import zscore_serie

from app.services.dados_equipa import carregar_df_equipa

METRICAS_ZSCORE = ["Carga Interna", "Distância Total (m)", "HSR (m)", "Sprint (m)", "Vel. Máx (km/h)"]


def _grupos_comparacao(medias: pd.Series, posicoes: pd.Series | None) -> dict[str, str]:
    if posicoes is None:
        return {j: "equipa" for j in medias.index}
    contagem = posicoes.reindex(medias.index).value_counts()
    return {
        j: (posicoes.get(j) if posicoes.get(j) and contagem.get(posicoes.get(j), 0) >= 2 else "equipa")
        for j in medias.index
    }


def obter_avancado(team_id: str) -> dict:
    df = carregar_df_equipa(team_id)
    if df.empty:
        return {"tem_dados": False, "microciclo": None, "metricas": []}

    mc_recente = int(df["Microciclo (Nr)"].dropna().max()) if "Microciclo (Nr)" in df.columns and df["Microciclo (Nr)"].notna().any() else None
    df_mc = df[df["Microciclo (Nr)"] == mc_recente] if mc_recente is not None else df

    tem_posicao = "Posição" in df_mc.columns and df_mc["Posição"].notna().any()
    posicoes = df_mc.dropna(subset=["Posição"]).groupby("Jogador")["Posição"].last() if tem_posicao else None

    resultado_metricas = []
    for metrica in METRICAS_ZSCORE:
        if metrica not in df_mc.columns or not df_mc[metrica].notna().any():
            continue
        medias = df_mc.groupby("Jogador")[metrica].mean().dropna()
        if len(medias) < 2:
            continue

        grupos = _grupos_comparacao(medias, posicoes)
        zscores = pd.concat([
            zscore_serie(medias.loc[[j for j, g in grupos.items() if g == grupo]])
            for grupo in set(grupos.values())
        ]).sort_values(ascending=False)

        resultado_metricas.append({
            "metrica": metrica,
            "jogadores": [
                {
                    "jogador": j, "valor": round(float(medias[j]), 1), "zscore": round(float(z), 2),
                    "grupo_comparacao": grupos[j],
                }
                for j, z in zscores.items()
            ],
        })

    return {"tem_dados": True, "microciclo": mc_recente, "metricas": resultado_metricas}
