"""LoadMonitorSystem — Cálculos científicos"""
import pandas as pd
import numpy as np
import streamlit as st

@st.cache_data(ttl=0)
def calcular_acwr(df: pd.DataFrame, jogador: str) -> pd.DataFrame:
    """ACWR EWMA por jogador — λ aguda=0.25, λ crónica=2/29"""
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
    resultado = {}
    if df_base.empty or "Jogador" not in df_base.columns: return resultado
    for jog in df_base["Jogador"].dropna().unique():
        acwr_df = calcular_acwr(df_base, jog)
        if acwr_df.empty or "ACWR" not in acwr_df.columns:
            resultado[jog] = {"acwr": np.nan}; continue
        acwr_val = acwr_df["ACWR"].dropna()
        resultado[jog] = {"acwr": acwr_val.iloc[-1] if not acwr_val.empty else np.nan}
    return resultado

def zscore_serie(serie: pd.Series) -> pd.Series:
    if serie.dropna().std() == 0: return pd.Series(0, index=serie.index)
    return (serie - serie.mean()) / serie.std()

def cor_acwr(v) -> str:
    if pd.isna(v): return "⚪"
    if v > 1.5:  return "🔴"
    if v > 1.3:  return "🟡"
    if v >= 0.8: return "🟢"
    return "🔵"

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
