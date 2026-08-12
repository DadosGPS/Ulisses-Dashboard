"""LoadMonitorSystem — Cálculos científicos"""
import pandas as pd
import numpy as np

# ── Streamlit — importação tolerante (ver utils/dados.py para o mesmo padrão) ─
try:
    import streamlit as st
    cache_data = st.cache_data
except ImportError:
    def cache_data(*dargs, **dkwargs):
        def _decorator(func):
            return func
        return _decorator


@cache_data(ttl=600, show_spinner=False)
def calcular_acwr(df: pd.DataFrame, jogador: str) -> pd.DataFrame:
    """ACWR EWMA por jogador — λ aguda=0.25, λ crónica=2/29.

    Mantida para compatibilidade com chamadas existentes no código
    (ex: app_pages/avancado.py linha 705). Para cálculo de toda a
    equipa de uma só vez, usar `calcular_acwr_global` (vetorizado).
    """
    # Guards iniciais — proteger contra df vazio ou sem colunas necessárias
    if df.empty or "Jogador" not in df.columns or "Data" not in df.columns:
        return pd.DataFrame()
    sub = df[df["Jogador"] == jogador].sort_values("Data").copy()
    if sub.empty or "Carga Interna" not in sub.columns:
        return pd.DataFrame()
    sub = sub.dropna(subset=["Carga Interna", "Data"])
    if sub.empty:
        return pd.DataFrame()
    sub["Carga Aguda"]   = sub["Carga Interna"].ewm(alpha=0.25, adjust=False).mean()
    sub["Carga Crónica"] = sub["Carga Interna"].ewm(alpha=2/29, adjust=False).mean()
    sub["ACWR"] = np.where(sub["Carga Crónica"] > 0,
                           sub["Carga Aguda"] / sub["Carga Crónica"], np.nan)
    return sub[["Data", "Jogador", "Carga Interna", "Carga Aguda", "Carga Crónica", "ACWR"]]


@cache_data(ttl=600, show_spinner=False)
def calcular_acwr_global(df_base: pd.DataFrame) -> dict:
    """Calcula ACWR para todos os jogadores. Retorna dict jogador→info completa.

    VERSÃO VETORIZADA — calcula EWMA para todos os jogadores numa só
    passagem usando groupby().transform(), em vez de loop por jogador.
    Resultado idêntico ao loop original mas 10-100x mais rápido para
    plantéis grandes.

    Estrutura do dict por jogador (mantida igual à versão anterior):
        {
            "acwr":       float,    # ACWR mais recente
            "posicao":    str,      # Posição do jogador (ou "—")
            "data":       Timestamp,# Data da última sessão com ACWR válido
            "ci_agudo":   float,    # Carga aguda (EWMA λ=0.25) na última sessão
            "ci_cronico": float,    # Carga crónica (EWMA λ=2/29) na última sessão
        }

    Páginas dependem destes campos (dashboard.py linha 28 lê 'posicao', etc).
    """
    resultado: dict = {}
    if df_base.empty or "Jogador" not in df_base.columns:
        return resultado
    if "Carga Interna" not in df_base.columns or "Data" not in df_base.columns:
        return resultado

    # Preparar DF — ordenar por jogador+data e remover NaN
    sub = df_base.dropna(subset=["Carga Interna", "Data", "Jogador"]).copy()
    if sub.empty:
        return resultado
    sub = sub.sort_values(["Jogador", "Data"])

    # EWMA vetorizado por jogador (groupby + transform)
    grp = sub.groupby("Jogador", sort=False)["Carga Interna"]
    sub["Carga Aguda"]   = grp.transform(lambda x: x.ewm(alpha=0.25, adjust=False).mean())
    sub["Carga Crónica"] = grp.transform(lambda x: x.ewm(alpha=2/29, adjust=False).mean())
    sub["ACWR"] = np.where(sub["Carga Crónica"] > 0,
                           sub["Carga Aguda"] / sub["Carga Crónica"], np.nan)

    # Última entrada válida por jogador (= maior Data com ACWR != NaN)
    validos = sub.dropna(subset=["ACWR"])
    if validos.empty:
        return resultado

    # idxmax devolve o índice da última data por jogador (já ordenado)
    last_idx = validos.groupby("Jogador", sort=False).tail(1).set_index("Jogador")

    # Posições — mapeamento jogador→última posição registada
    pos_map: dict = {}
    if "Posição" in df_base.columns:
        df_pos = df_base.dropna(subset=["Jogador"]).copy()
        # Última posição não-nula por jogador
        df_pos_valido = df_pos.dropna(subset=["Posição"])
        if not df_pos_valido.empty:
            pos_map = (df_pos_valido.groupby("Jogador", sort=False)["Posição"]
                       .last().to_dict())

    for jog, last in last_idx.iterrows():
        resultado[jog] = {
            "acwr":       last["ACWR"],
            "posicao":    pos_map.get(jog, "—"),
            "data":       last["Data"],
            "ci_agudo":   last["Carga Aguda"],
            "ci_cronico": last["Carga Crónica"],
        }
    return resultado


def zscore_serie(serie: pd.Series) -> pd.Series:
    if serie.dropna().std() == 0:
        return pd.Series(0, index=serie.index)
    return (serie - serie.mean()) / serie.std()


def cor_acwr(v) -> str:
    """Retorna emoji + texto (e.g. '🔴 RISCO') para classificação ACWR.

    Páginas dependem do texto: usam `"RISCO" in estado` para classificar alertas.
    Não alterar o formato sem actualizar dashboard.py, equipa.py, sistema.py.
    """
    if pd.isna(v):      return "❓"
    if v >= 1.5:        return "🔴 RISCO"
    if v >= 1.3:        return "🟡 ATENÇÃO"
    if v >= 0.8:        return "🟢 OK"
    return "🔵 SUB-CARGA"


# Ordem canónica dos dias de um microciclo — mesma usada em
# app/services/resumo_5w1h.py (PERFIL_DIA_MD), duplicada aqui por
# utils/calculos.py ser um módulo puro (sem depender de app/).
DIAS_MD_ORDEM = ["MD-5", "MD-4", "MD-3", "MD-2", "MD-1", "MD", "MD+1", "MD+2"]


@cache_data(ttl=600, show_spinner=False)
def calcular_monotonia_strain(df_base: pd.DataFrame) -> pd.DataFrame:
    """Foster (1998) — Monotonia e Strain por jogador e microciclo.

    Trata cada microciclo como uma semana de 7 dias: usa os dias de "Dia MD"
    que a equipa costuma registar (ex: MD-5..MD), preenche com carga 0 os
    dias sem sessão registada (dia de folga) até perfazer 7 dias — sem isto
    a monotonia fica inflacionada, porque o dia de folga faz parte da
    variabilidade real da carga semanal, não é "ausência de dado".

    Monotonia = média das 7 cargas diárias ÷ desvio-padrão AMOSTRAL (ddof=1)
    dessas 7 cargas. Strain = carga semanal total × monotonia.
    """
    if df_base.empty or "Carga Interna" not in df_base.columns:
        return pd.DataFrame()
    obrigatorias = {"Microciclo (Nr)", "Jogador", "Dia MD"}
    if not obrigatorias.issubset(df_base.columns):
        return pd.DataFrame()

    sub = df_base.dropna(subset=["Carga Interna", "Jogador", "Microciclo (Nr)", "Dia MD"]).copy()
    if sub.empty:
        return pd.DataFrame()

    resultados = []
    for mc, g_mc in sub.groupby("Microciclo (Nr)", sort=False):
        # Dias que esta equipa registou neste microciclo, na ordem certa —
        # os que faltam até perfazer 7 são o(s) dia(s) de folga (carga 0).
        dias_semana = [d for d in DIAS_MD_ORDEM if d in set(g_mc["Dia MD"])]
        n_dias = max(7, len(dias_semana))
        n_folga = n_dias - len(dias_semana)

        for jogador, g_jog in g_mc.groupby("Jogador", sort=False):
            cargas_dia = g_jog.groupby("Dia MD")["Carga Interna"].sum().reindex(dias_semana).fillna(0.0)
            cargas_semana = np.append(cargas_dia.to_numpy(dtype=float), np.zeros(n_folga))

            soma = float(cargas_semana.sum())
            media = soma / n_dias
            dp = float(np.std(cargas_semana, ddof=1)) if n_dias > 1 else 0.0
            monotonia = media / dp if dp > 0 else 0.0
            strain = soma * monotonia

            resultados.append({
                "Jogador": jogador,
                "Microciclo (Nr)": mc,
                "Carga Semanal Total": round(soma, 0),
                "Monotonia": round(monotonia, 2),
                "Strain": round(strain, 0),
            })

    if not resultados:
        return pd.DataFrame()
    return pd.DataFrame(resultados).sort_values(["Jogador", "Microciclo (Nr)"]).reset_index(drop=True)
