"""LoadMonitorSystem — Cálculos científicos"""
import pandas as pd
import numpy as np
import streamlit as st

@st.cache_data(ttl=600, show_spinner=False)
def calcular_acwr(df: pd.DataFrame, jogador: str) -> pd.DataFrame:
    """ACWR EWMA por jogador — λ aguda=0.25, λ crónica=2/29"""
    # Guards iniciais — proteger contra df vazio ou sem colunas necessárias
    if df.empty or "Jogador" not in df.columns or "Data" not in df.columns:
        return pd.DataFrame()
    sub = df[df["Jogador"] == jogador].sort_values("Data").copy()
    if sub.empty or "Carga Interna" not in sub.columns:
        return pd.DataFrame()
    sub = sub.dropna(subset=["Carga Interna","Data"])
    if sub.empty: return pd.DataFrame()
    sub["Carga Aguda"]   = sub["Carga Interna"].ewm(alpha=0.25,   adjust=False).mean()
    sub["Carga Crónica"] = sub["Carga Interna"].ewm(alpha=2/29,   adjust=False).mean()
    sub["ACWR"] = np.where(sub["Carga Crónica"] > 0,
                           sub["Carga Aguda"] / sub["Carga Crónica"], np.nan)
    return sub[["Data","Jogador","Carga Interna","Carga Aguda","Carga Crónica","ACWR"]]

def calcular_acwr_global(df_base: pd.DataFrame) -> dict:
    """Calcula ACWR para todos os jogadores. Retorna dict jogador→info completa.
    
    Estrutura do dict por jogador:
        {
            "acwr":       float,    # ACWR mais recente
            "posicao":    str,      # Posição do jogador (ou "—")
            "data":       Timestamp,# Data da última sessão com ACWR válido
            "ci_agudo":   float,    # Carga aguda (EWMA λ=0.25) na última sessão
            "ci_cronico": float,    # Carga crónica (EWMA λ=2/29) na última sessão
        }
    
    Páginas dependem destes campos (dashboard.py linha 28 lê 'posicao', etc).
    """
    resultado = {}
    if df_base.empty or "Jogador" not in df_base.columns:
        return resultado
    for jog in df_base["Jogador"].dropna().unique():
        acwr_df = calcular_acwr(df_base, jog)
        if acwr_df.empty or "ACWR" not in acwr_df.columns:
            continue
        validos = acwr_df.dropna(subset=["ACWR"])
        if validos.empty:
            continue
        last = validos.iloc[-1]
        # Posição: vem do df_base original (calcular_acwr não a inclui no return)
        sub_jog = df_base[df_base["Jogador"] == jog]
        posicao = "—"
        if "Posição" in sub_jog.columns:
            pos_vals = sub_jog["Posição"].dropna()
            if not pos_vals.empty:
                posicao = pos_vals.iloc[-1]
        resultado[jog] = {
            "acwr":       last["ACWR"],
            "posicao":    posicao,
            "data":       last["Data"],
            "ci_agudo":   last.get("Carga Aguda", 0),
            "ci_cronico": last.get("Carga Crónica", 0),
        }
    return resultado

def zscore_serie(serie: pd.Series) -> pd.Series:
    if serie.dropna().std() == 0: return pd.Series(0, index=serie.index)
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

def calcular_monotonia_strain(df_base: pd.DataFrame) -> pd.DataFrame:
    """Foster (1998) — Monotonia e Strain por jogador e microciclo"""
    if df_base.empty or "Carga Interna" not in df_base.columns: return pd.DataFrame()
    rows = []
    for jog in sorted(df_base["Jogador"].dropna().unique()):
        df_jog = df_base[df_base["Jogador"] == jog]
        for mc in sorted(df_jog["Microciclo (Nr)"].dropna().unique()):
            sub = df_jog[df_jog["Microciclo (Nr)"] == mc]["Carga Interna"].dropna()
            if len(sub) < 2: continue
            media = sub.mean(); dp = sub.std()
            mono  = media / dp if dp > 0 else 0
            strain = sub.sum() * mono
            rows.append({"Jogador": jog, "Microciclo (Nr)": mc,
                         "Carga Média": round(media,1), "DP": round(dp,1),
                         "Monotonia": round(mono,2), "Strain": round(strain,0)})
    return pd.DataFrame(rows)
