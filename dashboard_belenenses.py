"""
Dashboard de Monitorização de Carga — Belenenses
Versão Cloud — Streamlit Cloud + GitHub
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import os
import io
import base64
import json
from pathlib import Path
from datetime import datetime, date

# ── Stripe ───────────────────────────────────────────────────────────────────
try:
    from auth_stripe import mostrar_botao_upgrade, verificar_retorno_stripe
    STRIPE_DISPONIVEL = True
except ImportError:
    STRIPE_DISPONIVEL = False
    def verificar_retorno_stripe(): pass
    def mostrar_botao_upgrade(*a, **kw): pass

# ── Configuração da página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Carga de Treino | Belenenses",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS personalizado ─────────────────────────────────────────────────────────

# ── Caminho do ficheiro Excel ─────────────────────────────────────────────────
EXCEL_PATH = "Excel_carga_de_treino_profissional_final_2.xlsx"

# ── Funções de carregamento ───────────────────────────────────────────────────
# ── Mapeamento inteligente de colunas ────────────────────────────────────────
COL_ALIASES = {
    "Distância Total (m)":  ["distance","dist","distancia","distância","total distance","distance total","dist total","dist. total","total dist","distance (m)","dist (m)","meters","metros"],
    "HSR (m)":              ["hsr","high speed running","high speed distance","hsd","alta velocidade","high intensity distance","hid","speed zone 4","zona 4","z4 dist"],
    "Sprint (m)":           ["sprint","sprint distance","sprinting","zona 5","z5","speed zone 5","max speed distance","sprint dist"],
    "Acc (n)":              ["acc","accelerations","aceleração","aceleracoes","acelerações","accel","accelerations count","n acc","num acc","ima acc","number of accelerations"],
    "Dcc (n)":              ["dcc","decel","decelerations","desaceleração","desaceleracoes","desacelerações","deceleration count","n dcc","ima dec"],
    "Vel. Máx (km/h)":      ["vmax","vel max","velocidade max","velocidade máxima","max speed","max velocity","peak speed","top speed","maximum speed","vmax (km/h)","speed max"],
    "PSE Sessão":           ["pse","rpe","perceived exertion","percepcao","perceção","sessão rpe","session rpe","rpe session"],
    "Duração (min)":        ["duracao","duração","duration","tempo","time","minutes","minutos","session duration","dur"],
    "Microciclo (Nr)":      ["microciclo","mc","week","semana","microcycle","gameweek","matchweek","gw"],
    "Carga Interna":        ["carga interna","internal load","session load","training load","load","tl","session tl"],
    "Hooper Index":         ["hooper","hooper index","hi","wellness score","wellness","bem estar","bem-estar"],
    "Sono (1-5)":           ["sono","sleep","sleep quality","qualidade sono"],
    "Dor Musc. (1-5)":      ["dor muscular","dor musc","muscle soreness","soreness","doms"],
    "Stress (1-5)":         ["stress","strain","tensao","tensão"],
    "Humor (1-5)":          ["humor","mood","estado humor","estado de humor"],
    "PlayerLoad":           ["playerload","player load","pl","player_load"],
    "Mechanical Power":     ["mechanical power","mec power","mech power","potencia mecanica","potência mecânica"],
    "Metabolic Power":      ["metabolic power","met power","potencia metabolica","potência metabólica","mp"],
    "Distância/min (m/min)":["dist/min","distance/min","relative distance","distância relativa","dist relativa","m/min","meters per minute"],
    "HSR%":                 ["hsr%","hsr percent","% hsr","high speed %","% alta velocidade"],
}

def normalizar_coluna(nome: str) -> str:
    nome_lower = nome.lower().strip()
    for standard, aliases in COL_ALIASES.items():
        if nome_lower == standard.lower(): return standard
        if any(nome_lower == a.lower() or nome_lower.replace(" ","") == a.lower().replace(" ","") for a in aliases):
            return standard
    return nome

def detectar_colunas_numericas(df, excluir=None):
    excluir = excluir or ["Jogador","Posição","Tipo","Dia MD","Data","Observações","Exercício","Categoria"]
    return [c for c in df.columns if c not in excluir
            and hasattr(df[c], 'dtype') and str(df[c].dtype) not in ['object','bool']
            and df[c].notna().any()]

def get_mets_gps(df):
    """Retorna TODAS as métricas numéricas disponíveis no Excel do utilizador."""
    excluir = {"Jogador","Posição","Tipo","Dia MD","Data","Observações",
               "Microciclo (Nr)","Exercício","Categoria"}
    import pandas as pd
    return [c for c in df.columns if c not in excluir
            and pd.api.types.is_numeric_dtype(df[c])
            and df[c].notna().any()]

@st.cache_data(ttl=0)
def carregar_dados(path: str):
    """Lê BD_Carga — aceita qualquer coluna GPS de qualquer plataforma."""
    import pandas as pd

    # ── 1. Detectar linha de cabeçalho ───────────────────────────────────────
    raw = pd.read_excel(path, sheet_name="BD_Carga", header=None, engine="openpyxl")
    header_row = 0
    for i, row in raw.iterrows():
        row_vals = [str(v).strip().lower() for v in row.values if pd.notna(v) and str(v).strip()]
        if any(v in ["jogador","player","atleta","athlete","name","nome"] for v in row_vals):
            header_row = i
            break

    df = pd.read_excel(path, sheet_name="BD_Carga", header=header_row, engine="openpyxl")

    # ── 2. Limpar colunas ────────────────────────────────────────────────────
    # Remover colunas completamente vazias ou "Unnamed"
    df = df.loc[:, ~df.columns.str.match(r'^Unnamed')]
    df = df.dropna(axis=1, how="all")
    # Normalizar nomes
    df.columns = [str(c).strip() for c in df.columns]
    # Eliminar colunas duplicadas (manter primeira ocorrência)
    df = df.loc[:, ~df.columns.duplicated()]

    # ── 3. Normalizar nomes de colunas via aliases ───────────────────────────
    rename_map = {}
    for col in df.columns:
        norm = normalizar_coluna(col)
        if norm != col and norm not in df.columns:
            rename_map[col] = norm
    if rename_map:
        df = df.rename(columns=rename_map)

    # Normalizar colunas de texto obrigatórias
    for standard, aliases in [
        ("Jogador", ["player","atleta","athlete","name","nome"]),
        ("Posição",  ["position","pos","posicion"]),
        ("Tipo",     ["type","session type","sessao"]),
        ("Dia MD",   ["matchday","match day","dia jogo","game day"]),
    ]:
        if standard not in df.columns:
            match = next((c for c in df.columns if c.lower().strip() in aliases), None)
            if match:
                df = df.rename(columns={match: standard})

    # ── 4. Converter Data ────────────────────────────────────────────────────
    col_data = next((c for c in df.columns if c.lower().strip() in ["data","date","fecha"]), None)
    if col_data:
        if col_data != "Data":
            df = df.rename(columns={col_data: "Data"})
        def conv(v):
            if pd.isna(v): return pd.NaT
            try: return pd.Timestamp("1899-12-30") + pd.Timedelta(days=float(v))
            except: return pd.to_datetime(v, errors="coerce")
        df["Data"] = df["Data"].apply(conv)

    # ── 5. Converter colunas numéricas ────────────────────────────────────────
    TEXTO = {"Jogador","Posição","Tipo","Dia MD","Observações","Exercício",
             "Categoria","Data","Hora","Clube","Equipa","Grupo"}
    for col in list(df.columns):
        if col in TEXTO:
            continue
        # Garantir que é Series (não DataFrame — acontece com colunas duplicadas)
        serie = df[col]
        if isinstance(serie, pd.DataFrame):
            serie = serie.iloc[:, 0]
            df = df.drop(columns=[col])
            df[col] = serie
        df[col] = pd.to_numeric(serie, errors="coerce")

    # ── 6. Calcular Carga Interna se não existir ──────────────────────────────
    if "Carga Interna" not in df.columns:
        col_pse = next((c for c in df.columns if "pse" in c.lower() or "rpe" in c.lower()), None)
        col_dur = next((c for c in df.columns
                        if "dura" in c.lower() or "duration" in c.lower()
                        or c.lower() in ["min","minutes","minutos"]), None)
        if col_pse and col_dur:
            df["Carga Interna"] = (pd.to_numeric(df[col_pse], errors="coerce") *
                                   pd.to_numeric(df[col_dur], errors="coerce"))

    # ── 7. Calcular Hooper Index se não existir ───────────────────────────────
    if "Hooper Index" not in df.columns:
        keywords = ["sono","sleep","dor musc","soreness","stress","humor","mood","fadiga"]
        cols_h = [c for c in df.columns
                  if any(k in c.lower() for k in keywords)
                  and pd.api.types.is_numeric_dtype(df[c])]
        if len(cols_h) >= 3:
            acc = pd.Series(0.0, index=df.index)
            for c in cols_h[:4]:
                acc = acc + (5 - pd.to_numeric(df[c], errors="coerce").fillna(0))
            df["Hooper Index"] = acc

    # ── 8. Limpar linhas vazias ───────────────────────────────────────────────
    df = df.dropna(how="all")
    if "Jogador" in df.columns:
        df = df[df["Jogador"].notna() & (df["Jogador"].astype(str).str.strip() != "")]

    return df


@st.cache_data(ttl=0)
def carregar_dados_safe(path: str):
    """Wrapper com tratamento de erros amigável."""
    try:
        return carregar_dados(path), None
    except Exception as e:
        return None, str(e)


@st.cache_data(ttl=0)
def carregar_exercicios(path: str):
    """Lê a folha Exercícios se existir."""
    try:
        raw = pd.read_excel(path, sheet_name="Exercícios", header=None, engine="openpyxl")
        header_row = 2
        for i, row in raw.iterrows():
            vals = [str(v).strip().lower() for v in row.values if v is not None]
            if any(v in ["data","nome do exercicio","nome","exercicio"] for v in vals):
                header_row = i
                break
        df_ex = pd.read_excel(path, sheet_name="Exercícios", header=header_row, engine="openpyxl")
        df_ex.columns = [str(c).strip().replace(chr(10)," ") for c in df_ex.columns]
        rename = {}
        for col in df_ex.columns:
            cl = col.lower()
            if "data" in cl:                              rename[col] = "Data"
            elif "microciclo" in cl:                      rename[col] = "Microciclo (Nr)"
            elif "dia" in cl and "md" in cl:              rename[col] = "Dia MD"
            elif ("nome" in cl or "exerc" in cl) and "categ" not in cl: rename[col] = "Exercício"
            elif "categ" in cl:                           rename[col] = "Categoria"
            elif "duração" in cl or "duracao" in cl:      rename[col] = "Duração (min)"
            elif "jogadores" in cl or "nº" in cl:         rename[col] = "Nº Jogadores"
            elif "distância" in cl or "distancia" in cl:  rename[col] = "Distância Total (m)"
            elif "hsr" in cl:                             rename[col] = "HSR (m)"
            elif "sprint" in cl:                          rename[col] = "Sprint (m)"
            elif "acc" in cl and "dcc" not in cl:         rename[col] = "Acc (n)"
            elif "dcc" in cl:                             rename[col] = "Dcc (n)"
            elif "vel" in cl or "vmáx" in cl or "vmax" in cl: rename[col] = "Vel. Máx (km/h)"
            elif "pse" in cl:                             rename[col] = "PSE Exercício"
            elif "nota" in cl:                            rename[col] = "Notas"
        df_ex = df_ex.rename(columns=rename)
        if "Data" in df_ex.columns:
            def conv(v):
                if pd.isna(v): return pd.NaT
                try: return pd.Timestamp("1899-12-30") + pd.Timedelta(days=float(v))
                except: return pd.to_datetime(v, errors="coerce")
            df_ex["Data"] = df_ex["Data"].apply(conv)
        if "PSE Exercício" in df_ex.columns and "Duração (min)" in df_ex.columns:
            df_ex["Carga Interna Ex."] = (pd.to_numeric(df_ex["PSE Exercício"], errors="coerce") *
                                           pd.to_numeric(df_ex["Duração (min)"], errors="coerce"))
        df_ex = df_ex.dropna(how="all")
        if "Exercício" in df_ex.columns:
            df_ex = df_ex[df_ex["Exercício"].notna()]
        for col in ["Microciclo (Nr)","Duração (min)","Nº Jogadores","Distância Total (m)",
                    "HSR (m)","Sprint (m)","Acc (n)","Dcc (n)","Vel. Máx (km/h)","PSE Exercício"]:
            if col in df_ex.columns:
                df_ex[col] = pd.to_numeric(df_ex[col], errors="coerce")
        return df_ex
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=0)
def calcular_acwr(df: pd.DataFrame, jogador: str):
    """EWMA ACWR por jogador — λ aguda=0.25, λ crónica=0.069."""
    sub = df[df["Jogador"] == jogador].sort_values("Data").copy()
    if sub.empty or "Carga Interna" not in sub.columns:
        return sub
    λa, λc = 0.25, 2 / 29
    sub["EWMA_Aguda"]   = sub["Carga Interna"].ewm(alpha=λa, adjust=False).mean()
    sub["EWMA_Crónica"] = sub["Carga Interna"].ewm(alpha=λc, adjust=False).mean()
    sub["ACWR"] = sub["EWMA_Aguda"] / sub["EWMA_Crónica"].replace(0, np.nan)
    return sub


# (cor_acwr definida globalmente acima)


# ── Sidebar ───────────────────────────────────────────────────────────────────
# ── Sistema de autenticação LoadMonitor ───────────────────────────────────────
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
try:
    from auth import (fazer_login, registar_utilizador, verificar_sessao,
                      fazer_logout, tem_acesso, alterar_password,
                      atualizar_perfil, PLANOS)
    AUTH_DISPONIVEL = True
except Exception as _auth_err:
    AUTH_DISPONIVEL = False

def ecrã_login():
    """Ecrã de login/registo profissional."""
    st.markdown("""
    <style>
    .login-container {
        max-width: 420px; margin: 60px auto; padding: 0 20px;
    }
    .login-logo {
        font-family: 'Arial Black', sans-serif;
        font-size: 2.2rem; font-weight: 900;
        letter-spacing: 2px; text-align: center;
        margin-bottom: 4px;
    }
    .login-logo span { color: #e63946; }
    .login-tagline {
        text-align: center; color: #666; font-size: 0.8rem;
        letter-spacing: 2px; text-transform: uppercase;
        margin-bottom: 32px;
    }
    .trial-badge {
        background: linear-gradient(135deg, #e63946, #c0392b);
        color: white; text-align: center; padding: 10px;
        border-radius: 8px; font-size: 0.8rem; font-weight: 600;
        margin-bottom: 20px; letter-spacing: 0.5px;
    }
    </style>
    <div class="login-container">
        <div class="login-logo">Load<span>Monitor</span></div>
        <div class="login-tagline">Monitorização de Carga Desportiva</div>
        <div class="trial-badge">🎉 14 dias grátis no plano Pro — sem cartão de crédito</div>
    </div>
    """, unsafe_allow_html=True)

    col_center = st.columns([1, 2, 1])[1]
    with col_center:
        tab_login, tab_registo = st.tabs(["Entrar", "Criar Conta"])

        with tab_login:
            email_l = st.text_input("Email", key="login_email", placeholder="preparador@email.com")
            pwd_l   = st.text_input("Password", type="password", key="login_pwd")
            if st.button("Entrar →", type="primary", use_container_width=True, key="btn_login"):
                if not email_l or not pwd_l:
                    st.error("Preenche email e password.")
                else:
                    result = fazer_login(email_l, pwd_l)
                    if result["sucesso"]:
                        st.session_state["lm_token"] = result["token"]
                        st.session_state["lm_user"]  = result["utilizador"]
                        st.rerun()
                    else:
                        st.error(result["erro"])

        with tab_registo:
            nome_r  = st.text_input("Nome completo", key="reg_nome")
            email_r = st.text_input("Email", key="reg_email", placeholder="preparador@email.com")
            clube_r = st.text_input("Clube / Organização (opcional)", key="reg_clube")
            pwd_r   = st.text_input("Password (mín. 8 caracteres)", type="password", key="reg_pwd")
            pwd_r2  = st.text_input("Confirmar password", type="password", key="reg_pwd2")

            if st.button("Criar conta grátis →", type="primary", use_container_width=True, key="btn_reg"):
                if pwd_r != pwd_r2:
                    st.error("As passwords não coincidem.")
                else:
                    result = registar_utilizador(email_r, pwd_r, nome_r, clube_r)
                    if result["sucesso"]:
                        r2 = fazer_login(email_r, pwd_r)
                        if r2["sucesso"]:
                            st.session_state["lm_token"] = r2["token"]
                            st.session_state["lm_user"]  = r2["utilizador"]
                            st.rerun()
                    else:
                        st.error(result["erro"])
    st.stop()

# ── Verificar autenticação ────────────────────────────────────────────────────
if not AUTH_DISPONIVEL:
    # Fallback: modo demo sem auth
    st.session_state["lm_user"] = {
        "id": 0, "nome": "Demo", "clube": "Demo",
        "plano": "pro", "trial_fim": None, "dias_trial": None,
    }
else:
    token = st.session_state.get("lm_token")
    if token:
        user = verificar_sessao(token)
        if user:
            st.session_state["lm_user"] = user
        else:
            st.session_state.pop("lm_token", None)
            st.session_state.pop("lm_user", None)

    if "lm_user" not in st.session_state:
        ecrã_login()

# ── Verificar retorno do Stripe após pagamento ────────────────────────────────
verificar_retorno_stripe()

# ── Mostrar página de upgrade se solicitado ───────────────────────────────────
if st.session_state.get("mostrar_upgrade") and STRIPE_DISPONIVEL:
    _up_user  = st.session_state.get("lm_user", {})
    _up_id    = _up_user.get("id", 0)
    _up_email = _up_user.get("email", "")
    _up_nome  = _up_user.get("nome", "")

    st.markdown("## 🚀 Activar Plano Pro")
    st.markdown("Estás a um passo de desbloquear todas as funcionalidades do LoadMonitorSystem.")

    col_up1, col_up2 = st.columns([1, 1])
    with col_up1:
        st.markdown("""**O Plano Pro inclui:**
- ✅ Atletas e equipas ilimitados
- ✅ Todos os alertas automáticos
- ✅ Análise GPS avançada (Vmáx, Sprint)
- ✅ Calculadora científica de exercícios
- ✅ Relatórios PDF personalizáveis
- ✅ Notificações email e WhatsApp
- ✅ Planeado vs Realizado % do jogo""")

    with col_up2:
        st.markdown("""**Preço:**""")
        st.markdown("## 29€/mês")
        st.caption("Sem contrato · Cancela quando quiseres · Começa hoje")

        # Gerar URL Stripe
        _stripe_key = f"stripe_checkout_url_{_up_id}"
        if _stripe_key not in st.session_state:
            with st.spinner("A preparar pagamento seguro..."):
                from auth_stripe import criar_checkout_stripe
                resultado = criar_checkout_stripe(_up_id, _up_email, _up_nome)
                if "url" in resultado:
                    st.session_state[_stripe_key] = resultado["url"]
                else:
                    st.error(resultado.get("erro", "Erro ao criar sessão."))

        if _stripe_key in st.session_state:
            _checkout_url = st.session_state[_stripe_key]
            st.markdown(
                f'<a href="{_checkout_url}" target="_blank" style="display:block;'
                f'background:#e63946;color:white;text-align:center;padding:16px;'
                f'border-radius:8px;font-weight:700;font-size:1rem;text-decoration:none;'
                f'margin-top:8px">💳 Pagar com segurança →</a>',
                unsafe_allow_html=True
            )
            st.caption("🔒 Processado com segurança pelo Stripe · Podes usar cartão de crédito ou débito")

    if st.button("← Voltar à app", key="btn_voltar_upgrade"):
        st.session_state.pop("mostrar_upgrade", None)
        st.session_state.pop(f"stripe_checkout_url_{_up_id}", None)
        st.rerun()
    st.stop()

# ── Fonte de dados ─────────────────────────────────────────────────────────────
# Na cloud: suporta upload direto OU ficheiro no repositório GitHub
IS_CLOUD = not os.path.exists(EXCEL_PATH)

if IS_CLOUD:
    # Chave única por utilizador — garante isolamento total de dados
    _uid = st.session_state.get("lm_user", {}).get("id", 0)
    _excel_key = f"excel_bytes_{_uid}"
    if _excel_key not in st.session_state:
        st.session_state[_excel_key] = None
    # Compatibilidade com código legado
    st.session_state["excel_bytes"] = st.session_state[_excel_key]
    st.session_state["_excel_key"]  = _excel_key

# Utilizador autenticado
_lm_user = st.session_state.get("lm_user", {})
_lm_nome  = _lm_user.get("nome", "Utilizador")
_lm_clube = _lm_user.get("clube", "")
_lm_plano = _lm_user.get("plano", "free")
_lm_trial = _lm_user.get("dias_trial")

with st.sidebar:
    # ── LoadMonitor Logo ─────────────────────────────────────────────────
    st.markdown("""
    <div style="padding:20px 16px 12px;border-bottom:1px solid rgba(255,255,255,0.05);margin-bottom:12px">
        <div style="font-family:'Space Grotesk',sans-serif;font-size:1.3rem;font-weight:700;
        letter-spacing:1px;color:white">Load<span style="color:#e63946">Monitor</span></div>
        <div style="font-size:0.6rem;color:rgba(255,255,255,0.25);letter-spacing:2px;
        text-transform:uppercase;margin-top:2px">Sports Performance</div>
    </div>
    """, unsafe_allow_html=True)

    # Info do utilizador
    plano_cor = "#e63946" if _lm_plano == "pro" else "#888"
    plano_label = f"PRO{'  ⏳ ' + str(_lm_trial) + 'd trial' if _lm_trial else ''}" if _lm_plano == "pro" else "FREE"
    st.markdown(f"""
    <div style='background:rgba(255,255,255,0.05);border-radius:10px;
    padding:10px 12px;margin-bottom:8px;border:1px solid rgba(255,255,255,0.08)'>
        <div style='font-weight:700;font-size:0.85rem'>{_lm_nome}</div>
        <div style='font-size:0.72rem;color:#888'>{_lm_clube}</div>
        <div style='margin-top:5px'>
        <span style='background:{plano_cor};color:white;padding:2px 8px;
        border-radius:4px;font-size:0.65rem;font-weight:700;letter-spacing:1px'>
        {plano_label}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Botão upgrade se free
    if _lm_plano == "free":
        st.markdown("""
        <a href='#' style='display:block;background:linear-gradient(135deg,#e63946,#c0392b);
        color:white;text-align:center;padding:8px;border-radius:8px;font-size:0.75rem;
        font-weight:700;text-decoration:none;margin-bottom:8px;letter-spacing:0.5px'>
        ⚡ Upgrade para Pro — 19€/mês</a>
        """, unsafe_allow_html=True)

    st.divider()

    if IS_CLOUD:
        st.markdown("### 📤 Carregar Excel")
        uploaded = st.file_uploader(
            "Faz upload do ficheiro Excel",
            type=["xlsx"],
            help="Carrega o teu ficheiro Excel com os dados de carga",
            key="uploader"
        )
        if uploaded is not None:
            _bytes = uploaded.read()
            _ek = st.session_state.get("_excel_key", "excel_bytes_0")
            st.session_state[_ek]            = _bytes
            st.session_state["excel_bytes"]  = _bytes
            st.cache_data.clear()
            st.success(f"✅ {uploaded.name}")

        _ek_chk = st.session_state.get("_excel_key", "excel_bytes_0")
        if st.session_state.get(_ek_chk) is None:
            st.session_state["excel_bytes"] = None
        if st.session_state["excel_bytes"] is None:
            # ── ECRÃ DE BOAS-VINDAS ───────────────────────────────────────────────
            st.markdown("""
<div style="background:linear-gradient(135deg,#0d1421,#161b22);border:1px solid rgba(255,255,255,0.07);
border-radius:16px;padding:32px 28px;margin:8px 0;border-top:3px solid #e63946">
<div style="font-family:'Space Grotesk',sans-serif;font-size:1.6rem;font-weight:700;
color:white;margin-bottom:8px">Bem-vindo ao LoadMonitorSystem 👋</div>
<div style="font-size:0.85rem;color:rgba(255,255,255,0.5);line-height:1.6">
Monitorização de Carga e Tomada de Decisão para preparadores físicos.
</div>
</div>
""", unsafe_allow_html=True)

            st.markdown("### Começa em 3 passos simples")

            col_ob1, col_ob2, col_ob3 = st.columns(3)
            for col, num, title, desc, icon in [
                (col_ob1, "1", "Descarrega o Template", "Usa o nosso ficheiro Excel oficial com todas as colunas já configuradas.", "📥"),
                (col_ob2, "2", "Preenche os dados", "Adiciona as sessões de treino, wellness e GPS. Segue as instruções dentro do ficheiro.", "✏️"),
                (col_ob3, "3", "Faz upload aqui", "Arrasta o ficheiro para o campo acima. A app analisa tudo automaticamente.", "🚀"),
            ]:
                col.markdown(f"""
<div style="background:#161b22;border:1px solid rgba(255,255,255,0.07);border-radius:12px;
padding:20px;height:100%">
<div style="font-size:2rem;margin-bottom:10px">{icon}</div>
<div style="font-family:'Space Grotesk',sans-serif;font-size:0.8rem;font-weight:700;
color:#e63946;letter-spacing:2px;margin-bottom:6px">PASSO {num}</div>
<div style="font-weight:600;color:white;margin-bottom:8px;font-size:0.9rem">{title}</div>
<div style="font-size:0.78rem;color:rgba(255,255,255,0.45);line-height:1.5">{desc}</div>
</div>
""", unsafe_allow_html=True)

            st.divider()

            # Download template
            st.markdown("#### 📥 Template Excel Oficial")
            st.markdown("Contém todas as colunas necessárias, fórmulas automáticas e dados de exemplo.")

            col_dl1, col_dl2 = st.columns([1,2])
            with col_dl1:
                try:
                    with open("LoadMonitorSystem_Template.xlsx", "rb") as f_tmpl:
                        st.download_button(
                            "⬇️ Descarregar Template Excel",
                            data=f_tmpl.read(),
                            file_name="LoadMonitorSystem_Template.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="primary",
                            use_container_width=True,
                        )
                except FileNotFoundError:
                    st.info("Template não encontrado no servidor.")
            with col_dl2:
                st.markdown("""
**O template inclui:**
- 📊 Folha de carga com fórmulas automáticas (Carga Interna, Hooper Index)
- 🏋️ Folha de Testes Neuromusculares (CMJ, RSI, Assimetria)
- 📋 Folha de Carga Planeada por Dia MD
- 📖 Instruções detalhadas dentro do próprio ficheiro
""")

            st.divider()
            st.markdown("""
<div style="background:rgba(230,57,70,0.08);border:1px solid rgba(230,57,70,0.2);
border-radius:10px;padding:16px;font-size:0.82rem;color:rgba(255,255,255,0.7)">
⚠️ <b>Compatível com qualquer plataforma GPS</b> — Catapult, STATSports, Polar, FieldWiz e outras.
A app deteta automaticamente as colunas do teu ficheiro.
</div>
""", unsafe_allow_html=True)

            st.stop()

        excel_path = io.BytesIO(st.session_state["excel_bytes"])
    else:
        # Modo local — lê do ficheiro diretamente
        excel_path = EXCEL_PATH

    if st.button("🔄 Atualizar Dados", type="primary", use_container_width=True):
        st.cache_data.clear()
        if IS_CLOUD and "excel_bytes" in st.session_state:
            pass  # mantém os bytes em memória
        st.rerun()

    if not IS_CLOUD:
        mod_time = os.path.getmtime(excel_path)
        st.caption(f"📅 Última modificação:\n{datetime.fromtimestamp(mod_time).strftime('%d/%m/%Y %H:%M')}")

    st.divider()

    # Carregar dados
    try:
        df, _load_err = carregar_dados_safe(excel_path)
        if df is None or df.empty:
            st.sidebar.error(f"Erro ao ler o Excel: {_load_err or 'ficheiro vazio ou formato inválido'}")
            st.info("### ⚠️ Erro ao carregar o ficheiro Excel\n\n"
                    f"**Detalhe:** {_load_err or 'ficheiro vazio'}\n\n"
                    "**Possíveis causas:**\n"
                    "- A folha chama-se diferente de 'BD_Carga'\n"
                    "- O ficheiro está aberto noutro programa\n"
                    "- Formato de dados inválido numa coluna\n\n"
                    "**Solução:** Usa o template oficial do LoadMonitorSystem.")
            st.stop()
    except Exception as e:
        st.error(f"Erro ao ler o Excel:\n{e}")
        st.stop()

    jogadores  = sorted(df["Jogador"].dropna().unique().tolist())
    microciclos = sorted(df["Microciclo (Nr)"].dropna().unique().tolist(), reverse=True)
    posicoes   = sorted(df["Posição"].dropna().unique().tolist()) if "Posição" in df.columns else []

    # Logout
    # Banner de upgrade na sidebar
    _lm_plano_sb = st.session_state.get("lm_user", {}).get("plano", "free")
    _lm_trial_sb = st.session_state.get("lm_user", {}).get("dias_trial")
    if STRIPE_DISPONIVEL and (_lm_plano_sb == "free" or _lm_trial_sb is not None):
        _lm_trial_sb = st.session_state.get("lm_user", {}).get("dias_trial")
        _cor_trial = "#e74c3c" if _lm_trial_sb and _lm_trial_sb <= 3 else "#f39c12" if _lm_trial_sb and _lm_trial_sb <= 7 else "#3498db"
        if _lm_trial_sb is not None:
            st.markdown(f"""<div style="background:{_cor_trial}18;border:1px solid {_cor_trial}50;
border-radius:10px;padding:10px 14px;text-align:center;margin:4px 0">
<div style="font-size:0.7rem;font-weight:700;color:{_cor_trial}">⏳ {_lm_trial_sb} dias de trial</div>
<div style="font-size:0.65rem;color:rgba(255,255,255,0.4);margin-top:2px">Faz upgrade para manter o acesso</div>
</div>""", unsafe_allow_html=True)
        st.markdown("""<div style="background:linear-gradient(160deg,#1c0608,#2d0d10);
border:2px solid #e63946;border-radius:12px;padding:16px 14px;text-align:center;margin:8px 0">
<div style="font-size:0.62rem;font-weight:700;color:#e63946;letter-spacing:3px;margin-bottom:6px">🚀 PLANO PRO</div>
<div style="font-size:1.6rem;font-weight:700;color:white;line-height:1">29€<span style="font-size:0.8rem;color:rgba(255,255,255,0.45);font-weight:400">/mês</span></div>
<div style="font-size:0.65rem;color:rgba(255,255,255,0.35);margin:4px 0 10px">Sem contrato · Cancela quando quiseres</div>
<div style="font-size:0.72rem;color:rgba(255,255,255,0.6);text-align:left;line-height:1.8">
✓ Atletas e equipas ilimitados<br>✓ Todos os alertas automáticos<br>✓ Análise GPS avançada<br>✓ Relatórios PDF personalizáveis
</div></div>""", unsafe_allow_html=True)
        if st.button("⬆️ Activar Plano Pro — 29€/mês", key="btn_upgrade_sidebar",
                      type="primary", use_container_width=True):
            st.session_state["mostrar_upgrade"] = True
            st.rerun()
        st.divider()

    if st.button("🚪 Sair", key="btn_logout", use_container_width=False):
        if AUTH_DISPONIVEL:
            fazer_logout(st.session_state.get("lm_token",""))
        # Limpar dados do utilizador atual antes do logout
        _uid_out = st.session_state.get("lm_user", {}).get("id", 0)
        for _k in [f"excel_bytes_{_uid_out}", "excel_bytes", "_excel_key"]:
            st.session_state.pop(_k, None)
        st.session_state.pop("lm_token", None)
        st.session_state.pop("lm_user",  None)
        st.rerun()

    st.divider()
    st.markdown("### 🔍 Filtros")
    st.caption("💡 Os filtros aplicam-se a todas as vistas")
    mc_sel      = st.multiselect("Microciclo(s)", microciclos, default=microciclos[:3] if len(microciclos) >= 3 else microciclos,
                                  help="Seleciona um ou mais microciclos para analisar")
    dias_md_ops = sorted(df["Dia MD"].dropna().unique().tolist()) if "Dia MD" in df.columns else []
    dia_md_sel  = st.multiselect("Dia do Microciclo (Dia MD)", dias_md_ops, default=dias_md_ops)
    pos_sel     = st.multiselect("Posição", posicoes, default=posicoes)
    jogador_sel = st.selectbox("Jogador (análise individual)", jogadores)

    # ── Navegação agrupada ────────────────────────────────────────────────
    st.markdown("""
    <style>
    div[data-testid="stRadio"] > div { gap: 2px; }
    div[data-testid="stRadio"] label {
        padding: 5px 10px !important;
        border-radius: 6px !important;
        font-size: 0.82rem !important;
    }
    div[data-testid="stRadio"] label:hover {
        background: rgba(230,57,70,0.1) !important;
    }
    .nav-group {
        font-size: 0.62rem; font-weight: 700; letter-spacing: 2px;
        color: rgba(255,255,255,0.3); text-transform: uppercase;
        margin: 12px 0 4px 2px;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Navegação simplificada ────────────────────────────────────────────
    SECCOES = [
        ("🎯 Dashboard",   "dashboard"),
        ("👤 Jogadores",    "jogadores"),
        ("🏟️ Equipa",       "equipa"),
        ("📋 Planeamento",  "planeamento"),
        ("🔬 Avançado",     "avancado"),
        ("⚙️ Sistema",      "sistema"),
    ]
    if "seccao" not in st.session_state:
        st.session_state["seccao"] = "dashboard"
    for label, key in SECCOES:
        is_active = st.session_state["seccao"] == key
        if st.sidebar.button(label, key=f"nav_{key}", use_container_width=True,
                              type="primary" if is_active else "secondary"):
            st.session_state["seccao"] = key
            st.rerun()
    seccao = st.session_state["seccao"]
    pagina = seccao


# ── Filtro global (sem Dia MD — aplicado por página onde relevante) ───────────
df_f = df.copy()
if mc_sel:
    df_f = df_f[df_f["Microciclo (Nr)"].isin(mc_sel)]
if pos_sel and "Posição" in df_f.columns:
    df_f = df_f[df_f["Posição"].isin(pos_sel)]

# df_f_dia inclui também o filtro de Dia MD (para páginas de treino/análise diária)
df_f_dia = df_f.copy()
if dia_md_sel and "Dia MD" in df_f_dia.columns:
    df_f_dia = df_f_dia[df_f_dia["Dia MD"].isin(dia_md_sel)]


# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES AUXILIARES GLOBAIS
# ═══════════════════════════════════════════════════════════════════════════════

def zscore_serie(serie: pd.Series) -> pd.Series:
    mu, sigma = serie.mean(), serie.std()
    if sigma == 0:
        return pd.Series([0.0] * len(serie), index=serie.index)
    return (serie - mu) / sigma

def cor_acwr(v):
    if pd.isna(v):      return "❓"
    if v > 1.5:         return "🔴 RISCO"
    if v > 1.3:         return "🟡 ATENÇÃO"
    if v >= 0.8:        return "🟢 OK"
    return "🔵 SUB-CARGA"

def calcular_acwr_global(df_base: pd.DataFrame):
    """Calcula ACWR para todos os jogadores usando calcular_acwr. Retorna dict jogador→último ACWR."""
    resultados = {}
    for jog in df_base["Jogador"].dropna().unique():
        sub = calcular_acwr(df_base, jog)
        if sub.empty or "ACWR" not in sub.columns:
            continue
        validos = sub.dropna(subset=["ACWR"])
        if not validos.empty:
            last = validos.iloc[-1]
            resultados[jog] = {
                "acwr": last["ACWR"],
                "posicao": last.get("Posição", "—"),
                "data": last["Data"],
                "ci_agudo": last.get("EWMA_Aguda", 0),
                "ci_cronico": last.get("EWMA_Crónica", 0),
            }
    return resultados

def gerar_pdf_html(conteudo_html: str, titulo: str) -> str:
    """Encapsula conteúdo HTML num documento imprimível."""
    return f"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<title>{titulo}</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 30px; color: #1a1a2e; }}
  h1 {{ color: #e63946; border-bottom: 3px solid #e63946; padding-bottom: 8px; }}
  h2 {{ color: #457b9d; margin-top: 24px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
  th {{ background: #e63946; color: white; padding: 8px 12px; text-align: left; }}
  td {{ padding: 7px 12px; border-bottom: 1px solid #ddd; }}
  tr:nth-child(even) {{ background: #f8f9fa; }}
  .alerta-red    {{ color: #e74c3c; font-weight: bold; }}
  .alerta-yellow {{ color: #e67e22; font-weight: bold; }}
  .alerta-green  {{ color: #27ae60; font-weight: bold; }}
  .alerta-blue   {{ color: #2980b9; font-weight: bold; }}
  .footer {{ margin-top: 40px; font-size: 0.8em; color: #888; border-top: 1px solid #ddd; padding-top: 10px; }}
  @media print {{ button {{ display: none; }} }}
</style>
</head>
<body>
{conteudo_html}
<div class="footer">Gerado automaticamente pelo Dashboard de Carga — Belenenses · {datetime.now().strftime("%d/%m/%Y %H:%M")}</div>
</body>
</html>"""

def botao_download_html(html_str: str, nome_ficheiro: str, label: str = "📥 Exportar Relatório PDF"):
    b64 = base64.b64encode(html_str.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{nome_ficheiro}" style="display:inline-block;padding:10px 20px;background:#e63946;color:white;border-radius:8px;text-decoration:none;font-weight:bold;margin:8px 0">{label}</a>'
    st.markdown(href, unsafe_allow_html=True)
    st.caption("💡 Abre o ficheiro no browser e usa Ctrl+P → 'Guardar como PDF' para exportar.")


# ── Log de alertas (ficheiro JSON local) ─────────────────────────────────────
LOG_PATH = Path("alertas_log.json")

def carregar_log():
    # Cloud: usa session_state; Local: usa ficheiro JSON
    if not os.path.exists(EXCEL_PATH):  # IS_CLOUD
        return st.session_state.get("alertas_log", [])
    if LOG_PATH.exists():
        try:
            return json.loads(LOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def guardar_alerta(jogador: str, tipo: str, descricao: str, valor: str):
    entrada = {
        "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "jogador": jogador,
        "tipo": tipo,
        "descricao": descricao,
        "valor": valor,
    }
    if not os.path.exists(EXCEL_PATH):  # IS_CLOUD — guarda em session_state
        if "alertas_log" not in st.session_state:
            st.session_state["alertas_log"] = []
        st.session_state["alertas_log"].append(entrada)
    else:
        log = carregar_log()
        log.append(entrada)
        LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

def registar_alertas_automaticos(acwr_dict: dict, df_base: pd.DataFrame):
    """Regista no log todos os alertas ativos neste momento."""
    for jog, dados in acwr_dict.items():
        v = dados["acwr"]
        estado = cor_acwr(v)
        if "RISCO" in estado:
            guardar_alerta(jog, "ACWR", "ACWR acima de 1.5 — risco de lesão elevado", f"{v:.2f}")
        elif "ATENÇÃO" in estado:
            guardar_alerta(jog, "ACWR", "ACWR entre 1.3 e 1.5 — monitorizar", f"{v:.2f}")

    # Wellness
    wcols = ["Sono (1-5)", "Dor Musc. (1-5)", "Stress (1-5)", "Humor (1-5)", "Hooper Index"]
    ultima = df_base.sort_values("Data").groupby("Jogador").last().reset_index()
    for _, row in ultima.iterrows():
        jog = row["Jogador"]
        hi = row.get("Hooper Index", np.nan)
        if pd.notna(hi) and hi >= 14:
            guardar_alerta(jog, "Wellness", f"Hooper Index elevado ({hi:.0f}/20)", f"{hi:.0f}")

    # Vmáx
    if "Vel. Máx (km/h)" in df_base.columns:
        for jog in df_base["Jogador"].dropna().unique():
            sub = df_base[df_base["Jogador"] == jog].dropna(subset=["Data","Vel. Máx (km/h)"]).sort_values("Data")
            if sub.empty: continue
            rec = sub["Vel. Máx (km/h)"].max()
            lim = rec * 0.90
            acima = sub[sub["Vel. Máx (km/h)"] >= lim]
            if acima.empty:
                guardar_alerta(jog, "Vmáx", "Nunca atingiu ≥90% do recorde", "—")
                continue
            dias = (sub["Data"].max() - acima["Data"].max()).days
            if dias > 7:
                guardar_alerta(jog, "Vmáx", f"{dias} dias sem ≥90% Vmáx — risco de desadaptação", f"{dias}d")


# ── Page header helper ───────────────────────────────────────────────────────
def lm_header(title: str, subtitle: str = "", badge: str = ""):
    """Cabeçalho padrão de página LoadMonitor."""
    badge_html = f'<div class="lm-page-badge">{badge}</div>' if badge else ""
    sub_html   = f'<div class="lm-page-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div class="lm-page-header">{badge_html}'
        f'<div class="lm-page-title">{title}</div>{sub_html}</div>',
        unsafe_allow_html=True
    )


def premium_layout(height=380, title="", margin=None):
    """Layout padrão premium para todos os gráficos Plotly."""
    return dict(
        height=height,
        title=dict(text=title, font=dict(size=13, color="rgba(255,255,255,0.7)"), x=0) if title else None,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Calibri, sans-serif", color="rgba(255,255,255,0.75)", size=11),
        margin=margin or dict(t=20 if not title else 40, b=30, l=50, r=20),
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.04)",
            linecolor="rgba(255,255,255,0.08)",
            tickfont=dict(size=10),
            showgrid=True,
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.04)",
            linecolor="rgba(255,255,255,0.08)",
            tickfont=dict(size=10),
            showgrid=True,
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0.4)",
            bordercolor="rgba(255,255,255,0.08)",
            borderwidth=1,
            font=dict(size=10),
        ),
        hoverlabel=dict(
            bgcolor="#1a2535",
            bordercolor="#e63946",
            font=dict(size=11, color="white"),
        ),
    )


# ── Scatter Plot com Labels de Jogadores ─────────────────────────────────────
def scatter_jogadores(df_plot: pd.DataFrame, x_col: str, y_col: str,
                       title: str = "", color_col: str = "Posição",
                       size_col: str = None, height: int = 500):
    """
    Scatter plot estilo SportHorizon — círculos coloridos por posição
    com nome do jogador e métricas dentro do tooltip.
    """
    if df_plot.empty or x_col not in df_plot.columns or y_col not in df_plot.columns:
        return None

    df_plot = df_plot.dropna(subset=[x_col, y_col]).copy()
    if df_plot.empty:
        return None

    # Cores por posição
    CORES_POS = {
        "Guarda-Redes": "#3498db", "GR": "#3498db",
        "Defesa": "#2ecc71",       "DC": "#2ecc71", "DD": "#2ecc71", "DE": "#2ecc71",
        "Médio": "#f39c12",        "MC": "#f39c12", "MD": "#f39c12", "ME": "#f39c12",
        "Avançado": "#e63946",     "AV": "#e63946", "EX": "#e63946", "PL": "#e63946",
    }
    DEFAULT_COR = "#9b59b6"

    fig = go.Figure()

    # Agrupar por posição para a legenda
    grupos = df_plot[color_col].unique() if color_col in df_plot.columns else ["Todos"]

    for grupo in grupos:
        if color_col in df_plot.columns:
            sub = df_plot[df_plot[color_col] == grupo]
        else:
            sub = df_plot
        cor = CORES_POS.get(str(grupo), DEFAULT_COR)

        # Tamanho dos marcadores
        if size_col and size_col in sub.columns:
            sizes = sub[size_col].fillna(sub[size_col].mean())
            sizes_norm = ((sizes - sizes.min()) / (sizes.max() - sizes.min() + 1e-9) * 30 + 18).tolist()
        else:
            sizes_norm = [28] * len(sub)

        # Tooltip com todas as métricas numéricas disponíveis
        hover_texts = []
        for _, row in sub.iterrows():
            mets_txt = f"<b>{row['Jogador']}</b><br>"
            mets_txt += f"{x_col}: <b>{row[x_col]:,.1f}</b><br>"
            mets_txt += f"{y_col}: <b>{row[y_col]:,.1f}</b><br>"
            for m in get_mets_gps(df):
                if m in row and pd.notna(row[m]) and m != x_col and m != y_col:
                    mets_txt += f"{m.split('(')[0].strip()}: {row[m]:,.1f}<br>"
            hover_texts.append(mets_txt)

        fig.add_trace(go.Scatter(
            x=sub[x_col],
            y=sub[y_col],
            mode="markers+text",
            name=str(grupo),
            text=sub["Jogador"].apply(lambda n: n.split()[0] if isinstance(n, str) else n),
            textposition="top center",
            textfont=dict(size=10, color="white"),
            hovertext=hover_texts,
            hoverinfo="text",
            marker=dict(
                size=sizes_norm,
                color=cor,
                opacity=0.85,
                line=dict(width=2, color="white"),
            ),
        ))

    # Linhas de média
    x_mean = df_plot[x_col].mean()
    y_mean = df_plot[y_col].mean()
    fig.add_vline(x=x_mean, line_dash="dot", line_color="rgba(255,255,255,0.3)",
                  annotation_text=f"Média {x_col.split('(')[0].strip()}: {x_mean:,.0f}",
                  annotation_font_color="rgba(255,255,255,0.5)", annotation_font_size=10)
    fig.add_hline(y=y_mean, line_dash="dot", line_color="rgba(255,255,255,0.3)",
                  annotation_text=f"Média {y_col.split('(')[0].strip()}: {y_mean:,.0f}",
                  annotation_font_color="rgba(255,255,255,0.5)", annotation_font_size=10)

    # Quadrantes de fundo subtis
    x_min, x_max = df_plot[x_col].min(), df_plot[x_col].max()
    y_min, y_max = df_plot[y_col].min(), df_plot[y_col].max()
    fig.add_vrect(x0=x_mean, x1=x_max*1.05, fillcolor="#2ecc71", opacity=0.03, line_width=0)
    fig.add_hrect(y0=y_mean, y1=y_max*1.05, fillcolor="#2ecc71", opacity=0.03, line_width=0)

    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="white")) if title else None,
        xaxis_title=x_col,
        yaxis_title=y_col,
        height=height,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="rgba(255,255,255,0.85)",
        legend=dict(
            title=color_col if color_col in df_plot.columns else "",
            bgcolor="rgba(30,35,48,0.8)",
            bordercolor="rgba(255,255,255,0.2)",
            borderwidth=1,
        ),
        margin=dict(t=40, b=40, l=40, r=40),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)", zeroline=False),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", zeroline=False),
    )
    return fig


# ── Tendência de KPIs (delta vs microciclo anterior) ─────────────────────────
def calcular_delta(df_base, col, mc_atual, mc_anterior=None):
    """Calcula delta % de uma métrica entre microciclos."""
    if col not in df_base.columns or "Microciclo (Nr)" not in df_base.columns:
        return None, None
    val_atual = df_base[df_base["Microciclo (Nr)"] == mc_atual][col].mean()
    if mc_anterior is None:
        mcs = sorted(df_base["Microciclo (Nr)"].dropna().unique())
        idx = list(mcs).index(mc_atual) if mc_atual in mcs else -1
        mc_anterior = mcs[idx-1] if idx > 0 else None
    if mc_anterior is None:
        return val_atual, None
    val_ant = df_base[df_base["Microciclo (Nr)"] == mc_anterior][col].mean()
    if pd.isna(val_ant) or val_ant == 0:
        return val_atual, None
    delta = ((val_atual - val_ant) / abs(val_ant)) * 100
    return val_atual, delta


def metric_com_delta(col_st, label: str, val, delta_pct, formato=":,.0f", ajuda=""):
    """Mostra métrica com seta e delta % vs microciclo anterior."""
    if val is None or pd.isna(val):
        col_st.metric(label, "—", help=ajuda)
        return
    val_str = format(val, formato.lstrip(":"))
    if delta_pct is not None and not pd.isna(delta_pct):
        delta_str = f"{delta_pct:+.1f}% vs MC ant."
    else:
        delta_str = None
    col_st.metric(label, val_str, delta=delta_str, help=ajuda or f"Delta vs microciclo anterior")


# ── Validação de dados ────────────────────────────────────────────────────────
def validar_dados(df_base: pd.DataFrame):
    """Verifica problemas comuns nos dados do Excel."""
    erros, avisos, ok = [], [], []

    # Tipo
    if "Tipo" in df_base.columns:
        tipos_validos = {"treino", "jogo"}
        tipos_encontrados = df_base["Tipo"].dropna().str.lower().str.strip().unique()
        tipos_invalidos = [t for t in tipos_encontrados if t not in tipos_validos]
        if tipos_invalidos:
            erros.append(f"❌ Coluna 'Tipo' tem valores inválidos: {tipos_invalidos} — deve ser apenas 'Treino' ou 'Jogo'")
        else:
            ok.append("✅ Coluna 'Tipo' — valores corretos (Treino / Jogo)")

    # Dia MD
    if "Dia MD" in df_base.columns:
        dias_validos = {"MD-5","MD-4","MD-3","MD-2","MD-1","MD","MD+1","MD+2"}
        dias_encontrados = set(df_base["Dia MD"].dropna().str.strip().unique())
        dias_invalidos = dias_encontrados - dias_validos
        if dias_invalidos:
            avisos.append(f"⚠️ Coluna 'Dia MD' tem valores não standard: {dias_invalidos} — esperado: MD-5 a MD+2")
        else:
            ok.append("✅ Coluna 'Dia MD' — valores corretos")

    # Datas em falta
    if "Data" in df_base.columns:
        n_sem_data = df_base["Data"].isna().sum()
        if n_sem_data > 0:
            erros.append(f"❌ {n_sem_data} registos sem Data — verifica as linhas em branco no Excel")
        else:
            ok.append("✅ Coluna 'Data' — sem valores em falta")

    # PSE fora de escala
    if "PSE Sessão" in df_base.columns:
        pse = pd.to_numeric(df_base["PSE Sessão"], errors="coerce")
        fora = df_base[(pse < 0) | (pse > 10)]["PSE Sessão"].count()
        if fora > 0:
            erros.append(f"❌ {fora} valores de PSE fora do intervalo 0–10")
        else:
            ok.append("✅ PSE Sessão — todos os valores entre 0 e 10")

    # Hooper fora de escala
    if "Hooper Index" in df_base.columns:
        hi = pd.to_numeric(df_base["Hooper Index"], errors="coerce")
        fora_hi = df_base[(hi < 4) | (hi > 20)]["Hooper Index"].count()
        if fora_hi > 0:
            avisos.append(f"⚠️ {fora_hi} valores de Hooper Index fora do intervalo esperado (4–20)")
        else:
            ok.append("✅ Hooper Index — valores dentro do intervalo (4–20)")

    # Velocidade máxima
    if "Vel. Máx (km/h)" in df_base.columns:
        vmax = pd.to_numeric(df_base["Vel. Máx (km/h)"], errors="coerce")
        suspeitos = ((vmax > 40) | (vmax < 5)) & vmax.notna()
        n_sus = suspeitos.sum()
        if n_sus > 0:
            avisos.append(f"⚠️ {n_sus} valores de Vel. Máx suspeitos (<5 ou >40 km/h) — verifica se são erros de GPS")
        else:
            ok.append("✅ Vel. Máx — sem valores suspeitos")

    # Jogadores sem posição
    if "Posição" in df_base.columns and "Jogador" in df_base.columns:
        sem_pos = df_base[df_base["Posição"].isna()]["Jogador"].dropna().unique()
        if len(sem_pos) > 0:
            avisos.append(f"⚠️ Jogadores sem posição definida: {', '.join(sem_pos)}")
        else:
            ok.append("✅ Todos os jogadores têm posição definida")

    # Duplicados
    if "Data" in df_base.columns and "Jogador" in df_base.columns and "Tipo" in df_base.columns:
        dups = df_base.groupby(["Data","Jogador","Tipo"]).size()
        n_dups = (dups > 1).sum()
        if n_dups > 0:
            avisos.append(f"⚠️ {n_dups} combinações Data+Jogador+Tipo duplicadas — possíveis registos em duplicado")
        else:
            ok.append("✅ Sem registos duplicados")

    # Microciclos vazios (com 0 jogadores)
    if "Microciclo (Nr)" in df_base.columns:
        mc_counts = df_base.groupby("Microciclo (Nr)")["Jogador"].nunique()
        mc_poucos = mc_counts[mc_counts < 5].index.tolist()
        if mc_poucos:
            avisos.append(f"⚠️ Microciclos com menos de 5 jogadores registados: {[int(m) for m in mc_poucos]}")

    return erros, avisos, ok


# ── Envio de email de alertas ─────────────────────────────────────────────────
def enviar_email_alertas(destinatario: str, smtp_user: str, smtp_pass: str,
                          alertas: list, smtp_server: str = "smtp.gmail.com", smtp_port: int = 587):
    """Envia email com alertas ativos."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    if not alertas:
        return False, "Sem alertas para enviar."

    assunto = f"🚨 Alertas de Carga — {datetime.now().strftime('%d/%m/%Y')}"
    corpo_html = f"""
    <html><body style='font-family:Arial;background:#0e1117;color:#fff;padding:20px'>
    <h2 style='color:#e63946'>🚨 Alertas de Carga — Belenenses</h2>
    <p style='color:#aaa'>{datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
    <table style='border-collapse:collapse;width:100%'>
    <tr style='background:#e63946'><th style='padding:10px;text-align:left'>Jogador</th>
    <th style='padding:10px;text-align:left'>Tipo</th>
    <th style='padding:10px;text-align:left'>Descrição</th>
    <th style='padding:10px;text-align:left'>Valor</th></tr>
    """
    for a in alertas:
        cor = "#7b1d1d" if a["tipo"] == "ACWR" else "#7b5b00" if a["tipo"] == "Wellness" else "#0d3b5e"
        corpo_html += f"""<tr style='background:{cor}'>
        <td style='padding:8px;border-bottom:1px solid #333'><b>{a['jogador']}</b></td>
        <td style='padding:8px;border-bottom:1px solid #333'>{a['tipo']}</td>
        <td style='padding:8px;border-bottom:1px solid #333'>{a['descricao']}</td>
        <td style='padding:8px;border-bottom:1px solid #333;color:#e63946'><b>{a['valor']}</b></td>
        </tr>"""
    corpo_html += "</table><br><p style='color:#555;font-size:0.8rem'>Dashboard de Carga — Belenenses</p></body></html>"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"]    = smtp_user
        msg["To"]      = destinatario
        msg.attach(MIMEText(corpo_html, "html"))
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, destinatario, msg.as_string())
        return True, "Email enviado com sucesso!"
    except Exception as e:
        return False, f"Erro ao enviar email: {e}"


# ── Glossário ─────────────────────────────────────────────────────────────────
GLOSSARIO = {
    "ACWR (Acute:Chronic Workload Ratio)": {
        "simples": "Compara a carga da semana atual com a média das últimas 4 semanas. É um indicador de risco de lesão.",
        "tecnico": "Rácio entre a carga aguda (EWMA 7 dias, λ=0.25) e a carga crónica (EWMA 28 dias, λ=2/29). Zona segura: 0.8–1.3.",
        "zonas": {"🟢 OK": "0.8 – 1.3", "🟡 Atenção": "1.3 – 1.5", "🔴 Risco": "> 1.5", "🔵 Sub-carga": "< 0.8"},
    },
    "Carga Interna (UA)": {
        "simples": "Mede o esforço percebido pelo jogador. Calculada multiplicando a duração da sessão pelo valor de PSE.",
        "tecnico": "Session-RPE method (Foster et al.): Carga Interna = PSE × Duração (min). Unidade arbitrária (UA).",
        "zonas": {},
    },
    "PSE (Perceção Subjetiva de Esforço)": {
        "simples": "Escala de 0 a 10 onde o jogador avalia o quão difícil foi a sessão. 10 = esforço máximo.",
        "tecnico": "Escala CR-10 de Borg modificada. Recolhida 20–30 min após o treino para evitar viés imediato.",
        "zonas": {"1–2": "Muito fácil", "3–4": "Fácil/Moderado", "5–6": "Difícil", "7–8": "Muito difícil", "9–10": "Máximo"},
    },
    "HSR (High Speed Running)": {
        "simples": "Distância percorrida a alta velocidade. Mede a exigência das corridas intensas numa sessão.",
        "tecnico": "Distância acumulada acima de um determinado limiar de velocidade (normalmente >19.8 km/h ou >21 km/h, dependendo do GPS).",
        "zonas": {},
    },
    "Sprint": {
        "simples": "Distância percorrida a velocidade máxima (sprints). Indica a exigência neuromuscular de alta intensidade.",
        "tecnico": "Distância acumulada acima do limiar de sprint (normalmente >25 km/h). Indicador de exposição a velocidades máximas.",
        "zonas": {},
    },
    "Z-Score": {
        "simples": "Indica se um valor está acima ou abaixo da média. 0 = na média. +2 = muito acima. -2 = muito abaixo.",
        "tecnico": "Z = (X − μ) / σ. Permite comparar métricas em escalas diferentes. Assume distribuição normal.",
        "zonas": {"🟢 Normal": "−1 a +1σ", "🟡 Acima": "+1 a +2σ", "🔴 Muito acima": "> +2σ", "🔵 Abaixo": "−1 a −2σ", "🟣 Muito abaixo": "< −2σ"},
    },
    "Monotonia (Foster)": {
        "simples": "Mede se o treino é sempre igual. Treinos muito repetitivos são prejudiciais mesmo com carga baixa.",
        "tecnico": "Monotonia = Média semanal CI / Desvio Padrão CI. Valores >2.0 indicam falta de variação na carga.",
        "zonas": {"🟢 Boa variação": "< 1.5", "🟡 Atenção": "1.5 – 2.0", "🔴 Excessiva": "> 2.0"},
    },
    "Strain (Foster)": {
        "simples": "Combina a carga total da semana com a repetição dos treinos. Alto strain = semana intensa E monótona.",
        "tecnico": "Strain = Carga Semanal Total × Monotonia. Elevado strain crónico associado a overtraining e lesão.",
        "zonas": {},
    },
    "Hooper Index": {
        "simples": "Questionário de bem-estar preenchido pelo jogador antes do treino. Soma de 4 fatores (sono, stress, dor muscular, humor). Quanto mais alto, pior.",
        "tecnico": "Soma de 4 itens numa escala de 1–5 cada (Sono, Stress, Dor Muscular, Humor). Range: 4–20. Valores ≥14 indicam acumulação de fadiga.",
        "zonas": {"🟢 Excelente": "4 – 8", "🟡 Normal": "9 – 13", "🔴 Preocupante": "≥ 14"},
    },
    "Vmáx (Velocidade Máxima)": {
        "simples": "A velocidade mais alta atingida pelo jogador. Importante expô-lo regularmente a ≥90% deste valor para manter a capacidade de sprint.",
        "tecnico": "Pico de velocidade registado pelo GPS. A exposição regular a ≥90% Vmáx é crítica para prevenção de lesões musculares (Malone et al., 2017).",
        "zonas": {"🟢 OK": "< 5 dias sem ≥90%", "🟡 Atenção": "5–7 dias", "🔴 Risco": "> 7 dias"},
    },
    "Acc / Dcc (Acelerações / Desacelerações)": {
        "simples": "Número de mudanças bruscas de velocidade. Elevado número indica sessão com muita intensidade neuromuscular.",
        "tecnico": "Contagem de eventos acima de um limiar (normalmente ≥3 m/s²). Alto impacto nos tecidos musculotendinosos.",
        "zonas": {},
    },
}



# ═══════════════════════════════════════════════════════════════════════════════
# VISTA: ALERTAS DO DIA
# ═══════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════════
# RELATÓRIOS — FUNÇÃO CENTRAL DE RENDERIZAÇÃO DE BLOCOS
# ═══════════════════════════════════════════════════════════════════════════════

def renderizar_bloco(bloco_key: str, df_base: pd.DataFrame,
                     contexto: str = "dia", met_principal: str = "Carga Interna",
                     nome_extra: str = "") -> dict:
    """
    Renderiza um bloco de relatório e retorna HTML para exportação.
    contexto: "dia" ou "microciclo"
    Retorna dict com {"rendered": bool, "html": str, "fig": go.Figure|None}
    """
    html_out = ""
    rendered = False

    METS_GPS = get_mets_gps(df_base if "df_base" in dir() else df)
    mets_disp = [m for m in METS_GPS if m in df_base.columns and df_base[m].notna().any()]

    if df_base.empty or not mets_disp:
        return {"rendered": False, "html": "", "fig": None}

    # ── KPIs ─────────────────────────────────────────────────────────────────
    if bloco_key == "kpis":
        st.markdown('<p class="section-title">📊 Métricas da Sessão</p>', unsafe_allow_html=True)
        cols_k = st.columns(min(len(mets_disp), 6))
        html_rows = ""
        html_headers = ""
        for i, met in enumerate(mets_disp[:6]):
            val = df_base[met].mean()
            lbl = met.split("(")[0].strip()
            val_str = f"{val:,.1f}" if not pd.isna(val) else "—"
            cols_k[i].metric(lbl, val_str)
            html_headers += f"<th>{lbl}</th>"
            html_rows += f"<td>{val_str}</td>"
        html_out = f"<h2>Métricas</h2><table><tr>{html_headers}</tr><tr>{html_rows}</tr></table>"
        rendered = True

    # ── Ranking ──────────────────────────────────────────────────────────────
    elif bloco_key == "ranking":
        if met_principal in df_base.columns:
            st.markdown(f'<p class="section-title">🏆 Ranking — {met_principal.split("(")[0].strip()}</p>', unsafe_allow_html=True)
            df_rank = df_base.groupby("Jogador")[met_principal].mean().reset_index().sort_values(met_principal, ascending=False)
            df_rank.columns = ["Jogador", met_principal]
            media_r = df_rank[met_principal].mean()

            cores_rank = []
            for idx, v in enumerate(df_rank[met_principal]):
                pct = v / df_rank[met_principal].max() if df_rank[met_principal].max() > 0 else 0
                if idx == 0:          cores_rank.append("#f39c12")
                elif idx == 1:        cores_rank.append("#95a5a6")
                elif idx == 2:        cores_rank.append("#cd7f32")
                elif pct >= 0.75:     cores_rank.append("#e63946")
                else:                 cores_rank.append("#457b9d")

            fig = go.Figure(go.Bar(
                y=df_rank["Jogador"], x=df_rank[met_principal],
                orientation="h", marker_color=cores_rank,
                text=df_rank[met_principal].round(1), textposition="outside",
            ))
            fig.add_vline(x=media_r, line_dash="dash",
                          line_color="rgba(255,255,255,0.3)",
                          annotation_text=f"Média {media_r:,.1f}",
                          annotation_font_color="rgba(255,255,255,0.5)")
            fig.update_layout(
                height=max(280, len(df_rank)*44),
                xaxis_title=met_principal,
                yaxis=dict(autorange="reversed"),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="rgba(255,255,255,0.85)", showlegend=False, margin=dict(t=10, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)
            html_out = (f"<h2>Ranking — {met_principal.split('(')[0].strip()}</h2>"
                        f"<table><tr><th>#</th><th>Jogador</th><th>{met_principal}</th></tr>"
                        + "".join(f"<tr><td>{i+1}</td><td>{r['Jogador']}</td><td>{r[met_principal]:.1f}</td></tr>"
                                  for i, (_, r) in enumerate(df_rank.iterrows()))
                        + "</table>")
            rendered = True

    # ── Heatmap de jogadores ──────────────────────────────────────────────────
    elif bloco_key == "heatmap":
        st.markdown('<p class="section-title">🗺️ Perfil de Carga — Todos os Jogadores</p>', unsafe_allow_html=True)
        df_heat = df_base.groupby("Jogador")[mets_disp].mean()
        df_heat_z = df_heat.apply(lambda c: (c - c.mean()) / c.std() if c.std() > 0 else c * 0, axis=0)
        labels_h = [m.split("(")[0].strip() for m in mets_disp]
        df_heat_z.columns = labels_h
        fig = go.Figure(go.Heatmap(
            z=df_heat_z.values,
            x=labels_h, y=df_heat_z.index.tolist(),
            text=df_heat.round(1).values, texttemplate="%{text}",
            colorscale="RdYlGn", zmid=0,
            colorbar=dict(title="Z-Score", tickfont=dict(color="white")),
        ))
        fig.update_layout(
            height=max(260, len(df_heat_z) * 44),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="rgba(255,255,255,0.85)", margin=dict(t=10),
            xaxis_title="Métrica", yaxis_title="Jogador",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("🟢 Verde = acima da média · 🔴 Vermelho = abaixo · Valores reais em cada célula")
        html_out = "<h2>Heatmap de Jogadores</h2><p>[Gráfico incluído na versão visual]</p>"
        rendered = True

    # ── ACWR ─────────────────────────────────────────────────────────────────
    elif bloco_key == "acwr":
        st.markdown('<p class="section-title">🚦 Estado ACWR</p>', unsafe_allow_html=True)
        acwr_d = calcular_acwr_global(df)
        rows_acwr = []
        for jog, dados in acwr_d.items():
            v = dados["acwr"]
            e = cor_acwr(v)
            cor_a = "#e74c3c" if "RISCO" in e else "#f39c12" if "ATENÇÃO" in e else "#2ecc71" if "OK" in e else "#3498db"
            rows_acwr.append({"Jogador": jog, "ACWR": round(v, 2), "Estado": e, "_cor": cor_a})

        if rows_acwr:
            df_acwr_r = pd.DataFrame(rows_acwr).sort_values("ACWR", ascending=False)
            fig = go.Figure(go.Bar(
                x=df_acwr_r["Jogador"], y=df_acwr_r["ACWR"],
                marker_color=df_acwr_r["_cor"].tolist(),
                text=df_acwr_r["ACWR"].round(2), textposition="outside",
            ))
            fig.add_hline(y=1.5, line_dash="dash", line_color="#e74c3c", annotation_text="Risco 1.5")
            fig.add_hline(y=0.8, line_dash="dash", line_color="#3498db", annotation_text="Sub-carga 0.8")
            fig.update_layout(
                height=320, yaxis_title="ACWR",
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="rgba(255,255,255,0.85)", showlegend=False, margin=dict(t=10),
            )
            st.plotly_chart(fig, use_container_width=True)
            html_out = ("<h2>ACWR</h2><table><tr><th>Jogador</th><th>ACWR</th><th>Estado</th></tr>"
                        + "".join(f"<tr><td>{r['Jogador']}</td><td>{r['ACWR']}</td><td>{r['Estado']}</td></tr>"
                                  for _, r in df_acwr_r.iterrows()) + "</table>")
            rendered = True

    # ── Wellness ──────────────────────────────────────────────────────────────
    elif bloco_key == "wellness":
        wcols = [c for c in ["Sono (1-5)", "Dor Musc. (1-5)", "Stress (1-5)", "Humor (1-5)", "Hooper Index"]
                 if c in df_base.columns and df_base[c].notna().any()]
        if wcols:
            st.markdown('<p class="section-title">💤 Wellness</p>', unsafe_allow_html=True)
            html_rows_w = ""
            for _, row in df_base.groupby("Jogador")[wcols].mean().reset_index().iterrows():
                hi = row.get("Hooper Index", np.nan)
                sono = row.get("Sono (1-5)", np.nan)
                stress = row.get("Stress (1-5)", np.nan)
                dor = row.get("Dor Musc. (1-5)", np.nan)
                alertas = []
                if pd.notna(hi) and hi >= 14:     alertas.append(f"Hooper {hi:.0f}🔴")
                if pd.notna(sono) and sono <= 2:   alertas.append(f"Sono {sono:.0f}🔴")
                if pd.notna(stress) and stress >= 4: alertas.append(f"Stress {stress:.0f}🔴")
                if pd.notna(dor) and dor >= 4:     alertas.append(f"Dor {dor:.0f}🔴")
                cor_w = "#e74c3c" if alertas else "#2ecc71"
                msg_w = " · ".join(alertas) if alertas else "✅ OK"
                st.markdown(
                    f'<div style="border-left:3px solid {cor_w};padding:6px 12px;margin:3px 0;'
                    f'background:{cor_w}18;border-radius:0 8px 8px 0;font-size:0.82rem">'
                    f'<b>{row["Jogador"]}</b> — {msg_w}</div>',
                    unsafe_allow_html=True
                )
                html_rows_w += f"<tr><td>{row['Jogador']}</td><td>{msg_w}</td></tr>"
            html_out = f"<h2>Wellness</h2><table><tr><th>Jogador</th><th>Estado</th></tr>{html_rows_w}</table>"
            rendered = True

    # ── Vmáx ──────────────────────────────────────────────────────────────────
    elif bloco_key == "vmax":
        if "Vel. Máx (km/h)" in df_base.columns and df_base["Vel. Máx (km/h)"].notna().any():
            st.markdown('<p class="section-title">🏃 Velocidades Máximas</p>', unsafe_allow_html=True)
            vmax_r = df_base.groupby("Jogador")["Vel. Máx (km/h)"].max().reset_index().sort_values("Vel. Máx (km/h)", ascending=False)
            fig = go.Figure(go.Bar(
                x=vmax_r["Jogador"], y=vmax_r["Vel. Máx (km/h)"],
                marker_color=["#e63946" if v >= 28 else "#f39c12" if v >= 25 else "#457b9d"
                               for v in vmax_r["Vel. Máx (km/h)"]],
                text=vmax_r["Vel. Máx (km/h)"].round(1), textposition="outside",
            ))
            fig.update_layout(
                height=300, yaxis_title="km/h",
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="rgba(255,255,255,0.85)", showlegend=False, margin=dict(t=10),
            )
            st.plotly_chart(fig, use_container_width=True)
            html_out = ("<h2>Velocidades Máximas</h2><table><tr><th>Jogador</th><th>Vmáx (km/h)</th></tr>"
                        + "".join(f"<tr><td>{r['Jogador']}</td><td>{r['Vel. Máx (km/h)']:.1f}</td></tr>"
                                  for _, r in vmax_r.iterrows()) + "</table>")
            rendered = True

    # ── Scatter GPS ───────────────────────────────────────────────────────────
    elif bloco_key == "scatter":
        if len(mets_disp) >= 2:
            st.markdown('<p class="section-title">📈 Scatter — Perfil GPS</p>', unsafe_allow_html=True)
            sc1, sc2 = st.columns(2)
            x_sc = sc1.selectbox("Eixo X", mets_disp, index=0, key=f"sc_x_{nome_extra}")
            y_sc = sc2.selectbox("Eixo Y", mets_disp, index=min(1, len(mets_disp)-1), key=f"sc_y_{nome_extra}")
            df_sc = df_base.groupby("Jogador")[mets_disp].mean().reset_index()
            if "Posição" in df_base.columns:
                df_sc["Posição"] = df_sc["Jogador"].map(df_base.groupby("Jogador")["Posição"].last())
            fig = scatter_jogadores(df_sc, x_sc, y_sc,
                                    color_col="Posição" if "Posição" in df_sc.columns else "Jogador",
                                    height=440)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            html_out = f"<h2>Scatter GPS ({x_sc.split('(')[0].strip()} vs {y_sc.split('(')[0].strip()})</h2><p>[Gráfico incluído na versão visual]</p>"
            rendered = True

    # ── Assimetria de carga ───────────────────────────────────────────────────
    elif bloco_key == "assimetria":
        if met_principal in df_base.columns:
            st.markdown(f'<p class="section-title">⚖️ Assimetria — {met_principal.split("(")[0].strip()}</p>', unsafe_allow_html=True)
            df_ass = df_base.groupby("Jogador")[met_principal].mean().reset_index()
            df_ass.columns = ["Jogador", met_principal]
            media_ass = df_ass[met_principal].mean()
            df_ass["Δ%"] = ((df_ass[met_principal] - media_ass) / media_ass * 100).round(1)
            df_ass = df_ass.sort_values("Δ%", ascending=False)
            fig = go.Figure(go.Bar(
                x=df_ass["Jogador"], y=df_ass["Δ%"],
                marker_color=["#e74c3c" if v > 20 else "#2ecc71" if v > -20 else "#3498db"
                               for v in df_ass["Δ%"]],
                text=df_ass["Δ%"].apply(lambda v: f"{v:+.0f}%"), textposition="outside",
            ))
            fig.add_hline(y=0, line_color="rgba(255,255,255,0.3)", line_width=1)
            fig.update_layout(
                height=300, yaxis_title="Δ vs Média Equipa (%)",
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="rgba(255,255,255,0.85)", showlegend=False, margin=dict(t=10),
            )
            st.plotly_chart(fig, use_container_width=True)
            html_out = (f"<h2>Assimetria de Carga</h2>"
                        f"<table><tr><th>Jogador</th><th>{met_principal}</th><th>Δ vs Média</th></tr>"
                        + "".join(f"<tr><td>{r['Jogador']}</td><td>{r[met_principal]:.1f}</td><td>{r['Δ%']:+.1f}%</td></tr>"
                                  for _, r in df_ass.iterrows()) + "</table>")
            rendered = True

    # ── Evolução por Dia MD ───────────────────────────────────────────────────
    elif bloco_key == "evolucao_dia_md":
        if "Dia MD" in df_base.columns and met_principal in df_base.columns:
            st.markdown(f'<p class="section-title">📈 Evolução por Dia MD — {met_principal.split("(")[0].strip()}</p>', unsafe_allow_html=True)
            dias_ord = ["MD-5","MD-4","MD-3","MD-2","MD-1","MD","MD+1","MD+2"]
            ci_dia = df_base.groupby("Dia MD")[met_principal].mean().reset_index()
            ci_dia["ord"] = ci_dia["Dia MD"].apply(lambda d: dias_ord.index(d) if d in dias_ord else 99)
            ci_dia = ci_dia.sort_values("ord")
            fig = go.Figure(go.Bar(
                x=ci_dia["Dia MD"], y=ci_dia[met_principal],
                marker_color="#e63946",
                text=ci_dia[met_principal].round(1), textposition="outside",
            ))
            fig.update_layout(
                height=300, yaxis_title=met_principal,
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="rgba(255,255,255,0.85)", showlegend=False, margin=dict(t=10),
            )
            st.plotly_chart(fig, use_container_width=True)
            html_out = (f"<h2>Evolução por Dia MD — {met_principal.split('(')[0].strip()}</h2>"
                        f"<table><tr><th>Dia MD</th><th>{met_principal}</th></tr>"
                        + "".join(f"<tr><td>{r['Dia MD']}</td><td>{r[met_principal]:.1f}</td></tr>"
                                  for _, r in ci_dia.iterrows()) + "</table>")
            rendered = True

    # ── GPS por posição ───────────────────────────────────────────────────────
    elif bloco_key == "gps_posicao":
        if "Posição" in df_base.columns and met_principal in df_base.columns:
            st.markdown(f'<p class="section-title">📊 {met_principal.split("(")[0].strip()} por Posição</p>', unsafe_allow_html=True)
            df_pos_r = df_base.groupby("Posição")[met_principal].mean().reset_index().sort_values(met_principal, ascending=False)
            fig = px.bar(df_pos_r, x="Posição", y=met_principal,
                         color="Posição", text=df_pos_r[met_principal].round(1),
                         color_discrete_sequence=px.colors.qualitative.Bold)
            fig.update_traces(textposition="outside")
            fig.update_layout(
                height=300, showlegend=False,
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="rgba(255,255,255,0.85)", margin=dict(t=10),
            )
            st.plotly_chart(fig, use_container_width=True)
            html_out = (f"<h2>{met_principal.split('(')[0].strip()} por Posição</h2>"
                        f"<table><tr><th>Posição</th><th>Média</th></tr>"
                        + "".join(f"<tr><td>{r['Posição']}</td><td>{r[met_principal]:.1f}</td></tr>"
                                  for _, r in df_pos_r.iterrows()) + "</table>")
            rendered = True

    # ── Tabela completa ───────────────────────────────────────────────────────
    elif bloco_key == "tabela":
        st.markdown('<p class="section-title">📋 Tabela Completa</p>', unsafe_allow_html=True)
        COLS_TAB = ["Posição"] + mets_disp
        cols_tab_num = [c for c in mets_disp if c in df_base.columns]
        cols_tab = ["Posição"] + cols_tab_num if "Posição" in df_base.columns else cols_tab_num
        # Só colunas numéricas no groupby mean
        df_tab_num = df_base.groupby("Jogador")[cols_tab_num].mean().round(1)
        if "Posição" in df_base.columns:
            df_tab_num.insert(0, "Posição", df_base.groupby("Jogador")["Posição"].last())
        df_tab = df_tab_num
        st.dataframe(df_tab, use_container_width=True)
        html_hdrs = "".join(f"<th>{c}</th>" for c in ["Jogador"] + cols_tab)
        html_rows_t = "".join(
            f"<tr><td>{jog}</td>" + "".join(f"<td>{row[c]:.1f}</td>" if isinstance(row[c], float) else f"<td>{row[c]}</td>" for c in cols_tab) + "</tr>"
            for jog, row in df_tab.iterrows()
        )
        html_out = f"<h2>Tabela Completa</h2><table><tr>{html_hdrs}</tr>{html_rows_t}</table>"
        rendered = True

    # ── Conclusões automáticas ────────────────────────────────────────────────
    elif bloco_key == "conclusoes":
        st.markdown('<p class="section-title">🧠 Conclusões Automáticas</p>', unsafe_allow_html=True)
        conclusoes_html = "<h2>Conclusões</h2><ul>"
        if "Carga Interna" in df_base.columns and df_base["Carga Interna"].notna().any():
            top = df_base.groupby("Jogador")["Carga Interna"].mean().idxmax()
            media_ci = df_base["Carga Interna"].mean()
            msg1 = f"⚡ **Maior carga interna**: {top} ({df_base.groupby('Jogador')['Carga Interna'].mean().max():.0f} UA)"
            msg2 = f"📊 **Média da equipa**: {media_ci:.0f} UA"
            st.markdown(msg1); st.markdown(msg2)
            conclusoes_html += f"<li>{msg1}</li><li>{msg2}</li>"
        if "PSE Sessão" in df_base.columns and df_base["PSE Sessão"].notna().any():
            pse = df_base["PSE Sessão"].mean()
            nivel = "elevada" if pse >= 7 else "moderada" if pse >= 5 else "baixa"
            msg3 = f"💪 **PSE média**: {pse:.1f}/10 — perceção de esforço {nivel}"
            st.markdown(msg3); conclusoes_html += f"<li>{msg3}</li>"
        if "Vel. Máx (km/h)" in df_base.columns and df_base["Vel. Máx (km/h)"].notna().any():
            vmax_top = df_base["Vel. Máx (km/h)"].max()
            jog_vmax = df_base.loc[df_base["Vel. Máx (km/h)"].idxmax(), "Jogador"]
            msg4 = f"🚀 **Velocidade máxima**: {jog_vmax} — {vmax_top:.1f} km/h"
            st.markdown(msg4); conclusoes_html += f"<li>{msg4}</li>"
        acwr_d_c = calcular_acwr_global(df)
        risco_c = [j for j,d in acwr_d_c.items() if "RISCO" in cor_acwr(d["acwr"])]
        if risco_c:
            msg5 = f"🔴 **Risco ACWR**: {', '.join(risco_c)}"
            st.markdown(msg5); conclusoes_html += f"<li>{msg5}</li>"
        if "Hooper Index" in df_base.columns and df_base["Hooper Index"].notna().any():
            hi = df_base["Hooper Index"].mean()
            if hi >= 14:
                msg6 = f"⚠️ **Hooper Index elevado**: {hi:.1f}/20 — monitorizar fadiga"
                st.markdown(msg6); conclusoes_html += f"<li>{msg6}</li>"
        conclusoes_html += "</ul>"
        html_out = conclusoes_html
        rendered = True

    return {"rendered": rendered, "html": html_out}


# ── Definição dos blocos disponíveis ─────────────────────────────────────────
TODOS_BLOCOS = {
    "📊 KPIs / Médias":             "kpis",
    "🏆 Ranking de Exigência":      "ranking",
    "🗺️ Heatmap de Jogadores":      "heatmap",
    "🚦 ACWR — Estado da Equipa":   "acwr",
    "💤 Wellness":                   "wellness",
    "🏃 Velocidades Máximas":       "vmax",
    "📈 Scatter GPS":               "scatter",
    "⚖️ Assimetria de Carga":       "assimetria",
    "📈 Evolução por Dia MD":       "evolucao_dia_md",
    "📊 GPS por Posição":           "gps_posicao",
    "📋 Tabela Completa":           "tabela",
    "🧠 Conclusões Automáticas":    "conclusoes",
}

BLOCOS_DEFAULT_DIA = {"kpis", "ranking", "acwr", "wellness", "conclusoes", "tabela"}
BLOCOS_DEFAULT_MC  = {"kpis", "ranking", "evolucao_dia_md", "acwr", "wellness", "gps_posicao", "conclusoes", "tabela"}


# ═══════════════════════════════════════════════════════════════════════════════
# VISTA: RELATÓRIO DIÁRIO
# ═══════════════════════════════════════════════════════════════════════════════
if seccao == "dashboard":
    hoje = datetime.now()

    # ── Calcular tudo para o dashboard ────────────────────────────────────────
    acwr_dict = calcular_acwr_global(df)
    registar_alertas_automaticos(acwr_dict, df)

    # Classificar jogadores por prioridade
    alertas_criticos = []
    alertas_atencao  = []
    for jog, dados in acwr_dict.items():
        v = dados["acwr"]; estado = cor_acwr(v)
        pos = dados.get("posicao", "—")
        if "RISCO" in estado:
            alertas_criticos.append({"jog": jog, "pos": pos, "tipo": "ACWR", "val": f"{v:.2f}", "msg": "Carga excessiva", "cor": "#e74c3c"})
        elif "ATENÇÃO" in estado:
            alertas_atencao.append({"jog": jog, "pos": pos, "tipo": "ACWR", "val": f"{v:.2f}", "msg": "Monitorizar carga", "cor": "#f39c12"})

    # Wellness alerts
    ultima_sessao = df.sort_values("Data").groupby("Jogador").last().reset_index()
    for _, row in ultima_sessao.iterrows():
        hi = row.get("Hooper Index", np.nan)
        if pd.notna(hi) and hi >= 14:
            alertas_criticos.append({"jog": row["Jogador"], "pos": row.get("Posição","—"), "tipo": "Wellness",
                                      "val": f"{hi:.0f}/20", "msg": "Fadiga/stress elevado", "cor": "#e74c3c"})

    # Vmáx alerts
    if "Vel. Máx (km/h)" in df.columns:
        for jog in df["Jogador"].dropna().unique():
            sub_v = df[df["Jogador"]==jog].dropna(subset=["Data","Vel. Máx (km/h)"]).sort_values("Data")
            if sub_v.empty: continue
            rec = sub_v["Vel. Máx (km/h)"].max()
            acima = sub_v[sub_v["Vel. Máx (km/h)"] >= rec * 0.90]
            if acima.empty: dias_v = 999
            else: dias_v = (sub_v["Data"].max() - acima["Data"].max()).days
            if dias_v > 7:
                alertas_criticos.append({"jog": jog, "pos": "—", "tipo": "Vmáx",
                    "val": f"{dias_v}d", "msg": f"Sem sprint ≥90% há {dias_v} dias", "cor": "#e74c3c"})
            elif dias_v >= 5:
                alertas_atencao.append({"jog": jog, "pos": "—", "tipo": "Vmáx",
                    "val": f"{dias_v}d", "msg": f"Atenção: {dias_v} dias sem ≥90% Vmáx", "cor": "#f39c12"})

    n_alertas_total = len(alertas_criticos) + len(alertas_atencao)

    # KPIs globais
    mc_recente = sorted(df["Microciclo (Nr)"].dropna().unique())[-1] if "Microciclo (Nr)" in df.columns else None
    mc_anterior = sorted(df["Microciclo (Nr)"].dropna().unique())[-2] if mc_recente and len(df["Microciclo (Nr)"].dropna().unique()) >= 2 else None
    ci_media = df[df["Microciclo (Nr)"]==mc_recente]["Carga Interna"].mean() if mc_recente and "Carga Interna" in df.columns else np.nan
    acwr_media = np.mean([d["acwr"] for d in acwr_dict.values()]) if acwr_dict else np.nan
    hooper_media = df[df["Microciclo (Nr)"]==mc_recente]["Hooper Index"].mean() if mc_recente and "Hooper Index" in df.columns else np.nan
    n_risco = len(alertas_criticos)

    # ══════════════════════════════════════════════════════════════════════════
    # RENDERIZAR DASHBOARD
    # ══════════════════════════════════════════════════════════════════════════

    # ── Header ────────────────────────────────────────────────────────────────
    meses = {"January":"Janeiro","February":"Fevereiro","March":"Março","April":"Abril",
             "May":"Maio","June":"Junho","July":"Julho","August":"Agosto",
             "September":"Setembro","October":"Outubro","November":"Novembro","December":"Dezembro"}
    dias_s = {"Monday":"Segunda","Tuesday":"Terça","Wednesday":"Quarta","Thursday":"Quinta",
              "Friday":"Sexta","Saturday":"Sábado","Sunday":"Domingo"}
    data_str = hoje.strftime("%A, %d de %B de %Y")
    for en, pt in {**meses, **dias_s}.items():
        data_str = data_str.replace(en, pt)

    alerta_cor_header = "#e74c3c" if alertas_criticos else "#f39c12" if alertas_atencao else "#2ecc71"
    alerta_icon = "🔴" if alertas_criticos else "🟡" if alertas_atencao else "🟢"
    alerta_msg  = f"{n_alertas_total} alertas ativos" if n_alertas_total > 0 else "Sem alertas — equipa OK"
    clube_nome = _lm_user.get("clube", "")

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0d1117,#161b22);border:1px solid rgba(255,255,255,0.06);
    border-radius:16px;padding:24px 28px 20px;margin-bottom:20px;position:relative;overflow:hidden">
        <div style="position:absolute;top:0;left:0;right:0;height:3px;
        background:linear-gradient(90deg,{alerta_cor_header},transparent)"></div>
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">
            <div>
                <div style="font-size:0.6rem;color:rgba(255,255,255,0.3);letter-spacing:3px;
                text-transform:uppercase;margin-bottom:6px">LoadMonitor{' · ' + clube_nome if clube_nome else ''}</div>
                <div style="font-family:'Space Grotesk',sans-serif;font-size:1.8rem;font-weight:700;
                color:white;line-height:1.1">{data_str}</div>
                <div style="font-size:0.8rem;color:rgba(255,255,255,0.4);margin-top:6px">
                Bem-vindo, {_lm_nome} · MC {int(mc_recente) if mc_recente else '—'} · {df['Jogador'].nunique()} jogadores</div>
            </div>
            <div style="background:{alerta_cor_header}18;border:1px solid {alerta_cor_header}44;
            border-radius:10px;padding:10px 16px;text-align:center">
                <div style="font-size:1.5rem">{alerta_icon}</div>
                <div style="font-size:0.75rem;font-weight:600;color:{alerta_cor_header}">{alerta_msg}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Alertas prioritários (máx 5) ──────────────────────────────────────────
    top_alertas = (alertas_criticos + alertas_atencao)[:5]
    if top_alertas:
        st.markdown('<p class="section-title">🚨 Alertas Prioritários</p>', unsafe_allow_html=True)
        for a in top_alertas:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:12px;padding:10px 16px;margin:3px 0;'
                f'background:{a["cor"]}0d;border-left:3px solid {a["cor"]};border-radius:0 8px 8px 0">'
                f'<div style="min-width:70px"><b style="color:{a["cor"]};font-size:0.9rem">{a["jog"]}</b>'
                f'<div style="font-size:0.65rem;color:#888">{a["pos"]}</div></div>'
                f'<div style="flex:1;font-size:0.8rem;color:rgba(255,255,255,0.7)">{a["msg"]}</div>'
                f'<div style="text-align:right"><span style="background:{a["cor"]}22;color:{a["cor"]};'
                f'padding:3px 8px;border-radius:4px;font-size:0.7rem;font-weight:700">{a["tipo"]} {a["val"]}</span></div>'
                f'</div>',
                unsafe_allow_html=True
            )
    else:
        st.success("✅ Nenhum alerta ativo — toda a equipa dentro dos parâmetros normais.")

    st.divider()

    # ── KPIs principais ───────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)

    # Carga Interna
    if mc_recente and "Carga Interna" in df.columns and not pd.isna(ci_media):
        ci_ant = df[df["Microciclo (Nr)"]==mc_anterior]["Carga Interna"].mean() if mc_anterior else np.nan
        delta_ci = f"{((ci_media-ci_ant)/ci_ant*100):+.0f}% vs MC ant." if not pd.isna(ci_ant) and ci_ant > 0 else None
        k1.metric("⚡ Carga Interna", f"{ci_media:,.0f} UA", delta=delta_ci,
                  help="Média de Carga Interna (PSE × Duração) por sessão no MC atual")
    else:
        k1.metric("⚡ Carga Interna", "—", help="PSE × Duração em minutos")

    # ACWR com zona
    if not pd.isna(acwr_media):
        if acwr_media > 1.5:     acwr_zona, acwr_dc = "🔴 Risco >1.5",    "inverse"
        elif acwr_media > 1.3:   acwr_zona, acwr_dc = "🟡 Atenção 1.3–1.5","off"
        elif acwr_media >= 0.8:  acwr_zona, acwr_dc = "🟢 Zona Segura",    "off"
        else:                    acwr_zona, acwr_dc = "🔵 Sub-carga <0.8", "normal"
        k2.metric("📊 ACWR Médio", f"{acwr_media:.2f}", delta=acwr_zona,
                  delta_color=acwr_dc, help="Rácio Carga Aguda/Crónica · Zona óptima: 0.8–1.3")
    else:
        k2.metric("📊 ACWR Médio", "—", help="Precisa de dados de Carga Interna")

    # Hooper Index (delta invertido — descida = verde)
    if not pd.isna(hooper_media) and "Hooper Index" in df.columns:
        hooper_ant = df[df["Microciclo (Nr)"]==mc_anterior]["Hooper Index"].mean() if mc_anterior else np.nan
        delta_h = f"{((hooper_media-hooper_ant)/hooper_ant*100):+.0f}% vs MC ant." if not pd.isna(hooper_ant) and hooper_ant > 0 else None
        h_estado = "⚠️ Risco" if hooper_media >= 14 else "👀 Monitorizar" if hooper_media >= 10 else "✅ Boa recuperação"
        k3.metric("💤 Hooper Index", f"{hooper_media:.1f}/16",
                  delta=delta_h, delta_color="inverse",
                  help=f"0=Recuperação total · 16=Exaustão · Estado: {h_estado}")
    else:
        k3.metric("💤 Hooper Index", "—", help="Precisa de dados de Wellness")

    # Jogadores em risco com breakdown
    risco_acwr_n = len([a for a in alertas_criticos if a["tipo"]=="ACWR"])
    risco_well_n = len([a for a in alertas_criticos if a["tipo"]=="Wellness"])
    risco_vmax_n = len([a for a in alertas_criticos if a["tipo"]=="Vmáx"])
    k4.metric("🚨 Em Risco", str(n_risco),
              delta=f"ACWR:{risco_acwr_n} · Well:{risco_well_n} · Vmáx:{risco_vmax_n}" if n_risco>0 else "✅ Equipa OK",
              delta_color="off",
              help="Jogadores com ACWR>1.5, Hooper≥14 ou sem sprint ≥90% Vmáx há >7 dias")

    st.divider()


    # ── Recomendação do dia ───────────────────────────────────────────────────
    st.markdown('<p class="section-title">💡 Recomendação do Dia</p>', unsafe_allow_html=True)

    # ── Contexto do Dia MD ────────────────────────────────────────────────────────
    dia_md_hoje = None
    if "Dia MD" in df.columns and "Data" in df.columns and not df.empty:
        ultima_data = df["Data"].dropna().max()
        if pd.notna(ultima_data):
            sessoes_recentes = df[df["Data"].dt.date == ultima_data.date()]
            if not sessoes_recentes.empty:
                moda = sessoes_recentes["Dia MD"].mode()
                dia_md_hoje = moda.iloc[0] if not moda.empty else None

    PERFIL_DIA_MD = {
        "MD-5": {"intensidade":"alta",      "foco":"carga física elevada",            "sprint":True},
        "MD-4": {"intensidade":"media",     "foco":"trabalho técnico-tático",          "sprint":False},
        "MD-3": {"intensidade":"alta",      "foco":"jogos reduzidos competitivos",     "sprint":True},
        "MD-2": {"intensidade":"media",     "foco":"manutenção e velocidade",          "sprint":True},
        "MD-1": {"intensidade":"baixa",     "foco":"ativação pré-jogo e sprints",      "sprint":True},
        "MD":   {"intensidade":"jogo",      "foco":"jogo oficial",                     "sprint":True},
        "MD+1": {"intensidade":"recuperacao","foco":"recuperação ativa",               "sprint":False},
        "MD+2": {"intensidade":"baixa",     "foco":"regeneração e mobilidade",         "sprint":False},
    }
    perfil_hoje = PERFIL_DIA_MD.get(dia_md_hoje)
    recomendacoes = []

    # ── 1. Contexto do Dia MD ─────────────────────────────────────────────────────
    if dia_md_hoje and perfil_hoje:
        if dia_md_hoje in ["MD+1","MD+2"]:
            recomendacoes.append(("🔵", f"DIA {dia_md_hoje} — RECUPERAÇÃO",
                f"Sessão de {perfil_hoje['foco']}. Evitar alta intensidade. "
                f"O sistema neuromuscular ainda está a recuperar do jogo — priorizar mobilidade e regeneração ativa."))
        elif dia_md_hoje == "MD-1":
            recomendacoes.append(("🟡", "DIA MD-1 — ATIVAÇÃO PRÉ-JOGO",
                "Sessão curta e intensa. Incluir sprints de ativação (<5 segundos). "
                "Reduzir volume total — preservar energia para o máximo desempenho amanhã."))
        elif dia_md_hoje == "MD":
            recomendacoes.append(("🎯", "DIA DE JOGO",
                "Aquecimento progressivo com sprints de ativação. "
                "Monitorizar Hooper Index pré-jogo e identificar jogadores com sinais de fadiga."))

    # ── 2. ACWR ───────────────────────────────────────────────────────────────────
    if acwr_dict:
        acwr_vals    = [d["acwr"] for d in acwr_dict.values()]
        n_risco_acwr = len([v for v in acwr_vals if v > 1.5])
        n_atenc_acwr = len([v for v in acwr_vals if 1.3 < v <= 1.5])
        n_sub_acwr   = len([v for v in acwr_vals if v < 0.8])
        jogs_risco_a = [j for j,d in acwr_dict.items() if d["acwr"] > 1.5]
        jogs_atenc_a = [j for j,d in acwr_dict.items() if 1.3 < d["acwr"] <= 1.5]

        # Incluir posição no alerta individual
        def get_pos(jog):
            if "Posição" not in df.columns: return ""
            p = df[df["Jogador"]==jog]["Posição"].dropna()
            return f" ({p.iloc[-1]})" if not p.empty else ""

        if n_risco_acwr >= 3:
            recomendacoes.append(("🔴", "REDUZIR CARGA — EQUIPA",
                f"{n_risco_acwr} jogadores com ACWR>1.5. Sessão de baixa intensidade para toda a equipa. "
                "Foco: trabalho técnico sem pressão, posse estática, mobilidade e recuperação ativa."))
        elif n_risco_acwr >= 1:
            jogs_str = ", ".join(f"{j}{get_pos(j)}" for j in jogs_risco_a)
            atenc_str = f" Monitorizar também: {', '.join(jogs_atenc_a)}." if jogs_atenc_a else ""
            recomendacoes.append(("🟡", "GESTÃO INDIVIDUAL — ACWR",
                f"Reduzir carga de: {jogs_str}. Restante equipa pode treinar normalmente.{atenc_str}"))
        elif n_sub_acwr >= 3 and (not perfil_hoje or perfil_hoje["intensidade"] in ["alta","media"]):
            recomendacoes.append(("🔵", "AUMENTAR ESTÍMULO",
                f"{n_sub_acwr} jogadores em sub-carga crónica (ACWR<0.8). "
                "Incluir: jogos reduzidos de alta intensidade, sprints em transição, pressing intenso."))

    # ── 3. Wellness / Hooper ──────────────────────────────────────────────────────
    if not pd.isna(hooper_media):
        if hooper_media >= 14:
            recomendacoes.append(("🔴", "PRIORIZAR RECUPERAÇÃO — WELLNESS",
                f"Hooper médio {hooper_media:.1f}/16 — fadiga acumulada significativa. "
                "Reduzir volume e intensidade desta sessão. Foco em mobilidade e recuperação."))
        elif hooper_media >= 10:
            ul_df = df.sort_values("Data").groupby("Jogador").last().reset_index() if "Hooper Index" in df.columns else pd.DataFrame()
            jogs_hi = ul_df[ul_df["Hooper Index"] >= 12]["Jogador"].tolist() if not ul_df.empty else []
            if jogs_hi:
                recomendacoes.append(("🟡", "WELLNESS EM ATENÇÃO",
                    f"Hooper médio moderado ({hooper_media:.1f}/16). "
                    f"Jogadores a monitorizar: {', '.join(jogs_hi[:3])}. Considerar redução individual."))

    # ── 4. Exposição a alta velocidade ───────────────────────────────────────────
    n_sem_sprint = len([a for a in alertas_criticos + alertas_atencao if a["tipo"] == "Vmáx"])
    sprint_indicado = perfil_hoje["sprint"] if perfil_hoje else True

    if n_sem_sprint >= 2:
        jogs_v = [a["jog"] for a in alertas_criticos + alertas_atencao if a["tipo"] == "Vmáx"]
        if sprint_indicado:
            recomendacoes.append(("🏃", "INCLUIR EXPOSIÇÃO A ALTA VELOCIDADE",
                f"{n_sem_sprint} jogadores sem sprint ≥90% Vmáx recentemente: {', '.join(jogs_v[:4])}. "
                "Incluir: situações 1v1 em espaço amplo, acelerações em transição, sprints progressivos."))
        else:
            recomendacoes.append(("ℹ️", "NOTA — VELOCIDADE MÁXIMA",
                f"{n_sem_sprint} jogadores sem exposição recente a alta velocidade. "
                f"O perfil deste dia ({dia_md_hoje or 'atual'}) não é ideal para sprints máximos — "
                "planear exposição na próxima sessão de alta intensidade."))

    # ── Default ───────────────────────────────────────────────────────────────────
    if not recomendacoes:
        foco_txt = f" Para este {dia_md_hoje}: foco em {perfil_hoje['foco']}." if perfil_hoje and dia_md_hoje else ""
        recomendacoes.append(("🟢", "MANTER PLANO",
            f"Equipa dentro dos parâmetros normais.{foco_txt} Continuar a monitorizar individualmente."))

    # ── Renderizar badge Dia MD + recomendações ────────────────────────────────────
    if dia_md_hoje:
        cor_dia = {"MD-5":"#e63946","MD-4":"#f39c12","MD-3":"#e63946",
                   "MD-2":"#f39c12","MD-1":"#9b59b6","MD":"#e63946",
                   "MD+1":"#3498db","MD+2":"#2ecc71"}.get(dia_md_hoje,"#888")
        foco_str = perfil_hoje["foco"] if perfil_hoje else "Treino"
        st.markdown(
            f'<div style="display:inline-flex;align-items:center;gap:8px;background:{cor_dia}15;'
            f'border:1px solid {cor_dia}40;border-radius:8px;padding:6px 14px;margin-bottom:10px">'
            f'<span style="font-family:monospace;font-weight:700;color:{cor_dia};font-size:0.85rem">{dia_md_hoje}</span>'
            f'<span style="font-size:0.75rem;color:rgba(255,255,255,0.5)">{foco_str}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    COR_REC = {"🔴":"#e74c3c","🟡":"#f39c12","🟢":"#2ecc71","🔵":"#3498db",
               "🏃":"#f39c12","🎯":"#e63946","ℹ️":"#7f8c8d"}
    for icon, titulo, texto in recomendacoes[:3]:
        cor_rec = COR_REC.get(icon, "#888")
        st.markdown(
            f'<div style="background:{cor_rec}0a;border:1px solid {cor_rec}30;border-radius:12px;'
            f'padding:16px 20px;margin:6px 0">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">'
            f'<span style="font-size:1.2rem">{icon}</span>'
            f'<span style="font-weight:700;font-size:0.85rem;color:{cor_rec};letter-spacing:1px">{titulo}</span>'
            f'</div>'
            f'<div style="font-size:0.82rem;color:rgba(255,255,255,0.75);line-height:1.6">{texto}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    st.divider()

    # ── Evolução ACWR (últimos 4 MC) ──────────────────────────────────────────
    col_chart, col_topbot = st.columns([2, 1])

    with col_chart:
        st.markdown('<p class="section-title">📈 Evolução da Carga</p>', unsafe_allow_html=True)
        if "Carga Interna" in df.columns and "Microciclo (Nr)" in df.columns:
            mcs_ultimos = sorted(df["Microciclo (Nr)"].dropna().unique())[-6:]
            ci_evolucao = df[df["Microciclo (Nr)"].isin(mcs_ultimos)].groupby("Microciclo (Nr)")["Carga Interna"].mean().reset_index()
            ci_evolucao = ci_evolucao.sort_values("Microciclo (Nr)")
            fig_ci_dash = go.Figure()
            fig_ci_dash.add_trace(go.Scatter(
                x=ci_evolucao["Microciclo (Nr)"].astype(str),
                y=ci_evolucao["Carga Interna"],
                mode="lines+markers+text",
                text=ci_evolucao["Carga Interna"].round(0).astype(int).astype(str),
                textposition="top center",
                textfont=dict(size=10, color="white"),
                line=dict(color="#e63946", width=3),
                marker=dict(size=10, color="#e63946", line=dict(width=2, color="white")),
                fill="tozeroy", fillcolor="rgba(230,57,70,0.06)",
            ))
            fig_ci_dash.update_layout(
                height=260, yaxis_title="CI Médio (UA)",
                xaxis_title="Microciclo",
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="rgba(255,255,255,0.85)", showlegend=False,
                margin=dict(t=10, b=30, l=50, r=10),
                xaxis=dict(gridcolor="rgba(255,255,255,0.04)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.04)"),
            )
            st.plotly_chart(fig_ci_dash, use_container_width=True)

    with col_topbot:
        st.markdown('<p class="section-title">📊 Carga por Jogador</p>', unsafe_allow_html=True)
        if mc_recente and "Carga Interna" in df.columns:
            ci_jog = df[df["Microciclo (Nr)"]==mc_recente].groupby("Jogador")["Carga Interna"].mean().sort_values(ascending=False)
            if len(ci_jog) >= 3:
                # Top 3
                st.markdown("**🔼 Mais carga:**")
                for jog, val in ci_jog.head(3).items():
                    st.markdown(f'<div style="font-size:0.8rem;padding:3px 0;color:rgba(255,255,255,0.8)">'
                                f'<b style="color:#e63946">{jog}</b> — {val:,.0f} UA</div>', unsafe_allow_html=True)
                st.markdown("")
                # Bottom 3
                st.markdown("**🔽 Menos carga:**")
                for jog, val in ci_jog.tail(3).items():
                    st.markdown(f'<div style="font-size:0.8rem;padding:3px 0;color:rgba(255,255,255,0.8)">'
                                f'<b style="color:#3498db">{jog}</b> — {val:,.0f} UA</div>', unsafe_allow_html=True)

    st.divider()

    # ── Quick Actions ─────────────────────────────────────────────────────────
    st.markdown('<p class="section-title">⚡ Ações Rápidas</p>', unsafe_allow_html=True)
    qa1, qa2, qa3, qa4 = st.columns(4)
    if qa1.button("👤 Ver Jogadores", use_container_width=True):
        st.session_state["seccao"] = "jogadores"; st.rerun()
    if qa2.button("🏟️ Ver Equipa", use_container_width=True):
        st.session_state["seccao"] = "equipa"; st.rerun()
    if qa3.button("📋 Planeamento", use_container_width=True):
        st.session_state["seccao"] = "planeamento"; st.rerun()
    if qa4.button("🔬 Avançado", use_container_width=True):
        st.session_state["seccao"] = "avancado"; st.rerun()

    # ── Export button ─────────────────────────────────────────────────────────
    st.divider()
    alertas_html = "".join(
        f'<tr><td style="color:{a["cor"]};font-weight:700">{a["jog"]}</td>'
        f'<td>{a["tipo"]}</td><td>{a["msg"]}</td><td><b>{a["val"]}</b></td></tr>'
        for a in top_alertas
    )
    rec_html = "".join(f"<li><b>{t}:</b> {txt}</li>" for _, t, txt in recomendacoes[:3])
    ci_media_str   = f"{ci_media:,.0f}"   if not pd.isna(ci_media)   else "—"
    acwr_media_str = f"{acwr_media:.2f}"  if not pd.isna(acwr_media) else "—"
    hooper_str     = f"{hooper_media:.1f}" if not pd.isna(hooper_media) else "—"
    html_dash = gerar_pdf_html(f"""
<h1 style="color:#e63946">Dashboard — {data_str}</h1>
<table><tr><th>CI Médio</th><th>ACWR Médio</th><th>Hooper</th><th>Alertas</th></tr>
<tr><td>{ci_media_str}</td><td>{acwr_media_str}</td>
<td>{hooper_str}/20</td><td>{n_risco}</td></tr></table>
<h2>Alertas Prioritários</h2>
<table><tr><th>Jogador</th><th>Tipo</th><th>Descrição</th><th>Valor</th></tr>{alertas_html}</table>
<h2>Recomendações</h2><ul>{rec_html}</ul>
""", f"Dashboard_{hoje.strftime('%Y%m%d')}.html")
    botao_download_html(html_dash, f"Dashboard_{hoje.strftime('%Y%m%d')}.html", "📥 Exportar Resumo do Dia")



elif seccao == "equipa":
    lm_header("Equipa", "Visão global do plantel — carga, GPS, wellness e performance", "Equipa")
    tab_eq = st.tabs(["📊 Visão Geral", "📐 Por Posição", "🏃 Vmáx"])

    with tab_eq[0]:
        df_f = df_f_dia
        st.caption(f"{len(df_f)} registos · {df_f['Jogador'].nunique()} jogadores · {len(mc_sel)} microciclo(s) selecionado(s)")

        # ── KPIs globais com tendência ────────────────────────────────────────────
        mc_atual_eq  = mc_sel[0] if mc_sel else None
        mcs_todos    = sorted(df["Microciclo (Nr)"].dropna().unique())
        mc_ant_eq    = mcs_todos[mcs_todos.index(mc_atual_eq)-1] if mc_atual_eq in mcs_todos and mcs_todos.index(mc_atual_eq) > 0 else None

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Sessões Totais", f"{len(df_f):,}", help="Total de registos nos filtros selecionados")

        for col_st, col_nm, fmt, label, ajuda, inverter in [
                (c2, "Distância Total (m)", ":,.0f", "Dist. Média (m)", "Distância média por sessão",         False),
                (c3, "PSE Sessão",          ":.1f",  "PSE Média",       "Perceção Subjetiva de Esforço média", False),
                (c4, "Carga Interna",       ":,.0f", "CI Médio",        "Carga Interna média (PSE × Duração)", False),
                (c5, "Hooper Index",        ":.1f",  "Hooper Médio",    "Hooper ↓ = melhor recuperação (verde quando desce)", True),
        ]:
                if col_nm in df_f.columns and mc_atual_eq:
                    val, delta = calcular_delta(df, col_nm, mc_atual_eq, mc_ant_eq)
                    # Hooper: delta negativo é BOM (menos stress/fadiga) → inverter sinal para Streamlit
                    delta_display = (-delta) if (delta is not None and inverter) else delta
                    delta_str = f"{delta_display:+.1f}% vs MC ant." if delta_display is not None else None
                    col_st.metric(label, format(val, fmt.lstrip(":")) if val is not None and not pd.isna(val) else "—",
                                  delta=delta_str,
                                  delta_color="inverse" if inverter else "normal",
                                  help=ajuda)
                else:
                    col_st.metric(label, "—", help=ajuda)

        st.divider()

        # ── ACWR por jogador (último valor) ───────────────────────────────────────
        st.markdown('<p class="section-title">🚦 ACWR — Risco por Jogador (última sessão)</p>', unsafe_allow_html=True)

        acwr_rows = []
        for jog in jogadores:
                sub = calcular_acwr(df[df["Microciclo (Nr)"].isin(mc_sel)] if mc_sel else df, jog)
                if not sub.empty and "ACWR" in sub.columns and sub["ACWR"].notna().any():
                    last = sub.dropna(subset=["ACWR"]).iloc[-1]
                    acwr_rows.append({
                        "Jogador": jog,
                        "Posição": last.get("Posição", ""),
                        "ACWR": round(last["ACWR"], 2),
                        "CI Agudo": round(last.get("EWMA_Aguda", 0)),
                        "CI Crónico": round(last.get("EWMA_Crónica", 0)),
                        "Estado": cor_acwr(last["ACWR"]),
                    })

        if acwr_rows:
                df_acwr = pd.DataFrame(acwr_rows).sort_values("ACWR", ascending=False)
                df_acwr["ACWR"] = pd.to_numeric(df_acwr["ACWR"], errors="coerce").fillna(0)

                fig_acwr = go.Figure()
                cores = []
                for _, row in df_acwr.iterrows():
                    v = row["ACWR"]
                    if v > 1.5:    cor = "#e74c3c"
                    elif v > 1.3:  cor = "#f39c12"
                    elif v >= 0.8: cor = "#2ecc71"
                    else:           cor = "#3498db"
                    cores.append(cor)

                fig_acwr.add_trace(go.Bar(
                    x=df_acwr["Jogador"], y=df_acwr["ACWR"],
                    marker_color=cores, text=df_acwr["ACWR"].round(2), textposition="outside",
                ))
                fig_acwr.add_hline(y=1.5, line_dash="dash", line_color="#e74c3c",  annotation_text="Risco (1.5)")
                fig_acwr.add_hline(y=1.3, line_dash="dash", line_color="#f39c12",  annotation_text="Atenção (1.3)")
                fig_acwr.add_hline(y=0.8, line_dash="dash", line_color="#3498db",  annotation_text="Sub-carga (0.8)")
                fig_acwr.update_layout(
                    yaxis_title="ACWR", height=380, plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                    showlegend=False, margin=dict(t=20, b=10),
                )
                st.plotly_chart(fig_acwr, use_container_width=True)

                # tabela resumo
                st.dataframe(
                    df_acwr.set_index("Jogador")[["Posição", "ACWR", "CI Agudo", "CI Crónico", "Estado"]],
                    use_container_width=True,
                )

        st.divider()

        # ── Carga Interna por microciclo ──────────────────────────────────────────
        st.markdown('<p class="section-title">📈 Carga Interna Média por Microciclo</p>', unsafe_allow_html=True)

        if "Carga Interna" in df_f and "Microciclo (Nr)" in df_f:
                ci_mc = df_f.groupby(["Microciclo (Nr)", "Jogador"])["Carga Interna"].mean().reset_index()
                ci_mc_mean = df_f.groupby("Microciclo (Nr)")["Carga Interna"].mean().reset_index()
                fig_ci = px.line(ci_mc_mean, x="Microciclo (Nr)", y="Carga Interna",
                                 markers=True, labels={"Carga Interna": "CI Médio", "Microciclo (Nr)": "Microciclo"})
                fig_ci.update_traces(line_color="#e63946", line_width=3, marker_size=8)
                fig_ci.update_layout(height=300, plot_bgcolor="rgba(0,0,0,0)",
                                      paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)", margin=dict(t=20))
                st.plotly_chart(fig_ci, use_container_width=True)

        # ── Distribuição GPS ──────────────────────────────────────────────────────
        st.divider()
        st.markdown('<p class="section-title">🏃 Métricas GPS — Distribuição por Jogador</p>', unsafe_allow_html=True)

        _mets_gps_eq = get_mets_gps(df_f)
        metrica_gps = st.selectbox("Métrica GPS", _mets_gps_eq, key="eq_met_gps") if _mets_gps_eq else None
        if metrica_gps and metrica_gps in df_f.columns:
                df_gps = df_f.groupby("Jogador")[metrica_gps].mean().reset_index().sort_values(metrica_gps, ascending=True)
                fig_gps = px.bar(df_gps, x=metrica_gps, y="Jogador", orientation="h",
                                 color=metrica_gps, color_continuous_scale="Reds",
                                 labels={metrica_gps: metrica_gps, "Jogador": ""})
                fig_gps.update_layout(height=max(300, len(df_gps)*35), plot_bgcolor="rgba(0,0,0,0)",
                                       paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                                       coloraxis_showscale=False, margin=dict(t=10))
                st.plotly_chart(fig_gps, use_container_width=True)

        # ── Scatter GPS — Perfil físico do plantel ────────────────────────────────
        st.divider()
        st.markdown('<p class="section-title">🎯 Scatter — Perfil Físico do Plantel</p>', unsafe_allow_html=True)
        st.caption("Cada círculo = um jogador. Posiciona-se de acordo com as duas métricas escolhidas.")

        METS_SCATTER = get_mets_gps(df)
        mets_sc_disp = [m for m in METS_SCATTER if m in df_f.columns]

        if len(mets_sc_disp) >= 2:
                sc_col1, sc_col2, sc_col3 = st.columns(3)
                x_sc = sc_col1.selectbox("Eixo X", mets_sc_disp, index=0, key="eq_sc_x")
                y_sc = sc_col2.selectbox("Eixo Y", mets_sc_disp, index=1, key="eq_sc_y")
                size_sc = sc_col3.selectbox("Tamanho (opcional)", ["—"] + mets_sc_disp, index=0, key="eq_sc_size")

                # Médias por jogador
                df_sc_eq = df_f.groupby("Jogador")[mets_sc_disp].mean().reset_index()
                if "Posição" in df_f.columns:
                    pos_map = df_f.groupby("Jogador")["Posição"].last()
                    df_sc_eq["Posição"] = df_sc_eq["Jogador"].map(pos_map)

                fig_sc_eq = scatter_jogadores(
                    df_sc_eq, x_sc, y_sc,
                    title=f"{x_sc.split('(')[0].strip()} vs {y_sc.split('(')[0].strip()} — Médias do Plantel",
                    color_col="Posição" if "Posição" in df_sc_eq.columns else "Jogador",
                    size_col=size_sc if size_sc != "—" else None,
                    height=520,
                )
                if fig_sc_eq:
                    st.plotly_chart(fig_sc_eq, use_container_width=True)
                    st.caption("🟢 Quadrante superior direito = acima da média em ambas as métricas · Linhas pontilhadas = média da equipa")

        # ── Wellness da equipa ────────────────────────────────────────────────────
        st.divider()
        st.markdown('<p class="section-title">💤 Wellness da Equipa (médias)</p>', unsafe_allow_html=True)

        wellness_cols = ["Sono (1-5)", "Dor Musc. (1-5)", "Stress (1-5)", "Humor (1-5)", "Hooper Index"]
        wellness_disp = [c for c in wellness_cols if c in df_f.columns]

        if wellness_disp:
                w_mean = df_f[wellness_disp].mean().reset_index()
                w_mean.columns = ["Métrica", "Média"]
                fig_w = px.bar(w_mean, x="Métrica", y="Média", color="Métrica",
                               color_discrete_sequence=px.colors.qualitative.Pastel,
                               text=w_mean["Média"].round(1))
                fig_w.update_traces(textposition="outside")
                fig_w.update_layout(height=320, showlegend=False, plot_bgcolor="rgba(0,0,0,0)",
                                     paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)", margin=dict(t=10))
                st.plotly_chart(fig_w, use_container_width=True)

        # ── Conclusões automáticas ────────────────────────────────────────────────
        st.divider()
        st.markdown('<p class="section-title">🧠 Conclusões Automáticas</p>', unsafe_allow_html=True)

        insights = []

        if acwr_rows:
                em_risco    = [r["Jogador"] for r in acwr_rows if "RISCO"    in r["Estado"]]
                em_atencao  = [r["Jogador"] for r in acwr_rows if "ATENÇÃO"  in r["Estado"]]
                sub_carga   = [r["Jogador"] for r in acwr_rows if "SUB-CARGA" in r["Estado"]]

                if em_risco:
                    insights.append(f"🔴 **Risco de lesão elevado**: {', '.join(em_risco)} — ACWR > 1.5. Reduzir carga imediatamente.")
                if em_atencao:
                    insights.append(f"🟡 **Monitorizar de perto**: {', '.join(em_atencao)} — ACWR entre 1.3 e 1.5.")
                if sub_carga:
                    insights.append(f"🔵 **Sub-carga**: {', '.join(sub_carga)} — ACWR < 0.8. Avaliar razão (lesão/recuperação?).")
                if not em_risco and not em_atencao:
                    insights.append("🟢 **Toda a equipa dentro do intervalo seguro de ACWR (0.8–1.3).**")

        if "Hooper Index" in df_f.columns:
                h_mean = df_f["Hooper Index"].mean()
                if h_mean >= 14:
                    insights.append(f"⚠️ **Hooper Index médio elevado** ({h_mean:.1f}/20) — equipa com sinais de fadiga/stress acumulado.")
                elif h_mean <= 8:
                    insights.append(f"✅ **Hooper Index médio excelente** ({h_mean:.1f}/20) — bem-estar geral muito positivo.")
                else:
                    insights.append(f"ℹ️ **Hooper Index médio** ({h_mean:.1f}/20) — bem-estar dentro dos parâmetros normais.")

        if "PSE Sessão" in df_f.columns:
                pse_mean = df_f["PSE Sessão"].mean()
                insights.append(f"📊 **PSE média da equipa**: {pse_mean:.1f}/10 nos microciclos selecionados.")

        if "Distância Total (m)" in df_f.columns:
                dist_mean = df_f["Distância Total (m)"].mean()
                insights.append(f"📏 **Distância média por sessão**: {dist_mean:,.0f} m.")

        for ins in insights:
                st.markdown(ins)


        # ═══════════════════════════════════════════════════════════════════════════════
        # VISTA: JOGADOR INDIVIDUAL
        # ═══════════════════════════════════════════════════════════════════════════════

    # ── Conclusões automáticas da equipa ─────────────────────────────────────────
        st.divider()
        st.markdown('<p class="section-title">🧠 Análise Rápida da Equipa</p>', unsafe_allow_html=True)

        _insights_eq = []
        _acwr_global = calcular_acwr_global(df)
        _n_risco_eq  = sum(1 for d in _acwr_global.values() if d["acwr"] > 1.5)
        _n_sub_eq    = sum(1 for d in _acwr_global.values() if d["acwr"] < 0.8)
        _n_atenc_eq  = sum(1 for d in _acwr_global.values() if 1.3 < d["acwr"] <= 1.5)

        if _n_risco_eq > 0:
            _jogs_r = [j for j,d in _acwr_global.items() if d["acwr"] > 1.5]
            _insights_eq.append(("#e74c3c", f"🔴 {_n_risco_eq} jogador(es) em risco de sobrecarga (ACWR>1.5): {', '.join(_jogs_r)}. Reduzir carga individual."))
        if _n_atenc_eq > 0:
            _insights_eq.append(("#f39c12", f"🟡 {_n_atenc_eq} jogador(es) em zona de atenção (1.3<ACWR≤1.5). Monitorizar nas próximas sessões."))
        if _n_sub_eq > 0:
            _insights_eq.append(("#3498db", f"🔵 {_n_sub_eq} jogador(es) em sub-carga (ACWR<0.8). Considerar aumentar estímulo."))
        if _n_risco_eq == 0 and _n_atenc_eq == 0:
            _insights_eq.append(("#2ecc71", "🟢 Toda a equipa dentro da zona segura de ACWR. Continuar o plano do microciclo."))

        if "Hooper Index" in df_f.columns:
            _hi_eq = df_f["Hooper Index"].mean()
            if not pd.isna(_hi_eq):
                if _hi_eq >= 14:    _insights_eq.append(("#e74c3c", f"🔴 Hooper médio elevado ({_hi_eq:.1f}/16) — equipa com sinais de fadiga acumulada. Reduzir volume e carga desta sessão."))
                elif _hi_eq >= 10:  _insights_eq.append(("#f39c12", f"🟡 Hooper médio ({_hi_eq:.1f}/16) — recuperação moderada. Atenção ao contexto individual."))
                else:                _insights_eq.append(("#2ecc71", f"🟢 Hooper médio baixo ({_hi_eq:.1f}/16) — boa recuperação geral da equipa."))

        for _cor, _txt in _insights_eq:
            st.markdown(
                f'<div style="border-left:3px solid {_cor};padding:10px 16px;margin:4px 0;'
                f'background:{_cor}12;border-radius:0 8px 8px 0;font-size:0.85rem;line-height:1.5">{_txt}</div>',
                unsafe_allow_html=True
            )

    with tab_eq[1]:
            df_f = df_f_dia

            if "Posição" not in df_f.columns or df_f["Posição"].isna().all():
                st.warning("Coluna 'Posição' não encontrada nos dados.")

            metrica_pos = st.selectbox("Métrica a comparar", [
                "Distância Total (m)", "HSR (m)", "Sprint (m)",
                "Carga Interna", "PSE Sessão", "Vel. Máx (km/h)", "Hooper Index"
            ])

            if metrica_pos in df_f.columns:
                # Box plot por posição
                fig_box = px.box(df_f, x="Posição", y=metrica_pos,
                                 color="Posição", points="all",
                                 hover_data=["Jogador", "Data"] if "Data" in df_f.columns else ["Jogador"],
                                 color_discrete_sequence=px.colors.qualitative.Bold)
                fig_box.update_layout(height=420, plot_bgcolor="rgba(0,0,0,0)",
                                       paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                                       showlegend=False, margin=dict(t=20))
                st.plotly_chart(fig_box, use_container_width=True)

                # Scatter por posição
                st.divider()
                st.markdown('<p class="section-title">🎯 Scatter — Jogadores por Posição</p>', unsafe_allow_html=True)
                st.caption("Cada círculo = um jogador, cor = posição. Identifica padrões e outliers.")

                METS_SC_POS = get_mets_gps(df_f)
                mets_sc_pos = [m for m in METS_SC_POS if m in df_f.columns and df_f[m].notna().any()]

                if len(mets_sc_pos) >= 2:
                    sc_p1, sc_p2 = st.columns(2)
                    x_sc_pos = sc_p1.selectbox("Eixo X", mets_sc_pos, index=0, key="pos_sc_x")
                    y_sc_pos = sc_p2.selectbox("Eixo Y", mets_sc_pos, index=1, key="pos_sc_y")
                    df_sc_pos = df_f.groupby("Jogador")[mets_sc_pos].mean().reset_index()
                    if "Posição" in df_f.columns:
                        pos_map2 = df_f.groupby("Jogador")["Posição"].last()
                        df_sc_pos["Posição"] = df_sc_pos["Jogador"].map(pos_map2)
                    fig_sc_pos = scatter_jogadores(
                        df_sc_pos, x_sc_pos, y_sc_pos,
                        title=f"{x_sc_pos.split('(')[0].strip()} vs {y_sc_pos.split('(')[0].strip()}",
                        color_col="Posição" if "Posição" in df_sc_pos.columns else "Jogador",
                        height=500,
                    )
                    if fig_sc_pos:
                        st.plotly_chart(fig_sc_pos, use_container_width=True)

                st.divider()
                # Médias por posição e jogador
                st.markdown('<p class="section-title">Médias por Posição e Jogador</p>', unsafe_allow_html=True)
                df_pos = df_f.groupby(["Posição", "Jogador"])[metrica_pos].mean(numeric_only=True).reset_index()
                df_pos.columns = ["Posição", "Jogador", metrica_pos]
                df_pos = df_pos.sort_values([metrica_pos], ascending=False)

                fig_jog_pos = px.bar(df_pos, x="Jogador", y=metrica_pos,
                                      color="Posição", barmode="group",
                                      color_discrete_sequence=px.colors.qualitative.Bold,
                                      labels={metrica_pos: metrica_pos, "Jogador": ""})
                fig_jog_pos.update_layout(height=360, plot_bgcolor="rgba(0,0,0,0)",
                                           paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)", margin=dict(t=10))
                st.plotly_chart(fig_jog_pos, use_container_width=True)

            # Radar por posição
            st.divider()
            st.markdown('<p class="section-title">📡 Radar de Perfil por Posição</p>', unsafe_allow_html=True)

            radar_cols = get_mets_gps(df)
            radar_disp = [c for c in radar_cols if c in df_f.columns]

            if radar_disp:
                pos_means = df_f.groupby("Posição")[radar_disp].mean(numeric_only=True).reset_index()
                # Normalizar 0-100
                for col in radar_disp:
                    max_v = pos_means[col].max()
                    pos_means[col] = pos_means[col] / max_v * 100 if max_v > 0 else 0

                fig_radar = go.Figure()
                cores_radar = px.colors.qualitative.Bold
                for i, (_, row) in enumerate(pos_means.iterrows()):
                    vals = list(row[radar_disp]) + [row[radar_disp[0]]]
                    cats = radar_disp + [radar_disp[0]]
                    fig_radar.add_trace(go.Scatterpolar(
                        r=vals, theta=cats, fill="toself",
                        name=row["Posição"],
                        line_color=cores_radar[i % len(cores_radar)],
                        opacity=0.75,
                    ))
                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                    height=440, plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                )
                st.plotly_chart(fig_radar, use_container_width=True)


        # ═══════════════════════════════════════════════════════════════════════════════
        # VISTA: VMÁX MONITOR
        # ═══════════════════════════════════════════════════════════════════════════════

    with st.expander("🔄 Comparar Microciclos", expanded=False):

            METS_COMP = get_mets_gps(df)
            mets_comp_disp = [m for m in METS_COMP if m in df.columns]

            mcs_todos = sorted(df["Microciclo (Nr)"].dropna().unique(), reverse=True)
            if len(mcs_todos) < 2:
                st.warning("Precisas de pelo menos 2 microciclos para comparar.")

            col_mc1, col_mc2, col_mc3 = st.columns(3)
            mc_A = col_mc1.selectbox("Microciclo A", mcs_todos, index=0, key="comp_mcA")
            mc_B = col_mc2.selectbox("Microciclo B", mcs_todos, index=1, key="comp_mcB")
            nivel_comp = col_mc3.radio("Nível", ["Equipa", "Jogador"], horizontal=True, key="comp_nivel")

            if mc_A == mc_B:
                st.warning("Seleciona dois microciclos diferentes.")

            df_A = df[df["Microciclo (Nr)"] == mc_A]
            df_B = df[df["Microciclo (Nr)"] == mc_B]

            st.divider()

            if nivel_comp == "Equipa":
                # ── KPIs lado a lado ──────────────────────────────────────────────────
                st.markdown('<p class="section-title">📊 Médias da Equipa — Lado a Lado</p>', unsafe_allow_html=True)

                n_mets = len(mets_comp_disp)
                cols_comp = st.columns(n_mets)
                for i, met in enumerate(mets_comp_disp):
                    val_A = df_A[met].mean()
                    val_B = df_B[met].mean()
                    if pd.isna(val_A) and pd.isna(val_B):
                        continue
                    delta = ((val_A - val_B) / abs(val_B) * 100) if (not pd.isna(val_B) and val_B != 0) else None
                    delta_str = f"{delta:+.1f}% vs MC {int(mc_B)}" if delta is not None else None
                    label = met.replace(" (m)","").replace(" (n)","").replace(" (km/h)","")
                    cols_comp[i].metric(
                        f"{label} (MC {int(mc_A)})",
                        f"{val_A:,.1f}" if not pd.isna(val_A) else "—",
                        delta=delta_str,
                        help=f"MC {int(mc_A)}: {val_A:,.1f} | MC {int(mc_B)}: {val_B:,.1f}"
                    )

                st.divider()

                # ── Gráfico barras agrupadas ───────────────────────────────────────────
                st.markdown('<p class="section-title">📊 Comparação Visual — Todas as Métricas</p>', unsafe_allow_html=True)

                comp_rows = []
                for met in mets_comp_disp:
                    val_A = df_A[met].mean()
                    val_B = df_B[met].mean()
                    if pd.isna(val_A) and pd.isna(val_B): continue
                    comp_rows.append({"Métrica": met.split("(")[0].strip(),
                                       f"MC {int(mc_A)}": round(val_A, 1) if not pd.isna(val_A) else 0,
                                       f"MC {int(mc_B)}": round(val_B, 1) if not pd.isna(val_B) else 0})

                if comp_rows:
                    df_comp = pd.DataFrame(comp_rows)
                    fig_comp = go.Figure()
                    fig_comp.add_trace(go.Bar(
                        name=f"MC {int(mc_A)}", x=df_comp["Métrica"],
                        y=df_comp[f"MC {int(mc_A)}"],
                        marker_color="#e63946", text=df_comp[f"MC {int(mc_A)}"].round(1),
                        textposition="outside",
                    ))
                    fig_comp.add_trace(go.Bar(
                        name=f"MC {int(mc_B)}", x=df_comp["Métrica"],
                        y=df_comp[f"MC {int(mc_B)}"],
                        marker_color="#457b9d", text=df_comp[f"MC {int(mc_B)}"].round(1),
                        textposition="outside",
                    ))
                    fig_comp.update_layout(
                        barmode="group", height=420,
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font_color="rgba(255,255,255,0.85)", margin=dict(t=30),
                        legend=dict(orientation="h", y=1.05),
                    )
                    st.plotly_chart(fig_comp, use_container_width=True)

                st.divider()

                # ── Radar comparativo ──────────────────────────────────────────────────
                st.markdown('<p class="section-title">📡 Radar Comparativo</p>', unsafe_allow_html=True)
                mets_radar = [m for m in get_mets_gps(df_f)[:6] if m in df.columns]
                if len(mets_radar) >= 3:
                    max_vals = {m: df[m].replace(0, np.nan).max() for m in mets_radar if m in df.columns and df[m].notna().any()}
                    vals_A = [df_A[m].mean() / max_vals[m] * 100 if max_vals[m] > 0 else 0 for m in mets_radar]
                    vals_B = [df_B[m].mean() / max_vals[m] * 100 if max_vals[m] > 0 else 0 for m in mets_radar]
                    labs   = [m.split("(")[0].strip() for m in mets_radar]

                    fig_radar_comp = go.Figure()
                    fig_radar_comp.add_trace(go.Scatterpolar(
                        r=vals_A + [vals_A[0]], theta=labs + [labs[0]],
                        fill="toself", name=f"MC {int(mc_A)}", line_color="#e63946", opacity=0.8,
                    ))
                    fig_radar_comp.add_trace(go.Scatterpolar(
                        r=vals_B + [vals_B[0]], theta=labs + [labs[0]],
                        fill="toself", name=f"MC {int(mc_B)}", line_color="#457b9d", opacity=0.8,
                    ))
                    fig_radar_comp.update_layout(
                        polar=dict(radialaxis=dict(visible=True, range=[0,100], ticksuffix="%")),
                        height=440, plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                    )
                    st.plotly_chart(fig_radar_comp, use_container_width=True)

                # ── Dia MD comparativo ─────────────────────────────────────────────────
                if "Dia MD" in df.columns:
                    st.divider()
                    st.markdown('<p class="section-title">📅 Por Dia MD — Comparação</p>', unsafe_allow_html=True)
                    met_dia_comp = st.selectbox("Métrica", mets_comp_disp, key="comp_dia_met")
                    dias_ordem = ["MD-5","MD-4","MD-3","MD-2","MD-1","MD","MD+1","MD+2"]

                    rows_dias = []
                    for dia in dias_ordem:
                        vA = df_A[df_A["Dia MD"] == dia][met_dia_comp].mean()
                        vB = df_B[df_B["Dia MD"] == dia][met_dia_comp].mean()
                        if pd.isna(vA) and pd.isna(vB): continue
                        rows_dias.append({"Dia MD": dia, f"MC {int(mc_A)}": round(vA,1) if not pd.isna(vA) else 0,
                                           f"MC {int(mc_B)}": round(vB,1) if not pd.isna(vB) else 0})

                    if rows_dias:
                        df_dias_comp = pd.DataFrame(rows_dias)
                        fig_dias_comp = go.Figure()
                        fig_dias_comp.add_trace(go.Scatter(
                            x=df_dias_comp["Dia MD"], y=df_dias_comp[f"MC {int(mc_A)}"],
                            mode="lines+markers", name=f"MC {int(mc_A)}",
                            line_color="#e63946", line_width=3, marker_size=10,
                        ))
                        fig_dias_comp.add_trace(go.Scatter(
                            x=df_dias_comp["Dia MD"], y=df_dias_comp[f"MC {int(mc_B)}"],
                            mode="lines+markers", name=f"MC {int(mc_B)}",
                            line_color="#457b9d", line_width=3, marker_size=10,
                        ))
                        fig_dias_comp.update_layout(
                            height=360, yaxis_title=met_dia_comp,
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                            font_color="rgba(255,255,255,0.85)", margin=dict(t=20),
                        )
                        st.plotly_chart(fig_dias_comp, use_container_width=True)

            else:  # Nível Jogador
                jog_comp = st.selectbox("Jogador", sorted(df["Jogador"].dropna().unique()), key="comp_jog")
                df_A_jog = df_A[df_A["Jogador"] == jog_comp]
                df_B_jog = df_B[df_B["Jogador"] == jog_comp]

                st.markdown(f'<p class="section-title">📊 {jog_comp} — MC {int(mc_A)} vs MC {int(mc_B)}</p>', unsafe_allow_html=True)

                cols_j = st.columns(len(mets_comp_disp))
                for i, met in enumerate(mets_comp_disp):
                    vA = df_A_jog[met].mean()
                    vB = df_B_jog[met].mean()
                    if pd.isna(vA) and pd.isna(vB): continue
                    delta = ((vA - vB) / abs(vB) * 100) if (not pd.isna(vB) and vB != 0) else None
                    label = met.split("(")[0].strip()
                    cols_j[i].metric(
                        f"{label}",
                        f"{vA:,.1f}" if not pd.isna(vA) else "—",
                        delta=f"{delta:+.1f}% vs MC {int(mc_B)}" if delta else None,
                    )

                # Scatter comparativo jogador
                if len(mets_comp_disp) >= 2:
                    st.divider()
                    sc_j1, sc_j2 = st.columns(2)
                    x_cj = sc_j1.selectbox("Eixo X", mets_comp_disp, index=0, key="comp_jog_x")
                    y_cj = sc_j2.selectbox("Eixo Y", mets_comp_disp, index=1, key="comp_jog_y")

                    df_jog_todos = df[df["Jogador"] == jog_comp].dropna(subset=[x_cj, y_cj])
                    if not df_jog_todos.empty:
                        fig_ev_jog = go.Figure()
                        fig_ev_jog.add_trace(go.Scatter(
                            x=df_jog_todos[x_cj], y=df_jog_todos[y_cj],
                            mode="markers", name="Todas as sessões",
                            marker=dict(size=10, color="#457b9d", opacity=0.5),
                        ))
                        for mc_c, cor_c, nome_c in [(mc_A, "#e63946", f"MC {int(mc_A)}"), (mc_B, "#f39c12", f"MC {int(mc_B)}")]:
                            sub_mc = df_jog_todos[df_jog_todos["Microciclo (Nr)"] == mc_c]
                            if not sub_mc.empty:
                                fig_ev_jog.add_trace(go.Scatter(
                                    x=[sub_mc[x_cj].mean()], y=[sub_mc[y_cj].mean()],
                                    mode="markers+text", text=[nome_c],
                                    textposition="top center",
                                    marker=dict(size=22, color=cor_c, line=dict(width=2, color="white")),
                                    name=nome_c,
                                ))
                        fig_ev_jog.update_layout(
                            height=420, xaxis_title=x_cj, yaxis_title=y_cj,
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                            font_color="rgba(255,255,255,0.85)", margin=dict(t=20),
                        )
                        st.plotly_chart(fig_ev_jog, use_container_width=True)



        # ═══════════════════════════════════════════════════════════════════════════════
        # VISTA: PLANEADO VS REALIZADO
        # ═══════════════════════════════════════════════════════════════════════════════

    with tab_eq[2]:
            if AUTH_DISPONIVEL and not tem_acesso(_lm_user, "vmax"):
                st.warning("⚡ Esta funcionalidade é exclusiva do plano **Pro**.")
                st.markdown("Faz upgrade para aceder ao Vmáx Monitor, GPS, RHIE e muito mais.")

            # ── Calcular métricas de Vmáx a partir de BD_Carga ───────────────────────
            def calcular_vmax_monitor(df_base: pd.DataFrame):
                """Calcula perfil de Vmáx para todos os jogadores."""
                if "Vel. Máx (km/h)" not in df_base.columns or "Data" not in df_base.columns:
                    return pd.DataFrame()

                rows = []
                for jog in sorted(df_base["Jogador"].dropna().unique()):
                    sub = df_base[df_base["Jogador"] == jog].copy()
                    sub = sub.dropna(subset=["Data", "Vel. Máx (km/h)"])
                    if sub.empty:
                        continue

                    sub = sub.sort_values("Data")
                    vmax_record = sub["Vel. Máx (km/h)"].max()
                    posicao = sub["Posição"].iloc[-1] if "Posição" in sub.columns else "—"

                    # Limiar 90% do recorde
                    lim_90 = vmax_record * 0.90
                    lim_85 = vmax_record * 0.85
                    lim_95 = vmax_record * 0.95

                    # Última sessão com Vmáx ≥ 90% do recorde
                    sub_90 = sub[sub["Vel. Máx (km/h)"] >= lim_90]
                    if not sub_90.empty:
                        ultima_data_90 = sub_90["Data"].max()
                        dias_sem_90 = (sub["Data"].max() - ultima_data_90).days
                    else:
                        ultima_data_90 = pd.NaT
                        dias_sem_90 = 999

                    # Última sessão com Vmáx ≥ 95%
                    sub_95 = sub[sub["Vel. Máx (km/h)"] >= lim_95]
                    if not sub_95.empty:
                        ultima_data_95 = sub_95["Data"].max()
                        dias_sem_95 = (sub["Data"].max() - ultima_data_95).days
                    else:
                        ultima_data_95 = pd.NaT
                        dias_sem_95 = 999

                    # Total sessões ≥90%
                    total_sess_90 = len(sub_90)
                    total_sess = len(sub)
                    pct_sess_90 = total_sess_90 / total_sess if total_sess > 0 else 0

                    # Vmáx mais recente
                    vmax_ultima = sub.iloc[-1]["Vel. Máx (km/h)"]
                    pct_record = vmax_ultima / vmax_record if vmax_record > 0 else 0

                    # Alerta
                    if dias_sem_90 > 7:
                        alerta = "🔴 RISCO"
                        alerta_cor = "#e74c3c"
                    elif dias_sem_90 >= 5:
                        alerta = "🟡 ATENÇÃO"
                        alerta_cor = "#f39c12"
                    else:
                        alerta = "🟢 OK"
                        alerta_cor = "#2ecc71"

                    rows.append({
                        "Jogador": jog,
                        "Posição": posicao,
                        "Vmáx Record (km/h)": round(vmax_record, 1),
                        "Última Vmáx (km/h)": round(vmax_ultima, 1),
                        "% do Recorde": round(pct_record * 100, 1),
                        "Última Data ≥90%": ultima_data_90,
                        "Dias s/ ≥90% Vmáx": int(dias_sem_90) if dias_sem_90 < 999 else "Nunca",
                        "Última Data ≥95%": ultima_data_95,
                        "Dias s/ ≥95% Vmáx": int(dias_sem_95) if dias_sem_95 < 999 else "Nunca",
                        "Sessões ≥90%": total_sess_90,
                        "% Sessões ≥90%": round(pct_sess_90 * 100, 1),
                        "Alerta": alerta,
                        "_alerta_cor": alerta_cor,
                        "_lim_90": round(lim_90, 1),
                        "_lim_85": round(lim_85, 1),
                        "_lim_95": round(lim_95, 1),
                    })

                return pd.DataFrame(rows)

            df_vmax = calcular_vmax_monitor(df)

            if df_vmax.empty:
                st.warning("Dados de Vmáx não encontrados. Certifica-te que a folha BD_Carga tem a coluna 'Vel. Máx (km/h)'.")

            # ── SECÇÃO A — Perfil geral da equipa ────────────────────────────────────
            st.markdown('<p class="section-title">A — Perfil de Velocidade & Alerta de Inatividade</p>', unsafe_allow_html=True)

            # KPIs rápidos
            c1, c2, c3, c4 = st.columns(4)
            em_risco_v   = df_vmax[df_vmax["Alerta"] == "🔴 RISCO"]
            em_atencao_v = df_vmax[df_vmax["Alerta"] == "🟡 ATENÇÃO"]
            em_ok_v      = df_vmax[df_vmax["Alerta"] == "🟢 OK"]
            c1.metric("🔴 Em Risco (>7 dias s/ ≥90%)",    len(em_risco_v))
            c2.metric("🟡 Em Atenção (5–7 dias)",            len(em_atencao_v))
            c3.metric("🟢 OK (<7 dias)",                    len(em_ok_v))
            c4.metric("Vmáx Record da Equipa",              f"{df_vmax['Vmáx Record (km/h)'].max():.1f} km/h")

            st.divider()

            # Gráfico de barras — Vmáx Record vs Última Vmáx
            st.markdown('<p class="section-title">Vmáx Record vs Última Vmáx por Jogador</p>', unsafe_allow_html=True)

            df_vmax_sorted = df_vmax.sort_values("Vmáx Record (km/h)", ascending=True)

            fig_vmax_bars = go.Figure()
            fig_vmax_bars.add_trace(go.Bar(
                y=df_vmax_sorted["Jogador"],
                x=df_vmax_sorted["Vmáx Record (km/h)"],
                name="Vmáx Record",
                orientation="h",
                marker_color="#e63946",
                opacity=0.85,
            ))
            fig_vmax_bars.add_trace(go.Bar(
                y=df_vmax_sorted["Jogador"],
                x=df_vmax_sorted["Última Vmáx (km/h)"],
                name="Última Vmáx",
                orientation="h",
                marker_color="#457b9d",
                opacity=0.85,
            ))
            fig_vmax_bars.update_layout(
                barmode="overlay",
                height=max(320, len(df_vmax_sorted) * 42),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="rgba(255,255,255,0.85)",
                xaxis_title="km/h",
                legend=dict(orientation="h", y=1.05),
                margin=dict(t=30, b=10),
            )
            st.plotly_chart(fig_vmax_bars, use_container_width=True)

            # Gráfico de dias sem ≥90% Vmáx
            st.markdown('<p class="section-title">Dias sem Atingir ≥90% Vmáx Record</p>', unsafe_allow_html=True)

            df_dias = df_vmax.copy()
            df_dias["Dias_num"] = pd.to_numeric(df_dias["Dias s/ ≥90% Vmáx"], errors="coerce").fillna(999)
            df_dias = df_dias.sort_values("Dias_num", ascending=False)

            cores_dias = []
            for _, row in df_dias.iterrows():
                d = row["Dias_num"]
                if d > 7:    cores_dias.append("#e74c3c")
                elif d > 3:  cores_dias.append("#f39c12")
                else:        cores_dias.append("#2ecc71")

            fig_dias = go.Figure(go.Bar(
                x=df_dias["Jogador"],
                y=df_dias["Dias_num"],
                marker_color=cores_dias,
                text=[f"{int(d)}d" if d < 999 else "—" for d in df_dias["Dias_num"]],
                textposition="outside",
            ))
            fig_dias.add_hline(y=7, line_dash="dash", line_color="#e74c3c", annotation_text="Risco >7 dias")
            fig_dias.add_hline(y=5,  line_dash="dot",  line_color="#f39c12", annotation_text="Atenção ≥5 dias")
            fig_dias.update_layout(
                yaxis_title="Dias",
                height=360,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="rgba(255,255,255,0.85)",
                margin=dict(t=20, b=10),
            )
            st.plotly_chart(fig_dias, use_container_width=True)

            # % do Recorde — gauge style bar
            st.markdown('<p class="section-title">% do Recorde Pessoal (Última Sessão)</p>', unsafe_allow_html=True)

            df_pct = df_vmax.sort_values("% do Recorde", ascending=True)
            cores_pct = []
            for v in df_pct["% do Recorde"]:
                if v >= 95:   cores_pct.append("#2ecc71")
                elif v >= 90: cores_pct.append("#f39c12")
                else:         cores_pct.append("#e74c3c")

            fig_pct = go.Figure(go.Bar(
                y=df_pct["Jogador"],
                x=df_pct["% do Recorde"],
                orientation="h",
                marker_color=cores_pct,
                text=[f"{v:.1f}%" for v in df_pct["% do Recorde"]],
                textposition="outside",
            ))
            fig_pct.add_vline(x=95, line_dash="dash", line_color="#2ecc71", annotation_text="95%")
            fig_pct.add_vline(x=90, line_dash="dash", line_color="#f39c12", annotation_text="90%")
            fig_pct.update_layout(
                xaxis=dict(title="% do Recorde", range=[70, 105]),
                height=max(300, len(df_pct) * 40),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="rgba(255,255,255,0.85)",
                margin=dict(t=10, b=10),
            )
            st.plotly_chart(fig_pct, use_container_width=True)

            # Tabela resumo Secção A
            st.markdown('<p class="section-title">Tabela Resumo — Todos os Jogadores</p>', unsafe_allow_html=True)
            cols_tabela = ["Jogador", "Posição", "Vmáx Record (km/h)", "Última Vmáx (km/h)",
                           "% do Recorde", "Dias s/ ≥90% Vmáx", "Dias s/ ≥95% Vmáx",
                           "Sessões ≥90%", "% Sessões ≥90%", "Alerta"]
            st.dataframe(df_vmax[cols_tabela].set_index("Jogador"), use_container_width=True)

            # Scatter Vmáx Record vs Dias sem ≥90%
            st.divider()
            st.markdown('<p class="section-title">🎯 Scatter — Vmáx Record vs Dias sem ≥90%</p>', unsafe_allow_html=True)
            st.caption("Canto superior esquerdo = jogadores rápidos sem exposição recente → máximo risco")

            df_sc_vmax = df_vmax.copy()
            df_sc_vmax["Dias_num"] = pd.to_numeric(df_sc_vmax["Dias s/ ≥90% Vmáx"], errors="coerce").fillna(0)

            if not df_sc_vmax.empty:
                fig_sc_vmax = go.Figure()
                for _, row in df_sc_vmax.iterrows():
                    d = row["Dias_num"]
                    v = row["Vmáx Record (km/h)"]
                    if d > 7:    cor_v = "#e74c3c"
                    elif d > 3:  cor_v = "#f39c12"
                    else:        cor_v = "#2ecc71"
                    fig_sc_vmax.add_trace(go.Scatter(
                        x=[v], y=[d],
                        mode="markers+text",
                        text=[row["Jogador"].split()[0] if isinstance(row["Jogador"], str) else row["Jogador"]],
                        textposition="top center",
                        textfont=dict(size=10, color="white"),
                        marker=dict(size=28, color=cor_v, opacity=0.85, line=dict(width=2, color="white")),
                        hovertext=f'<b>{row["Jogador"]}</b><br>Vmáx Record: {v:.1f} km/h<br>Dias s/ ≥90%: {int(d)}',
                        hoverinfo="text",
                        showlegend=False,
                    ))
                fig_sc_vmax.add_hline(y=7, line_dash="dash", line_color="#e74c3c", annotation_text="Risco >7 dias")
                fig_sc_vmax.add_hline(y=5,  line_dash="dot",  line_color="#f39c12", annotation_text="Atenção ≥5 dias")
                fig_sc_vmax.update_layout(
                    xaxis_title="Vmáx Record (km/h)", yaxis_title="Dias sem ≥90% Vmáx",
                    height=460, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)", showlegend=False, margin=dict(t=20),
                    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                )
                st.plotly_chart(fig_sc_vmax, use_container_width=True)

            st.divider()

            # ── SECÇÃO B — Histórico individual ──────────────────────────────────────
            st.markdown('<p class="section-title">B — Histórico de Velocidade Individual</p>', unsafe_allow_html=True)

            jog_vmax = st.selectbox("Seleciona o Jogador", sorted(df["Jogador"].dropna().unique()), key="vmax_jog")

            sub_hist = df[df["Jogador"] == jog_vmax].dropna(subset=["Data", "Vel. Máx (km/h)"]).sort_values("Data")

            if not sub_hist.empty:
                vmax_rec = sub_hist["Vel. Máx (km/h)"].max()
                lim_90 = vmax_rec * 0.90
                lim_85 = vmax_rec * 0.85
                lim_95 = vmax_rec * 0.95

                # % do recorde por sessão
                sub_hist = sub_hist.copy()
                sub_hist["% Record"] = (sub_hist["Vel. Máx (km/h)"] / vmax_rec * 100).round(1)

                # KPIs do jogador
                info_jog = df_vmax[df_vmax["Jogador"] == jog_vmax]
                if not info_jog.empty:
                    r = info_jog.iloc[0]
                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("Vmáx Record", f"{r['Vmáx Record (km/h)']} km/h")
                    k2.metric("Limiar 90%",  f"{r['_lim_90']} km/h")
                    k3.metric("Limiar 95%",  f"{r['_lim_95']} km/h")
                    k4.metric("Alerta",      r["Alerta"])

                # Gráfico histórico Vmáx
                fig_hist = go.Figure()
                fig_hist.add_trace(go.Scatter(
                    x=sub_hist["Data"], y=sub_hist["Vel. Máx (km/h)"],
                    mode="lines+markers", name="Vmáx Sessão",
                    line_color="#e63946", line_width=2, marker_size=7,
                ))
                fig_hist.add_hline(y=vmax_rec, line_dash="solid",  line_color="#f39c12", line_width=2,
                                    annotation_text=f"Recorde {vmax_rec:.1f} km/h", annotation_position="top left")
                fig_hist.add_hline(y=lim_95,   line_dash="dash",   line_color="#2ecc71",
                                    annotation_text=f"≥95% ({lim_95:.1f})", annotation_position="bottom right")
                fig_hist.add_hline(y=lim_90,   line_dash="dash",   line_color="#f39c12",
                                    annotation_text=f"≥90% ({lim_90:.1f})", annotation_position="bottom right")
                fig_hist.add_hline(y=lim_85,   line_dash="dot",    line_color="#3498db",
                                    annotation_text=f"≥85% ({lim_85:.1f})", annotation_position="bottom right")

                # Colorir pontos por zona
                cores_pts = []
                for v in sub_hist["Vel. Máx (km/h)"]:
                    if v >= lim_95:   cores_pts.append("#2ecc71")
                    elif v >= lim_90: cores_pts.append("#f39c12")
                    elif v >= lim_85: cores_pts.append("#3498db")
                    else:             cores_pts.append("#e74c3c")
                fig_hist.update_traces(marker_color=cores_pts, selector=dict(name="Vmáx Sessão"))

                fig_hist.update_layout(
                    height=400,
                    yaxis_title="Vel. Máx (km/h)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)",
                    showlegend=False,
                    margin=dict(t=20),
                )
                st.plotly_chart(fig_hist, use_container_width=True)

                # Gráfico % do Recorde ao longo do tempo
                st.markdown('<p class="section-title">% do Recorde por Sessão</p>', unsafe_allow_html=True)
                fig_pct_hist = go.Figure()
                fig_pct_hist.add_trace(go.Bar(
                    x=sub_hist["Data"], y=sub_hist["% Record"],
                    marker_color=[
                        "#2ecc71" if v >= 95 else "#f39c12" if v >= 90 else "#3498db" if v >= 85 else "#e74c3c"
                        for v in sub_hist["% Record"]
                    ],
                    text=sub_hist["% Record"].astype(str) + "%",
                    textposition="outside",
                ))
                fig_pct_hist.add_hline(y=95, line_dash="dash", line_color="#2ecc71", annotation_text="95%")
                fig_pct_hist.add_hline(y=90, line_dash="dash", line_color="#f39c12", annotation_text="90%")
                fig_pct_hist.update_layout(
                    yaxis=dict(title="% do Recorde", range=[60, 108]),
                    height=320,
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)",
                    margin=dict(t=10),
                )
                st.plotly_chart(fig_pct_hist, use_container_width=True)

                # Exposição por zonas — Nº sprints ≥85/90/95%
                cols_sprints = ["Nº ≥85% Vmáx", "Nº ≥90% Vmáx", "Nº ≥95% Vmáx"]
                cols_sprints_disp = [c for c in cols_sprints if c in sub_hist.columns]
                if cols_sprints_disp:
                    st.markdown('<p class="section-title">Nº de Ações por Zona de Velocidade</p>', unsafe_allow_html=True)
                    fig_sprints = px.line(sub_hist, x="Data", y=cols_sprints_disp,
                                           markers=True,
                                           color_discrete_map={
                                               "Nº ≥85% Vmáx": "#3498db",
                                               "Nº ≥90% Vmáx": "#f39c12",
                                               "Nº ≥95% Vmáx": "#e74c3c",
                                           })
                    fig_sprints.update_layout(
                        height=300,
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color="rgba(255,255,255,0.85)",
                        legend_title="Zona",
                        margin=dict(t=10),
                    )
                    st.plotly_chart(fig_sprints, use_container_width=True)

                # Tabela de dados brutos
                with st.expander("📋 Ver histórico completo de Vmáx"):
                    colunas_hist = ["Data", "Microciclo (Nr)", "Dia MD", "Vel. Máx (km/h)", "% Record"] + cols_sprints_disp
                    colunas_hist_disp = [c for c in colunas_hist if c in sub_hist.columns]
                    st.dataframe(sub_hist[colunas_hist_disp].sort_values("Data", ascending=False), use_container_width=True)

            # ── Conclusões Vmáx ───────────────────────────────────────────────────────
            st.divider()
            st.markdown('<p class="section-title">🧠 Conclusões — Vmáx Monitor</p>', unsafe_allow_html=True)

            if not df_vmax.empty:
                criticos = df_vmax[pd.to_numeric(df_vmax["Dias s/ ≥90% Vmáx"], errors="coerce") > 7]["Jogador"].tolist()
                atencao_v = df_vmax[pd.to_numeric(df_vmax["Dias s/ ≥90% Vmáx"], errors="coerce").between(4, 7)]["Jogador"].tolist()
                baixo_pct = df_vmax[df_vmax["% do Recorde"] < 90]["Jogador"].tolist()

                if criticos:
                    st.markdown(f"🔴 **Risco de desadaptação neural** — {', '.join(criticos)}: mais de 7 dias sem atingir ≥90% do recorde. Expor a estímulos de alta velocidade com urgência.")
                if atencao_v:
                    st.markdown(f"🟡 **Monitorizar** — {', '.join(atencao_v)}: entre 4-7 dias sem ≥90% Vmáx.")
                if baixo_pct:
                    st.markdown(f"📉 **Abaixo de 90% do recorde** na última sessão — {', '.join(baixo_pct)}. Verificar se é recuperação intencional ou sinal de fadiga.")
                if not criticos and not atencao_v:
                    st.markdown("🟢 **Toda a equipa em dia** com exposição a alta velocidade (<7 dias).")

                melhor = df_vmax.loc[df_vmax["Vmáx Record (km/h)"].idxmax()]
                st.markdown(f"⚡ **Jogador mais rápido**: {melhor['Jogador']} com recorde de **{melhor['Vmáx Record (km/h)']} km/h**.")



        # ═══════════════════════════════════════════════════════════════════════════════
        # VISTA: Z-SCORE
        # ═══════════════════════════════════════════════════════════════════════════════

    with st.expander("⚡ Monotonia & Strain (Foster)", expanded=False):
        st.info("**Foster (1998):** Monotonia = CI média/DP. Strain = CI total × Monotonia. Monotonia>2.0 = variação insuficiente. Strain elevado + Monotonia alta = risco aumentado.")
        df_f = df_f_dia
        st.markdown("""
        > **Monotonia** mede se o treino é sempre igual — treinos muito repetitivos são prejudiciais mesmo com carga baixa.  
        > **Strain** combina a carga total com a monotonia — semanas intensas *e* monótonas são as mais arriscadas.
        """)

        LIMIAR_MONO = 2.0
        LIMIAR_MONO_ATENCAO = 1.5

        def calcular_mono_strain(df_base: pd.DataFrame):
            rows = []
            for jog in sorted(df_base["Jogador"].dropna().unique()):
                sub = df_base[df_base["Jogador"] == jog].dropna(subset=["Microciclo (Nr)", "Carga Interna"])
                for mc in sub["Microciclo (Nr)"].unique():
                    mc_sub = sub[sub["Microciclo (Nr)"] == mc]["Carga Interna"]
                    if len(mc_sub) < 2: continue
                    media = mc_sub.mean()
                    dp    = mc_sub.std()
                    total = mc_sub.sum()
                    mono  = media / dp if dp > 0 else 0
                    strain = total * mono
                    pos = df_base[df_base["Jogador"] == jog]["Posição"].iloc[-1] if "Posição" in df_base.columns else "—"

                    if mono > LIMIAR_MONO:         estado_m, cor_m = "🔴 Excessiva",   "#e74c3c"
                    elif mono > LIMIAR_MONO_ATENCAO: estado_m, cor_m = "🟡 Atenção",    "#f39c12"
                    else:                            estado_m, cor_m = "🟢 Boa variação","#2ecc71"

                    rows.append({
                        "Jogador": jog, "Posição": pos, "Microciclo": int(mc),
                        "Carga Total": round(total, 0),
                        "Média Diária": round(media, 1),
                        "DP": round(dp, 1),
                        "Monotonia": round(mono, 2),
                        "Strain": round(strain, 0),
                        "Estado": estado_m,
                        "_cor": cor_m,
                    })
            return pd.DataFrame(rows)

        df_ms = calcular_mono_strain(df_f)

        if df_ms.empty:
            st.warning("Dados insuficientes para calcular Monotonia & Strain. Necessário pelo menos 2 sessões por microciclo.")

        tab_ms1, tab_ms2 = st.tabs(["🏟️ Vista de Equipa", "👤 Jogador Individual"])

        with tab_ms1:
            mc_ms = st.selectbox("Microciclo", sorted(df_ms["Microciclo"].unique(), reverse=True), key="ms_mc")
            df_ms_mc = df_ms[df_ms["Microciclo"] == mc_ms]

            # KPIs
            k1,k2,k3 = st.columns(3)
            k1.metric("Monotonia Média", f"{df_ms_mc['Monotonia'].mean():.2f}",
                      help="Ideal: <1.5 | Atenção: 1.5–2.0 | Excessivo: >2.0")
            k2.metric("Strain Médio",    f"{df_ms_mc['Strain'].mean():,.0f}",
                      help="Carga Total × Monotonia. Quanto maior, maior o risco acumulado.")
            k3.metric("Jogadores em risco de monotonia", f"{len(df_ms_mc[df_ms_mc['Monotonia'] > LIMIAR_MONO])}")

            st.divider()

            # Monotonia por jogador
            st.markdown('<p class="section-title">Monotonia por Jogador</p>', unsafe_allow_html=True)
            df_ms_sorted = df_ms_mc.sort_values("Monotonia", ascending=False)
            fig_mono = go.Figure(go.Bar(
                x=df_ms_sorted["Jogador"], y=df_ms_sorted["Monotonia"],
                marker_color=df_ms_sorted["_cor"].tolist(),
                text=df_ms_sorted["Monotonia"].round(2), textposition="outside",
            ))
            fig_mono.add_hline(y=LIMIAR_MONO,        line_dash="dash", line_color="#e74c3c",  annotation_text="Excessiva (2.0)")
            fig_mono.add_hline(y=LIMIAR_MONO_ATENCAO, line_dash="dot",  line_color="#f39c12", annotation_text="Atenção (1.5)")
            fig_mono.update_layout(
                yaxis_title="Monotonia", height=380,
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="rgba(255,255,255,0.85)", showlegend=False, margin=dict(t=20),
            )
            st.plotly_chart(fig_mono, use_container_width=True)

            # Scatter Strain vs Carga Total
            st.markdown('<p class="section-title">Strain vs Carga Total — Quadrantes de Risco</p>', unsafe_allow_html=True)
            st.caption("Ideal: carga alta com baixa monotonia (quadrante inferior direito)")

            if len(df_ms_mc) >= 2 and df_ms_mc["Carga Total"].nunique() > 1:
                fig_scatter = px.scatter(
                    df_ms_mc, x="Carga Total", y="Monotonia",
                    text="Jogador", color="Estado",
                    color_discrete_map={"🔴 Excessiva": "#e74c3c", "🟡 Atenção": "#f39c12", "🟢 Boa variação": "#2ecc71"},
                    size="Strain", size_max=40,
                    hover_data=["Strain", "Média Diária", "DP"],
                )
            else:
                fig_scatter = px.scatter(
                    df_ms_mc, x="Carga Total", y="Monotonia",
                    text="Jogador", color="Estado",
                    color_discrete_map={"🔴 Excessiva": "#e74c3c", "🟡 Atenção": "#f39c12", "🟢 Boa variação": "#2ecc71"},
                )
            fig_scatter.add_hline(y=LIMIAR_MONO,         line_dash="dash", line_color="#e74c3c")
            fig_scatter.add_hline(y=LIMIAR_MONO_ATENCAO,  line_dash="dot",  line_color="#f39c12")
            fig_scatter.update_traces(textposition="top center")
            fig_scatter.update_layout(
                height=420, plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)", margin=dict(t=20),
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

            # Tabela
            st.dataframe(
                df_ms_mc[["Jogador","Posição","Carga Total","Média Diária","DP","Monotonia","Strain","Estado"]]
                .set_index("Jogador"), use_container_width=True
            )

            # Conclusões
            st.divider()
            st.markdown('<p class="section-title">🧠 Conclusões Automáticas</p>', unsafe_allow_html=True)
            risco_mono  = df_ms_mc[df_ms_mc["Monotonia"] > LIMIAR_MONO]["Jogador"].tolist()
            atenc_mono  = df_ms_mc[df_ms_mc["Monotonia"].between(LIMIAR_MONO_ATENCAO, LIMIAR_MONO)]["Jogador"].tolist()
            strain_top  = df_ms_mc.nlargest(3, "Strain")[["Jogador","Strain"]].values.tolist()

            if risco_mono:
                st.markdown(f"🔴 **Monotonia excessiva** (>2.0): {', '.join(risco_mono)} — variar a estrutura das sessões com urgência (intensidade, volume, tipo de exercício).")
            if atenc_mono:
                st.markdown(f"🟡 **Atenção à monotonia** (1.5–2.0): {', '.join(atenc_mono)} — introduzir mais variação nos próximos dias.")
            if not risco_mono and not atenc_mono:
                st.markdown("🟢 **Toda a equipa com boa variação de carga** neste microciclo.")
            st.markdown("**Top 3 Strain** neste microciclo:")
            for jog_s, strain_s in strain_top:
                st.markdown(f"  ▸ **{jog_s}**: {strain_s:,.0f} UA")

        with tab_ms2:
            jog_ms = st.selectbox("Jogador", sorted(df_ms["Jogador"].unique()), key="ms_jog")
            df_ms_jog = df_ms[df_ms["Jogador"] == jog_ms].sort_values("Microciclo")

            fig_ms_ev = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                       subplot_titles=["Monotonia", "Strain"],
                                       vertical_spacing=0.12)
            fig_ms_ev.add_trace(go.Scatter(
                x=df_ms_jog["Microciclo"].astype(str), y=df_ms_jog["Monotonia"],
                mode="lines+markers+text", text=df_ms_jog["Monotonia"].round(2),
                textposition="top center", line_color="#e63946", name="Monotonia",
            ), row=1, col=1)
            fig_ms_ev.add_trace(go.Bar(
                x=df_ms_jog["Microciclo"].astype(str), y=df_ms_jog["Strain"],
                marker_color="#457b9d", name="Strain",
            ), row=2, col=1)
            fig_ms_ev.add_hline(y=LIMIAR_MONO,         line_dash="dash", line_color="#e74c3c",  row=1, col=1)
            fig_ms_ev.add_hline(y=LIMIAR_MONO_ATENCAO,  line_dash="dot",  line_color="#f39c12", row=1, col=1)
            fig_ms_ev.update_layout(
                height=480, plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                showlegend=False, margin=dict(t=30),
                xaxis2_title="Microciclo",
            )
            st.plotly_chart(fig_ms_ev, use_container_width=True)

            # Detalhe das sessões do microciclo selecionado
            mc_ms_jog = st.selectbox("Ver detalhe do Microciclo", sorted(df_ms_jog["Microciclo"].unique(), reverse=True), key="ms_jog_mc")
            sessoes_mc = df_f[(df_f["Jogador"] == jog_ms) & (df_f["Microciclo (Nr)"] == mc_ms_jog) & (df_f["Carga Interna"].notna())]
            if not sessoes_mc.empty:
                fig_sess = go.Figure(go.Bar(
                    x=sessoes_mc["Dia MD"] if "Dia MD" in sessoes_mc.columns else sessoes_mc["Data"].dt.strftime("%d/%m"),
                    y=sessoes_mc["Carga Interna"],
                    marker_color="#e63946",
                    text=sessoes_mc["Carga Interna"].round(0), textposition="outside",
                ))
                fig_sess.add_hline(
                    y=sessoes_mc["Carga Interna"].mean(),
                    line_dash="dash", line_color="white",
                    annotation_text=f"Média: {sessoes_mc['Carga Interna'].mean():.0f}",
                )
                fig_sess.update_layout(
                    yaxis_title="Carga Interna (UA)", height=300,
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)", margin=dict(t=10),
                )
                st.plotly_chart(fig_sess, use_container_width=True)


        # ═══════════════════════════════════════════════════════════════════════════════
        # VISTA: LOG DE ALERTAS
        # ═══════════════════════════════════════════════════════════════════════════════

elif seccao == "jogadores":
    lm_header("Jogadores", "Análise individual — perfil, historial e performance por jogador", "Jogadores")
    tab_jog = st.tabs(["👤 Individual", "📏 Perfil de Referência"])

    with tab_jog[0]:
            df_f = df_f_dia

            df_jog = df[df["Jogador"] == jogador_sel].sort_values("Data")
            df_jog_f = df_f[df_f["Jogador"] == jogador_sel].sort_values("Data")

            if df_jog_f.empty:
                st.warning("Sem dados para este jogador nos filtros selecionados.")

            # KPIs
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Sessões",          f"{len(df_jog_f)}")
            c2.metric("Dist. Média (m)",  f"{df_jog_f['Distância Total (m)'].mean():,.0f}")
            c3.metric("PSE Média",        f"{df_jog_f['PSE Sessão'].mean():.1f}")
            c4.metric("CI Médio",         f"{df_jog_f['Carga Interna'].mean():,.0f}")

            st.divider()

            # ACWR ao longo do tempo
            st.markdown('<p class="section-title">📉 ACWR ao Longo do Tempo</p>', unsafe_allow_html=True)
            df_acwr_jog = calcular_acwr(df_jog, jogador_sel)
            if "ACWR" in df_acwr_jog.columns:
                fig_acwr_t = go.Figure()
                fig_acwr_t.add_trace(go.Scatter(x=df_acwr_jog["Data"], y=df_acwr_jog["ACWR"],
                                                 mode="lines+markers", name="ACWR", line_color="#e63946"))
                fig_acwr_t.add_hrect(y0=0.8, y1=1.3, fillcolor="green",   opacity=0.08, line_width=0)
                fig_acwr_t.add_hrect(y0=1.3, y1=1.5, fillcolor="orange",  opacity=0.1,  line_width=0)
                fig_acwr_t.add_hrect(y0=1.5, y1=3.0, fillcolor="red",     opacity=0.1,  line_width=0)
                fig_acwr_t.add_hline(y=1.5, line_dash="dash", line_color="#e74c3c", annotation_text="1.5")
                fig_acwr_t.add_hline(y=0.8, line_dash="dash", line_color="#3498db", annotation_text="0.8")
                fig_acwr_t.update_layout(height=320, plot_bgcolor="rgba(0,0,0,0)",
                                           paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                                           yaxis_title="ACWR", margin=dict(t=10))
                st.plotly_chart(fig_acwr_t, use_container_width=True)

            # Carga Interna por sessão
            st.divider()
            st.markdown('<p class="section-title">⚡ Carga Interna por Sessão</p>', unsafe_allow_html=True)
            fig_ci_j = px.bar(df_jog_f, x="Data", y="Carga Interna",
                               color="Dia MD" if "Dia MD" in df_jog_f.columns else None,
                               labels={"Carga Interna": "CI", "Data": "Data"})
            fig_ci_j.update_layout(height=300, plot_bgcolor="rgba(0,0,0,0)",
                                     paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)", margin=dict(t=10))
            st.plotly_chart(fig_ci_j, use_container_width=True)

            # GPS ao longo do tempo
            st.divider()
            st.markdown('<p class="section-title">🏃 Evolução GPS</p>', unsafe_allow_html=True)
            metricas_gps = get_mets_gps(df_jog)
            metricas_gps_disp = [m for m in metricas_gps if m in df_jog_f.columns]

            fig_gps_j = make_subplots(rows=2, cols=2,
                                       subplot_titles=metricas_gps_disp,
                                       vertical_spacing=0.18, horizontal_spacing=0.1)
            posicoes_grid = [(1,1),(1,2),(2,1),(2,2)]
            cores_gps = ["#e63946","#457b9d","#2ecc71","#f39c12"]

            for i, met in enumerate(metricas_gps_disp[:4]):
                r, c = posicoes_grid[i]
                fig_gps_j.add_trace(
                    go.Scatter(x=df_jog_f["Data"], y=df_jog_f[met],
                               mode="lines+markers", name=met,
                               line_color=cores_gps[i], showlegend=False),
                    row=r, col=c
                )

            fig_gps_j.update_layout(height=460, plot_bgcolor="rgba(0,0,0,0)",
                                      paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)", margin=dict(t=30))
            st.plotly_chart(fig_gps_j, use_container_width=True)

            # Wellness
            st.divider()
            st.markdown('<p class="section-title">💤 Wellness (Hooper Index)</p>', unsafe_allow_html=True)
            w_cols = ["Sono (1-5)", "Dor Musc. (1-5)", "Stress (1-5)", "Humor (1-5)", "Hooper Index"]
            w_disp = [c for c in w_cols if c in df_jog_f.columns]
            if w_disp:
                fig_w_j = px.line(df_jog_f, x="Data", y=w_disp, markers=True)
                fig_w_j.update_layout(height=320, plot_bgcolor="rgba(0,0,0,0)",
                                       paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                                       legend_title="", margin=dict(t=10))
                st.plotly_chart(fig_w_j, use_container_width=True)

            # Tabela de dados brutos
            st.divider()
            with st.expander("📋 Ver todos os registos"):
                st.dataframe(df_jog_f.sort_values("Data", ascending=False), use_container_width=True)

            # Conclusões individuais
            st.divider()
            st.markdown('<p class="section-title">🧠 Conclusões</p>', unsafe_allow_html=True)

            df_acwr_all = calcular_acwr(df_jog, jogador_sel)
            if "ACWR" in df_acwr_all.columns and df_acwr_all["ACWR"].notna().any():
                acwr_last = df_acwr_all.dropna(subset=["ACWR"]).iloc[-1]["ACWR"]
                estado = cor_acwr(acwr_last)
                st.markdown(f"- **Último ACWR**: `{acwr_last:.2f}` → {estado}")

            if "Hooper Index" in df_jog_f.columns:
                h = df_jog_f["Hooper Index"].mean()
                if h >= 14:
                    st.markdown(f"- 😟 **Hooper Index elevado** ({h:.1f}) — possível acumulação de stress/fadiga.")
                elif h <= 8:
                    st.markdown(f"- 😃 **Hooper Index excelente** ({h:.1f}) — jogador em ótimo estado.")
                else:
                    st.markdown(f"- 😐 **Hooper Index normal** ({h:.1f}).")

            if "Vel. Máx (km/h)" in df_jog_f.columns:
                vmax = df_jog_f["Vel. Máx (km/h)"].max()
                vmax_mean = df_jog_f["Vel. Máx (km/h)"].mean()
                st.markdown(f"- **Velocidade máxima registada**: {vmax:.1f} km/h (média: {vmax_mean:.1f} km/h).")

            # ── Conclusões automáticas ────────────────────────────────────────────────
            st.divider()
            st.markdown('<p class="section-title">🧠 Análise Automática</p>', unsafe_allow_html=True)

            conclusoes_jog = []

            # ACWR
            df_acwr_jog = calcular_acwr(df, jogador_sel)
            if not df_acwr_jog.empty and "ACWR" in df_acwr_jog.columns and df_acwr_jog["ACWR"].notna().any():
                av = df_acwr_jog["ACWR"].dropna().iloc[-1]
                if av > 1.5:    conclusoes_jog.append(("#e74c3c", f"🔴 ACWR elevado ({av:.2f}) — carga aguda muito superior à crónica. Reduzir volume e intensidade nos próximos treinos."))
                elif av > 1.3:  conclusoes_jog.append(("#f39c12", f"🟡 ACWR em zona de atenção ({av:.2f}) — monitorizar nas próximas 48h."))
                elif av < 0.8:  conclusoes_jog.append(("#3498db", f"🔵 ACWR baixo ({av:.2f}) — sub-estimulação crónica. Considerar aumentar a carga progressivamente."))
                else:            conclusoes_jog.append(("#2ecc71", f"🟢 ACWR dentro da zona segura ({av:.2f}) — continuar o plano atual."))

            # Hooper Index
            if "Hooper Index" in df_jog_f.columns and df_jog_f["Hooper Index"].notna().any():
                hi = df_jog_f["Hooper Index"].dropna()
                hi_last = hi.iloc[-1]; hi_media = hi.mean()
                trend = "a melhorar ↓" if hi.diff().mean() < -0.5 else "a piorar ↑" if hi.diff().mean() > 0.5 else "estável"
                if hi_last >= 14:   conclusoes_jog.append(("#e74c3c", f"🔴 Hooper elevado ({hi_last:.0f}/16) — má recuperação. Avaliar contexto extra-desportivo."))
                elif hi_last >= 10: conclusoes_jog.append(("#f39c12", f"🟡 Hooper moderado ({hi_last:.0f}/16) — tendência {trend}. Média histórica: {hi_media:.1f}."))
                else:                conclusoes_jog.append(("#2ecc71", f"🟢 Hooper baixo ({hi_last:.0f}/16) — boa recuperação. Média histórica: {hi_media:.1f}."))

            # Carga Interna vs histórico
            if "Carga Interna" in df_jog_f.columns and df_jog_f["Carga Interna"].notna().any():
                ci_h = df_jog_f["Carga Interna"].dropna()
                if len(ci_h) >= 3:
                    ci_last = ci_h.iloc[-1]; ci_med = ci_h.mean()
                    diff_p = (ci_last - ci_med) / ci_med * 100 if ci_med > 0 else 0
                    conclusoes_jog.append(("#9b59b6", f"📊 Última sessão: {ci_last:.0f} UA ({diff_p:+.0f}% vs média histórica de {ci_med:.0f} UA)."))

            # Vmáx exposição
            if "Vel. Máx (km/h)" in df_jog_f.columns and df_jog_f["Vel. Máx (km/h)"].notna().any():
                vmax_rec = df_jog_f["Vel. Máx (km/h)"].max()
                vmax_90 = vmax_rec * 0.90
                acima_90 = df_jog_f[df_jog_f["Vel. Máx (km/h)"] >= vmax_90].sort_values("Data")
                if acima_90.empty:
                    conclusoes_jog.append(("#e74c3c", f"🔴 Sem registo de exposição a ≥90% Vmáx (recorde: {vmax_rec:.1f} km/h). Incluir exercícios de sprint."))
                else:
                    dias_v = int((df_jog_f["Data"].max() - acima_90["Data"].max()).days) if "Data" in df_jog_f.columns else 0
                    if dias_v > 7:    conclusoes_jog.append(("#e74c3c", f"🔴 Sem sprint ≥90% Vmáx há {dias_v} dias. Recorde: {vmax_rec:.1f} km/h."))
                    elif dias_v >= 5: conclusoes_jog.append(("#f39c12", f"🟡 Última exposição a alta velocidade há {dias_v} dias."))
                    else:              conclusoes_jog.append(("#2ecc71", f"🟢 Exposição recente a alta velocidade (≥{vmax_90:.1f} km/h há {dias_v} dias)."))

            if not conclusoes_jog:
                st.info("Sem dados suficientes para análise automática.")
            else:
                for cor_c, texto in conclusoes_jog:
                    st.markdown(
                        f'<div style="border-left:3px solid {cor_c};padding:10px 16px;margin:4px 0;'
                        f'background:{cor_c}15;border-radius:0 8px 8px 0;font-size:0.85rem;line-height:1.5">{texto}</div>',
                        unsafe_allow_html=True
                    )

            # ═══════════════════════════════════════════════════════════════════════════════
            # VISTA: COMPARAÇÃO POR POSIÇÃO
            # ═══════════════════════════════════════════════════════════════════════════════

    with tab_jog[1]:

            METS_PERFIL = [
                "Distância Total (m)", "HSR (m)", "Sprint (m)", "Vel. Máx (km/h)",
                "Acc (n)", "Dcc (n)", "PSE Sessão", "Carga Interna",
                "Hooper Index", "Sono (1-5)", "Dor Musc. (1-5)", "Stress (1-5)", "Humor (1-5)",
            ]
            mets_disp = [m for m in METS_PERFIL if m in df.columns]

            tab_p1, tab_p2 = st.tabs(["👤 Análise Individual", "🏟️ Semáforo da Equipa"])

            # ── TAB 1: Individual ────────────────────────────────────────────────────
            with tab_p1:
                col_a, col_b = st.columns(2)
                jog_p = col_a.selectbox("Jogador", sorted(df["Jogador"].dropna().unique()), key="perf_jog")
                n_semanas = col_b.slider("Semanas de histórico como referência", 4, 20, 8, key="perf_sem")

                df_jog_p = df[df["Jogador"] == jog_p].dropna(subset=["Data"]).sort_values("Data").copy()
                if df_jog_p.empty:
                    st.warning("Sem dados para este jogador.")
    
                # Referência = primeiras n_semanas × 7 dias de dados
                data_corte = df_jog_p["Data"].min() + pd.Timedelta(weeks=n_semanas)
                df_ref  = df_jog_p[df_jog_p["Data"] <= data_corte]
                df_recente = df_jog_p[df_jog_p["Data"] > data_corte]

                if df_ref.empty or df_recente.empty:
                    st.warning("Histórico insuficiente. Tenta reduzir o número de semanas de referência.")
                else:
                    st.info(f"📐 Referência baseada em **{len(df_ref)} sessões** ({df_ref['Data'].min().strftime('%d/%m/%y')} – {df_ref['Data'].max().strftime('%d/%m/%y')})")

                    # Calcular perfil de referência
                    perfil_rows = []
                    for met in mets_disp:
                        if df_ref[met].notna().sum() < 3:
                            continue
                        mu  = df_ref[met].mean()
                        sig = df_ref[met].std()
                        ult = df_recente[met].dropna()
                        if ult.empty: continue
                        ult_val = ult.iloc[-1]
                        z = (ult_val - mu) / sig if sig > 0 else 0
                        if z > 2:    estado = "🔴 Muito Acima"; cor = "#e74c3c"
                        elif z > 1:  estado = "🟡 Acima";       cor = "#f39c12"
                        elif z >= -1: estado = "🟢 Normal";      cor = "#2ecc71"
                        elif z >= -2: estado = "🔵 Abaixo";      cor = "#3498db"
                        else:         estado = "🟣 Muito Abaixo"; cor = "#9b59b6"
                        perfil_rows.append({
                            "Métrica": met,
                            "Ref. Média": round(mu, 1),
                            "Ref. ±DP": round(sig, 1),
                            "Último Valor": round(ult_val, 1),
                            "Z-Score": round(z, 2),
                            "Estado": estado,
                            "_cor": cor,
                        })

                    if perfil_rows:
                        df_perf = pd.DataFrame(perfil_rows)

                        # Cards de semáforo
                        st.markdown('<p class="section-title">Semáforo — Última Sessão vs Perfil Pessoal</p>', unsafe_allow_html=True)
                        n_cols = 4
                        cols_p = st.columns(n_cols)
                        for i, row in df_perf.iterrows():
                            cols_p[i % n_cols].markdown(
                                f'<div style="background:{row["_cor"]}22;border:2px solid {row["_cor"]};border-radius:10px;'
                                f'padding:10px;text-align:center;margin:4px">'
                                f'<div style="font-size:0.75rem;font-weight:700;color:#ccc">{row["Métrica"]}</div>'
                                f'<div style="font-size:1.4rem;font-weight:900;color:{row["_cor"]}">{row["Último Valor"]}</div>'
                                f'<div style="font-size:0.7rem;color:#aaa">Ref: {row["Ref. Média"]} ± {row["Ref. ±DP"]}</div>'
                                f'<div style="font-size:0.85rem;color:{row["_cor"]}">{row["Estado"]} (z={row["Z-Score"]})</div>'
                                f'</div>',
                                unsafe_allow_html=True
                            )

                        st.divider()

                        # Gráfico de barras Z-Score
                        st.markdown('<p class="section-title">Z-Score vs Perfil de Referência</p>', unsafe_allow_html=True)
                        fig_perf = go.Figure(go.Bar(
                            y=df_perf["Métrica"],
                            x=df_perf["Z-Score"],
                            orientation="h",
                            marker_color=df_perf["_cor"].tolist(),
                            text=df_perf["Z-Score"].round(2),
                            textposition="outside",
                        ))
                        fig_perf.add_vline(x=0,  line_color="white", line_width=1)
                        fig_perf.add_vline(x=1,  line_dash="dot", line_color="#f39c12", annotation_text="+1σ")
                        fig_perf.add_vline(x=-1, line_dash="dot", line_color="#3498db", annotation_text="-1σ")
                        fig_perf.add_vline(x=2,  line_dash="dash", line_color="#e74c3c", annotation_text="+2σ")
                        fig_perf.add_vline(x=-2, line_dash="dash", line_color="#9b59b6", annotation_text="-2σ")
                        fig_perf.update_layout(
                            height=max(300, len(df_perf)*50),
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                            font_color="rgba(255,255,255,0.85)", xaxis_title="Z-Score", margin=dict(t=10),
                        )
                        st.plotly_chart(fig_perf, use_container_width=True)

                        # Evolução histórica de uma métrica
                        st.divider()
                        st.markdown('<p class="section-title">Evolução Histórica com Bandas de Referência</p>', unsafe_allow_html=True)
                        met_ev = st.selectbox("Métrica", df_perf["Métrica"].tolist(), key="perf_ev")
                        mu_ev  = float(df_perf[df_perf["Métrica"] == met_ev]["Ref. Média"].iloc[0])
                        sig_ev = float(df_perf[df_perf["Métrica"] == met_ev]["Ref. ±DP"].iloc[0])

                        fig_ev = go.Figure()
                        fig_ev.add_hrect(y0=mu_ev-sig_ev, y1=mu_ev+sig_ev,   fillcolor="#2ecc71", opacity=0.08, line_width=0)
                        fig_ev.add_hrect(y0=mu_ev+sig_ev, y1=mu_ev+2*sig_ev, fillcolor="#f39c12", opacity=0.08, line_width=0)
                        fig_ev.add_hrect(y0=mu_ev-2*sig_ev, y1=mu_ev-sig_ev, fillcolor="#3498db", opacity=0.08, line_width=0)
                        fig_ev.add_trace(go.Scatter(
                            x=df_jog_p["Data"], y=df_jog_p[met_ev],
                            mode="lines+markers", line_color="#e63946", line_width=2, marker_size=6,
                            name=met_ev,
                        ))
                        fig_ev.add_hline(y=mu_ev, line_dash="dash", line_color="white", line_width=1, annotation_text="Média ref.")
                        fig_ev.add_hline(y=mu_ev+sig_ev,   line_dash="dot", line_color="#f39c12")
                        fig_ev.add_hline(y=mu_ev-sig_ev,   line_dash="dot", line_color="#3498db")
                        try:
                            fig_ev.add_vline(x=data_corte.timestamp()*1000, line_dash="dash", line_color="#888",
                                              annotation_text="Fim período ref.")
                        except Exception:
                            pass
                        fig_ev.update_layout(
                            height=360, yaxis_title=met_ev,
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                            font_color="rgba(255,255,255,0.85)", margin=dict(t=20), showlegend=False,
                        )
                        st.plotly_chart(fig_ev, use_container_width=True)

                        # Exportar relatório
                        st.divider()
                        linhas_tab = "".join([
                            f'<tr><td>{r["Métrica"]}</td><td>{r["Ref. Média"]} ± {r["Ref. ±DP"]}</td>'
                            f'<td>{r["Último Valor"]}</td><td>{r["Z-Score"]}</td><td>{r["Estado"]}</td></tr>'
                            for _, r in df_perf.iterrows()
                        ])
                        html_perf = gerar_pdf_html(f"""
        <h1>Perfil de Referência — {jog_p}</h1>
        <p>Referência: {df_ref["Data"].min().strftime("%d/%m/%Y")} a {df_ref["Data"].max().strftime("%d/%m/%Y")} ({len(df_ref)} sessões)</p>
        <table><tr><th>Métrica</th><th>Ref. Média ± DP</th><th>Último Valor</th><th>Z-Score</th><th>Estado</th></tr>
        {linhas_tab}</table>
        """, f"Perfil_{jog_p}.html")
                        botao_download_html(html_perf, f"Perfil_{jog_p.replace(' ','_')}.html", f"📥 Exportar Perfil de {jog_p}")

            # ── TAB 2: Semáforo da equipa ─────────────────────────────────────────────
            with tab_p2:
                st.markdown('<p class="section-title">Semáforo de Z-Score Pessoal — Última Sessão vs Perfil Próprio</p>', unsafe_allow_html=True)
                met_eq_p = st.selectbox("Métrica", mets_disp, key="perf_eq_met")
                semanas_ref = st.slider("Semanas de referência", 4, 20, 8, key="perf_eq_sem")

                equipa_perfil = []
                for jog in sorted(df["Jogador"].dropna().unique()):
                    df_j = df[df["Jogador"] == jog].dropna(subset=["Data", met_eq_p]).sort_values("Data")
                    if len(df_j) < 5: continue
                    corte = df_j["Data"].min() + pd.Timedelta(weeks=semanas_ref)
                    ref = df_j[df_j["Data"] <= corte][met_eq_p]
                    rec = df_j[df_j["Data"] > corte][met_eq_p]
                    if ref.empty or rec.empty: continue
                    mu, sig = ref.mean(), ref.std()
                    if sig == 0: continue
                    ult = rec.iloc[-1]
                    z = (ult - mu) / sig
                    if z > 2:     estado, cor = "🔴 Muito Acima", "#e74c3c"
                    elif z > 1:   estado, cor = "🟡 Acima",       "#f39c12"
                    elif z >= -1: estado, cor = "🟢 Normal",      "#2ecc71"
                    elif z >= -2: estado, cor = "🔵 Abaixo",      "#3498db"
                    else:         estado, cor = "🟣 Muito Abaixo","#9b59b6"
                    pos = df_j["Posição"].iloc[-1] if "Posição" in df_j.columns else "—"
                    equipa_perfil.append({"Jogador": jog, "Posição": pos, "Ref. Média": round(mu,1),
                                           "Último": round(ult,1), "Z-Score": round(z,2),
                                           "Estado": estado, "_cor": cor})

                if equipa_perfil:
                    df_ep = pd.DataFrame(equipa_perfil).sort_values("Z-Score", ascending=False)
                    cols_sem = st.columns(min(len(df_ep), 5))
                    for i, (_, row) in enumerate(df_ep.iterrows()):
                        cols_sem[i % 5].markdown(
                            f'<div style="background:{row["_cor"]}22;border:2px solid {row["_cor"]};border-radius:10px;'
                            f'padding:10px;text-align:center;margin:4px">'
                            f'<b style="font-size:0.9rem">{row["Jogador"]}</b><br>'
                            f'<span style="font-size:0.75rem;color:#aaa">{row["Posição"]}</span><br>'
                            f'<b style="font-size:1.3rem;color:{row["_cor"]}">{row["Z-Score"]:+.2f}</b><br>'
                            f'<span style="font-size:0.7rem">{row["Estado"]}</span></div>',
                            unsafe_allow_html=True
                        )

                    st.divider()
                    fig_eq_perf = go.Figure(go.Bar(
                        x=df_ep["Jogador"], y=df_ep["Z-Score"],
                        marker_color=df_ep["_cor"].tolist(),
                        text=df_ep["Z-Score"].round(2), textposition="outside",
                    ))
                    fig_eq_perf.add_hline(y=1,  line_dash="dot", line_color="#f39c12")
                    fig_eq_perf.add_hline(y=-1, line_dash="dot", line_color="#3498db")
                    fig_eq_perf.add_hline(y=0,  line_color="white", line_width=1)
                    fig_eq_perf.update_layout(
                        yaxis_title=f"Z-Score ({met_eq_p})", height=380,
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font_color="rgba(255,255,255,0.85)", margin=dict(t=20), showlegend=False,
                    )
                    st.plotly_chart(fig_eq_perf, use_container_width=True)
                else:
                    st.warning("Dados insuficientes para calcular perfis individuais.")


        # ═══════════════════════════════════════════════════════════════════════════════
        # VISTA: LESÕES & DISPONIBILIDADE
        # ═══════════════════════════════════════════════════════════════════════════════

    with st.expander("🦵 Testes Neuromusculares", expanded=False):

            try:
                df_cmj = pd.read_excel(excel_path, sheet_name="Testes_Neuromusculares", engine="openpyxl")
                df_cmj.columns = [str(c).strip() for c in df_cmj.columns]
                tem_dados = not df_cmj.empty and len(df_cmj) > 1
            except Exception:
                df_cmj = pd.DataFrame(); tem_dados = False

            if not tem_dados:
                st.info("""
        ### Folha 'Testes_Neuromusculares' não encontrada

        Adiciona uma folha ao Excel com estas colunas:
        **Data · Jogador · Posição · Tipo Teste · Altura Salto (cm) · Potência Relativa (W/kg) · RSI (m/s) · Assimetria (%) · Fase Excêntrica (s) · Fase Concêntrica (s) · RFD (N/s) · Microciclo (Nr) · Observações**
                """)
                # Dados de exemplo
                np.random.seed(42)
                jogs_ex = ["Paulino","Rafael","André","Diogo","Miguel","Carlos","João","Pedro","Tiago","Luís"]
                pos_ex  = ["GR","DC","DC","DD","DE","MC","MC","MD","AV","AV"]
                df_cmj = pd.DataFrame({
                    "Jogador": jogs_ex, "Posição": pos_ex,
                    "Altura Salto (cm)": np.random.normal(35,5,10).clip(22,50).round(1),
                    "Potência Relativa (W/kg)": np.random.normal(40,6,10).clip(26,56).round(1),
                    "Assimetria (%)": np.random.exponential(4,10).clip(0,18).round(1),
                    "RSI (m/s)": np.random.normal(1.8,0.3,10).clip(1.0,2.8).round(2),
                    "Tipo Teste": ["CMJ"]*10, "Data": [pd.Timestamp("2025-01-15")]*10,
                })
                st.caption("⚠️ Dados de exemplo — adiciona a folha 'Testes_Neuromusculares' para ver os teus dados")

            for col in ["Altura Salto (cm)","Potência Relativa (W/kg)","Assimetria (%)","RSI (m/s)","RFD (N/s)"]:
                if col in df_cmj.columns:
                    df_cmj[col] = pd.to_numeric(df_cmj[col], errors="coerce")

            df_latest = df_cmj.groupby("Jogador").last().reset_index() if "Jogador" in df_cmj.columns else df_cmj

            tab_nm1, tab_nm2, tab_nm3 = st.tabs(["🎯 Perfil Neuromuscular", "🏆 Rankings", "⚖️ Assimetria"])

            with tab_nm1:
                if "Altura Salto (cm)" in df_latest.columns and "RSI (m/s)" in df_latest.columns:
                    df_sc_nm = df_latest.dropna(subset=["Altura Salto (cm)","RSI (m/s)"]).copy()
                    if not df_sc_nm.empty:
                        x_mean_nm = df_sc_nm["Altura Salto (cm)"].mean()
                        y_mean_nm = df_sc_nm["RSI (m/s)"].mean()
                        CORES_POS_NM = {"GR":"#3498db","DC":"#2ecc71","DD":"#2ecc71","DE":"#2ecc71","MC":"#f39c12","MD":"#f39c12","AV":"#e63946"}
                        fig_nm = go.Figure()
                        fig_nm.add_hline(y=y_mean_nm, line_dash="dot", line_color="rgba(255,255,255,0.2)")
                        fig_nm.add_vline(x=x_mean_nm, line_dash="dot", line_color="rgba(255,255,255,0.2)")
                        for lbl, xp, yp, cor_q in [
                            ("EXPLOSIVE", df_sc_nm["Altura Salto (cm)"].max(), df_sc_nm["RSI (m/s)"].max(), "#2ecc71"),
                            ("POWER",     df_sc_nm["Altura Salto (cm)"].max(), df_sc_nm["RSI (m/s)"].min(), "#3498db"),
                            ("REACTIVE",  df_sc_nm["Altura Salto (cm)"].min(), df_sc_nm["RSI (m/s)"].max(), "#f39c12"),
                            ("UNDERPOWERED", df_sc_nm["Altura Salto (cm)"].min(), df_sc_nm["RSI (m/s)"].min(), "#e74c3c"),
                        ]:
                            fig_nm.add_annotation(x=xp, y=yp, text=lbl, font=dict(size=9, color=cor_q), showarrow=False, opacity=0.5)
                        for pos in df_sc_nm["Posição"].dropna().unique() if "Posição" in df_sc_nm.columns else [None]:
                            sub = df_sc_nm[df_sc_nm["Posição"]==pos] if pos else df_sc_nm
                            cor = CORES_POS_NM.get(str(pos), "#9b59b6") if pos else "#00d4ff"
                            fig_nm.add_trace(go.Scatter(
                                x=sub["Altura Salto (cm)"], y=sub["RSI (m/s)"],
                                mode="markers+text",
                                text=sub["Jogador"].apply(lambda n: n.split()[0] if isinstance(n,str) else n),
                                textposition="top center", textfont=dict(size=9, color="white"),
                                marker=dict(size=18, color=cor, opacity=0.85, line=dict(width=2, color="white")),
                                name=str(pos) if pos else "Todos",
                            ))
                        fig_nm.update_layout(height=520, xaxis_title="Altura Salto CMJ (cm)", yaxis_title="RSI (m/s)",
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)", margin=dict(t=20))
                        st.plotly_chart(fig_nm, use_container_width=True)

            with tab_nm2:
                mets_rank_nm = get_mets_gps(df_latest)
                if mets_rank_nm:
                    met_nm = st.selectbox("Métrica", mets_rank_nm, key="nm_rank")
                    df_rk_nm = df_latest.dropna(subset=[met_nm]).sort_values(met_nm, ascending=True)
                    fig_rk_nm = go.Figure(go.Bar(y=df_rk_nm["Jogador"], x=df_rk_nm[met_nm], orientation="h",
                        marker_color="#e63946", text=df_rk_nm[met_nm].round(1), textposition="outside"))
                    fig_rk_nm.add_vline(x=df_rk_nm[met_nm].mean(), line_dash="dash", line_color="white",
                                          annotation_text=f"Média: {df_rk_nm[met_nm].mean():.1f}")
                    fig_rk_nm.update_layout(height=max(300,len(df_rk_nm)*42), xaxis_title=met_nm,
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)", margin=dict(t=5))
                    st.plotly_chart(fig_rk_nm, use_container_width=True)

            with tab_nm3:
                if "Assimetria (%)" in df_latest.columns and df_latest["Assimetria (%)"].notna().any():
                    df_asy = df_latest.dropna(subset=["Assimetria (%)"]).sort_values("Assimetria (%)", ascending=False)
                    cores_asy = ["#e74c3c" if v>15 else "#f39c12" if v>10 else "#2ecc71" for v in df_asy["Assimetria (%)"]]
                    fig_asy = go.Figure(go.Bar(x=df_asy["Jogador"], y=df_asy["Assimetria (%)"],
                        marker_color=cores_asy, text=df_asy["Assimetria (%)"].apply(lambda v: f"{v:.1f}%"), textposition="outside"))
                    fig_asy.add_hline(y=15, line_dash="dash", line_color="#e74c3c", annotation_text="Crítico 15%")
                    fig_asy.add_hline(y=10, line_dash="dot",  line_color="#f39c12", annotation_text="Atenção 10%")
                    fig_asy.update_layout(height=340, yaxis_title="Assimetria (%)",
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)", margin=dict(t=10))
                    st.plotly_chart(fig_asy, use_container_width=True)
                    criticos = df_asy[df_asy["Assimetria (%)"]>15]["Jogador"].tolist()
                    if criticos: st.error(f"🔴 Assimetria crítica (>15%): {', '.join(criticos)}")


        # ═══════════════════════════════════════════════════════════════════════════════
        # 🏃 NORMALIZAÇÃO HSR/SPRINT
        # ═══════════════════════════════════════════════════════════════════════════════

            st.markdown("> Ref.: **Pimenta et al.** — *Sprint and High-Speed Running: Should We Use Absolute or Normalized Thresholds?* · Journal of Human Kinetics")

            if "Vel. Máx (km/h)" not in df.columns:
                st.error("Coluna 'Vel. Máx (km/h)' necessária.")

            vmaxes = df.groupby("Jogador")["Vel. Máx (km/h)"].max().reset_index()
            vmaxes.columns = ["Jogador","Vmáx Record (km/h)"]
            for pct in [85,90,95]:
                vmaxes[f"Lim {pct}% (km/h)"] = (vmaxes["Vmáx Record (km/h)"] * pct/100).round(1)
            if "Posição" in df.columns:
                vmaxes["Posição"] = vmaxes["Jogador"].map(df.groupby("Jogador")["Posição"].last())

            tab_nh1, tab_nh2 = st.tabs(["📊 Limiares Individuais", "📐 Absoluto vs Normalizado"])

            with tab_nh1:
                df_vs = vmaxes.sort_values("Vmáx Record (km/h)", ascending=True)
                fig_vn = go.Figure()
                fig_vn.add_trace(go.Bar(y=df_vs["Jogador"], x=df_vs["Vmáx Record (km/h)"],
                    orientation="h", marker_color="#e63946", name="Vmáx Record",
                    text=df_vs["Vmáx Record (km/h)"].round(1), textposition="outside"))
                fig_vn.add_trace(go.Bar(y=df_vs["Jogador"], x=df_vs["Lim 90% (km/h)"],
                    orientation="h", marker_color="rgba(255,255,255,0.15)", name="Limiar 90%"))
                fig_vn.update_layout(barmode="overlay", height=max(300,len(df_vs)*42),
                    xaxis_title="km/h", yaxis=dict(autorange="reversed"),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)", margin=dict(t=5))
                st.plotly_chart(fig_vn, use_container_width=True)
                st.dataframe(vmaxes.set_index("Jogador"), use_container_width=True)

            with tab_nh2:
                if "Posição" in vmaxes.columns:
                    pos_vmax = vmaxes.groupby("Posição").agg(
                        Vmáx_media=("Vmáx Record (km/h)","mean"),
                        Vmáx_max=("Vmáx Record (km/h)","max"),
                        Vmáx_min=("Vmáx Record (km/h)","min"),
                        n=("Jogador","count"),
                    ).reset_index().sort_values("Vmáx_media", ascending=False)
                    fig_pos_vn = go.Figure()
                    fig_pos_vn.add_trace(go.Bar(x=pos_vmax["Posição"], y=pos_vmax["Vmáx_media"],
                        name="Vmáx Média", marker_color="#e63946",
                        text=pos_vmax["Vmáx_media"].round(1), textposition="outside",
                        error_y=dict(type="data",
                            array=(pos_vmax["Vmáx_max"]-pos_vmax["Vmáx_media"]).tolist(),
                            arrayminus=(pos_vmax["Vmáx_media"]-pos_vmax["Vmáx_min"]).tolist(),
                            visible=True, color="rgba(255,255,255,0.4)"),
                    ))
                    fig_pos_vn.add_hline(y=25, line_dash="dash", line_color="#f39c12", annotation_text="Limiar absoluto 25 km/h")
                    fig_pos_vn.add_hline(y=19.8, line_dash="dot", line_color="#3498db", annotation_text="Limiar absoluto 19.8 km/h")
                    fig_pos_vn.update_layout(height=380, yaxis_title="Velocidade Máxima (km/h)",
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font_color="rgba(255,255,255,0.85)", showlegend=False, margin=dict(t=20))
                    st.plotly_chart(fig_pos_vn, use_container_width=True)
                    st.caption("Barras de erro = min–max · Linhas = limiares absolutos standard")


        # ═══════════════════════════════════════════════════════════════════════════════
        # 🧮 CALCULADORA DE EXERCÍCIOS
        # ═══════════════════════════════════════════════════════════════════════════════
            st.markdown("> **Casamichana & Castellano (2010)** · **Dellal et al. (2012)** · **Hill-Haas et al. (2011)** · **Owen et al. (2011)**")

            EXERCICIOS_REF = {
                "Rondo / Posse fechada":           {"dist_min":82,  "acc_min":1.8, "frac_hsr":0.015,"frac_spr":0.003,"frac_dcc":0.85,"vmax_ref":23,"metabolico":"Aeróbia lática mista","neuro":"Força-Velocidade"},
                "Jogo Posicional (5-8v5-8)":       {"dist_min":110, "acc_min":2.4, "frac_hsr":0.060,"frac_spr":0.010,"frac_dcc":0.82,"vmax_ref":26,"metabolico":"Aeróbia-Anaeróbia","neuro":"Potência"},
                "Jogo Reduzido Pequeno (3-4v)":    {"dist_min":130, "acc_min":3.6, "frac_hsr":0.035,"frac_spr":0.008,"frac_dcc":0.88,"vmax_ref":25,"metabolico":"Anaeróbia lática","neuro":"Força-Velocidade"},
                "Jogo Reduzido Médio (5-7v)":      {"dist_min":118, "acc_min":2.8, "frac_hsr":0.065,"frac_spr":0.018,"frac_dcc":0.85,"vmax_ref":27,"metabolico":"Aeróbia-Anaeróbia mista","neuro":"Potência-Velocidade"},
                "Jogo Reduzido Grande (8-10v)":    {"dist_min":108, "acc_min":2.0, "frac_hsr":0.090,"frac_spr":0.030,"frac_dcc":0.80,"vmax_ref":29,"metabolico":"Predominantemente aeróbia","neuro":"Resistência"},
                "Jogo Formal (11v11)":             {"dist_min":115, "acc_min":1.6, "frac_hsr":0.110,"frac_spr":0.038,"frac_dcc":0.80,"vmax_ref":31,"metabolico":"Aeróbia com picos","neuro":"Velocidade-Resistência"},
                "Sprint / Velocidade":             {"dist_min":145, "acc_min":4.5, "frac_hsr":0.280,"frac_spr":0.180,"frac_dcc":0.88,"vmax_ref":32,"metabolico":"Anaeróbia alática","neuro":"Velocidade máxima"},
                "Físico / Resistência":            {"dist_min":185, "acc_min":0.8, "frac_hsr":0.020,"frac_spr":0.002,"frac_dcc":0.80,"vmax_ref":20,"metabolico":"Aeróbia extensiva","neuro":"Resistência"},
                "Técnico-Tático":                  {"dist_min":70,  "acc_min":1.2, "frac_hsr":0.010,"frac_spr":0.002,"frac_dcc":0.82,"vmax_ref":22,"metabolico":"Aeróbia leve","neuro":"Coordenação"},
                "Ativação / Aquecimento":          {"dist_min":55,  "acc_min":0.6, "frac_hsr":0.005,"frac_spr":0.001,"frac_dcc":0.80,"vmax_ref":19,"metabolico":"Aeróbia leve","neuro":"Ativação"},
                "Retorno à Calma":                 {"dist_min":30,  "acc_min":0.2, "frac_hsr":0.002,"frac_spr":0.000,"frac_dcc":0.80,"vmax_ref":14,"metabolico":"Recuperação","neuro":"Recuperação"},
            }

            tab_c1, tab_c2 = st.tabs(["🧮 Calculadora", "📋 Tabela de Referência"])

            with tab_c1:
                col_c1, col_c2 = st.columns(2)
                tipo_ex = col_c1.selectbox("Tipo de Exercício", list(EXERCICIOS_REF.keys()), key="calc_tipo")
                n_jog   = col_c2.number_input("Nº de Jogadores", 2, 22, 8, key="calc_njog")
                duracao = col_c1.number_input("Duração (min)", 1, 60, 15, key="calc_dur")
                espaco  = col_c2.number_input("Espaço total (m²)", 50, 10000, 800, key="calc_esp")

                ref = EXERCICIOS_REF[tipo_ex]
                esp_jog = espaco / n_jog if n_jog > 0 else 100
                fator_esp = max(0.6, min(1.0 + (esp_jog - 100)/100 * 0.18, 1.6))
                fator_acc = max(0.5, min(1.0 + (100 - esp_jog)/100 * 0.25, 1.5))

                dist_jog   = ref["dist_min"] * duracao * fator_esp
                hsr_jog    = dist_jog * ref["frac_hsr"]
                sprint_jog = dist_jog * ref["frac_spr"]
                acc_jog    = ref["acc_min"] * fator_acc * duracao
                dcc_jog    = acc_jog * ref["frac_dcc"]
                vmax_ref   = ref["vmax_ref"]

                st.divider()
                st.markdown('<p class="section-title">📊 Previsão por Jogador</p>', unsafe_allow_html=True)
                k1,k2,k3,k4,k5,k6 = st.columns(6)
                for col_k, lbl, val, unit, hlp in [
                    (k1,"Distância",      f"{dist_jog:,.0f}","m",   "Distância total estimada"),
                    (k2,"HSR",            f"{hsr_jog:,.0f}", "m",   "Alta Velocidade"),
                    (k3,"Sprint",         f"{sprint_jog:,.0f}","m", "Velocidade máxima"),
                    (k4,"Acc (n)",        f"{acc_jog:.0f}",  "",    "Acelerações estimadas"),
                    (k5,"Dcc (n)",        f"{dcc_jog:.0f}",  "",    "Desacelerações estimadas"),
                    (k6,"Vmáx esperada",  f"{vmax_ref}",     "km/h","Velocidade máxima de referência"),
                ]:
                    col_k.metric(f"{lbl} {unit}".strip(), val, help=hlp)

                st.markdown('<p class="section-title">📦 Total da Equipa</p>', unsafe_allow_html=True)
                te1,te2,te3,te4,te5 = st.columns(5)
                te1.metric("Distância Total", f"{dist_jog*n_jog/1000:.2f} km")
                te2.metric("HSR Total",       f"{hsr_jog*n_jog:,.0f} m")
                te3.metric("Sprint Total",    f"{sprint_jog*n_jog:,.0f} m")
                te4.metric("Acc Total",       f"{acc_jog*n_jog:.0f}")
                te5.metric("Dcc Total",       f"{dcc_jog*n_jog:.0f}")

                col_i1,col_i2,col_i3 = st.columns(3)
                col_i1.info(f"⚗️ **Perfil Metabólico:** {ref['metabolico']}")
                col_i2.info(f"💪 **Perfil Neuromuscular:** {ref['neuro']}")
                col_i3.info(f"📐 **m²/jog:** {esp_jog:.0f} · Fator: {fator_esp:.2f}×")

            with tab_c2:
                df_ref_tab = pd.DataFrame([{
                    "Tipo": k, "Dist/min (m)": v["dist_min"],
                    "Acc/min": v["acc_min"], "Frac. HSR": f"{v['frac_hsr']*100:.1f}%",
                    "Frac. Sprint": f"{v['frac_spr']*100:.1f}%",
                    "Vmáx Ref (km/h)": v["vmax_ref"],
                    "Perfil Metabólico": v["metabolico"], "Perfil Neuro": v["neuro"],
                } for k,v in EXERCICIOS_REF.items()])
                st.dataframe(df_ref_tab.set_index("Tipo"), use_container_width=True)
                st.caption("Fonte: Casamichana & Castellano (2010) · Dellal et al. (2012) · Hill-Haas et al. (2011)")


        # ═══════════════════════════════════════════════════════════════════════════════
        # 📐 ESPAÇO & CARGA EXTERNA
        # ═══════════════════════════════════════════════════════════════════════════════
            st.markdown("> **Casamichana & Castellano (2010)** · **Dellal et al. (2012)** · **Hill-Haas et al. (2011)** · *'Duplicar o espaço → +15–25% distância'* (r=0.76)")

            ZONAS_ESP = [
                {"zona":"ZONA 1 — < 30 m²/jog",    "esp_min":0,   "esp_max":30,  "dist":"70–90 m/min",  "hsr":"<1%",    "sprint":"<0.3%",  "acc":"4–6/min",    "exemplos":"Rondos, posses fechadas","cor":"#2ecc71"},
                {"zona":"ZONA 2 — 30–100 m²/jog",  "esp_min":30,  "esp_max":100, "dist":"90–115 m/min", "hsr":"3–7%",   "sprint":"0.5–1%", "acc":"2–4/min",    "exemplos":"Jogos reduzidos 4v4–7v7","cor":"#f39c12"},
                {"zona":"ZONA 3 — 100–200 m²/jog", "esp_min":100, "esp_max":200, "dist":"110–130 m/min","hsr":"7–12%",  "sprint":"1.5–3%", "acc":"1–2/min",    "exemplos":"Jogos 8v8–10v10",        "cor":"#e67e22"},
                {"zona":"ZONA 4 — > 200 m²/jog",   "esp_min":200, "esp_max":999, "dist":">130 m/min",   "hsr":">12%",   "sprint":">3%",    "acc":"<1/min",     "exemplos":"Jogo formal",            "cor":"#e74c3c"},
            ]

            tab_esp1, tab_esp2 = st.tabs(["📊 Matriz de Referência", "🧮 Simulador"])

            with tab_esp1:
                cols_z = st.columns(4)
                for i, zona in enumerate(ZONAS_ESP):
                    cor_z = zona["cor"]
                    cols_z[i].markdown(
                        f'<div style="background:{cor_z}18;border:1px solid {cor_z}44;border-top:3px solid {cor_z};border-radius:10px;padding:14px;margin:4px">'
                        f'<div style="font-size:0.72rem;font-weight:700;color:{cor_z};margin-bottom:10px">{zona["zona"]}</div>'
                        f'<div style="font-size:0.68rem;color:rgba(255,255,255,0.8);margin:5px 0"><b>Distância:</b> {zona["dist"]}</div>'
                        f'<div style="font-size:0.68rem;color:rgba(255,255,255,0.8);margin:5px 0"><b>HSR:</b> {zona["hsr"]}</div>'
                        f'<div style="font-size:0.68rem;color:rgba(255,255,255,0.8);margin:5px 0"><b>Sprint:</b> {zona["sprint"]}</div>'
                        f'<div style="font-size:0.68rem;color:rgba(255,255,255,0.8);margin:5px 0"><b>Acc/Dcc:</b> {zona["acc"]}</div>'
                        f'<div style="font-size:0.62rem;color:rgba(255,255,255,0.4);margin-top:8px;padding-top:6px;border-top:1px solid rgba(255,255,255,0.06)">{zona["exemplos"]}</div>'
                        f'</div>', unsafe_allow_html=True)

            with tab_esp2:
                col_s1,col_s2,col_s3 = st.columns(3)
                s_x    = col_s1.number_input("Comprimento (m)", 10, 120, 40, key="esp_x")
                s_y    = col_s2.number_input("Largura (m)", 5, 80, 30, key="esp_y")
                s_njog = col_s3.number_input("Nº Jogadores em campo", 4, 22, 10, key="esp_njog_total")
                s_dur  = col_s1.number_input("Duração (min)", 1, 60, 12, key="esp_dur")
                s_tipo = col_s2.selectbox("Tipo", ["Jogo Reduzido","Jogo Posicional","Jogo Formal","Sprint"], key="esp_tipo")

                area_total = s_x * s_y
                area_jog   = area_total / s_njog if s_njog > 0 else 100
                base_dist  = {"Jogo Reduzido":100,"Jogo Posicional":110,"Jogo Formal":115,"Sprint":145}.get(s_tipo,110)
                fator_s    = max(0.6, min(1.0 + (area_jog - 100)/100 * 0.18, 1.6))
                fator_a    = max(0.5, min(1.0 + (100 - area_jog)/100 * 0.25, 1.5))
                frac_hsr   = {"Jogo Reduzido":0.065,"Jogo Posicional":0.060,"Jogo Formal":0.110,"Sprint":0.280}.get(s_tipo,0.065)
                frac_spr   = {"Jogo Reduzido":0.018,"Jogo Posicional":0.010,"Jogo Formal":0.038,"Sprint":0.180}.get(s_tipo,0.018)
                acc_min    = {"Jogo Reduzido":2.8,"Jogo Posicional":2.4,"Jogo Formal":1.6,"Sprint":4.5}.get(s_tipo,2.8)

                dist_s = base_dist * fator_s * s_dur
                hsr_s  = dist_s * frac_hsr
                spr_s  = dist_s * frac_spr
                acc_s  = acc_min * fator_a * s_dur
                dcc_s  = acc_s * 0.85

                zona_id = next((z for z in ZONAS_ESP if z["esp_min"] <= area_jog < z["esp_max"]), ZONAS_ESP[-1])
                cor_z2 = zona_id["cor"]
                st.markdown(f'<div style="background:{cor_z2}18;border:2px solid {cor_z2}55;border-radius:12px;padding:14px;margin:10px 0"><div style="font-size:0.75rem;font-weight:700;color:{cor_z2}">{zona_id["zona"]} — {area_jog:.0f} m²/jogador</div><div style="font-size:0.78rem;color:rgba(255,255,255,0.7);margin-top:4px">{s_x}×{s_y}m = {area_total} m² · {s_njog} jogadores</div></div>', unsafe_allow_html=True)

                k1e,k2e,k3e,k4e,k5e,k6e = st.columns(6)
                for col_ke, lbl_e, val_e in [
                    (k1e,"Distância/jog",f"{dist_s:,.0f} m"),
                    (k2e,"HSR/jog",      f"{hsr_s:,.0f} m"),
                    (k3e,"Sprint/jog",   f"{spr_s:,.0f} m"),
                    (k4e,"Acc/jog",      f"{acc_s:.0f}"),
                    (k5e,"Dcc/jog",      f"{dcc_s:.0f}"),
                    (k6e,"Fator Espaço", f"{fator_s:.2f}×"),
                ]:
                    col_ke.metric(lbl_e, val_e)


        # ═══════════════════════════════════════════════════════════════════════════════
        # ✅ VALIDAÇÃO DE DADOS
        # ═══════════════════════════════════════════════════════════════════════════════

            if st.button("🔍 Validar agora", type="primary"):
                with st.spinner("A analisar..."):
                    erros, avisos, ok_list = validar_dados(df)

                total = len(erros) + len(avisos) + len(ok_list)
                score = int(len(ok_list)/total*100) if total > 0 else 0
                cor_s = "#2ecc71" if score>=80 else "#f39c12" if score>=60 else "#e74c3c"

                col_sc, col_res = st.columns([1,3])
                col_sc.markdown(f'<div style="background:{cor_s}22;border:3px solid {cor_s};border-radius:16px;padding:20px;text-align:center"><div style="font-size:0.9rem;color:#aaa">Qualidade</div><div style="font-size:3rem;font-weight:900;color:{cor_s}">{score}%</div></div>', unsafe_allow_html=True)
                col_res.metric("❌ Erros críticos", len(erros))
                col_res.metric("⚠️ Avisos", len(avisos))
                col_res.metric("✅ OK", len(ok_list))

                st.divider()
                for e in erros:   st.error(e)
                for a in avisos:  st.warning(a)
                for o in ok_list: st.success(o)

                st.divider()
                st.markdown("### 🔍 Valores únicos por coluna crítica")
                for col in ["Tipo","Dia MD","Posição","Microciclo (Nr)"]:
                    if col in df.columns:
                        vals = df[col].dropna().unique()
                        with st.expander(f"**{col}** — {len(vals)} valores únicos"):
                            st.write(sorted([str(v) for v in vals]))

                cols_crit = get_mets_gps(df)
                df_nulos = df[df[cols_crit].isna().any(axis=1)][cols_crit]
                if df_nulos.empty:
                    st.success("✅ Nenhum registo com campos críticos em falta!")
                else:
                    st.warning(f"{len(df_nulos)} registos com campos críticos em falta:")
                    st.dataframe(df_nulos, use_container_width=True)
            else:
                st.info("Clica em **🔍 Validar agora** para analisar a qualidade dos dados.")






elif seccao == "planeamento":
    lm_header("Planeamento", "Ferramentas de planeamento e comparação com jogo", "Planeamento")
    tab_plan = st.tabs(["📋 Planeado vs Realizado", "⚽ Jogo vs Treino", "📊 Treino vs Jogo %"])

    with tab_plan[0]:
            st.markdown('<p class="section-title">⚽ Carga de Jogo vs Carga de Treino</p>', unsafe_allow_html=True)
            st.caption("Percentagem da carga de jogo em relação ao total do microciclo")

            METRICAS_JOGO = [
                "Distância Total (m)", "HSR (m)", "Sprint (m)",
                "Acc (n)", "Dcc (n)", "Carga Interna", "PSE Sessão",
            ]
            mets_jogo_disp = [m for m in METRICAS_JOGO if m in df.columns]

            # Separar treinos e jogos
            if "Tipo" not in df.columns:
                st.error("Coluna 'Tipo' não encontrada. Certifica-te que o Excel tem a coluna 'Tipo' com valores 'Treino' e 'Jogo'.")

            df_jogos   = df[df["Tipo"].str.strip().str.lower() == "jogo"].copy()
            df_treinos = df[df["Tipo"].str.strip().str.lower() == "treino"].copy()

            if df_jogos.empty:
                st.warning("Nenhum registo com Tipo = 'Jogo' encontrado no Excel.")

            # Filtros de contexto
            col1, col2, col3 = st.columns(3)
            mc_jogo = col1.selectbox("Microciclo", sorted(df["Microciclo (Nr)"].dropna().unique(), reverse=True), key="jogo_mc")
            met_jogo = col2.selectbox("Métrica", mets_jogo_disp, key="jogo_met")
            modo_jogo = col3.radio("Modo de comparação", ["Por Jogador", "Equipa (média)"], key="jogo_modo")

            st.divider()

            # ── Dados do microciclo selecionado ───────────────────────────────────────
            jogos_mc   = df_jogos[df_jogos["Microciclo (Nr)"] == mc_jogo]
            treinos_mc = df_treinos[df_treinos["Microciclo (Nr)"] == mc_jogo]

            if jogos_mc.empty:
                st.warning(f"Sem registos de jogo para o Microciclo {int(mc_jogo)}.")

            if treinos_mc.empty:
                st.warning(f"Sem registos de treino para o Microciclo {int(mc_jogo)}.")

            # ── MODO: POR JOGADOR ─────────────────────────────────────────────────────
            if modo_jogo == "Por Jogador":
                jog_jogo = st.selectbox("Jogador", sorted(df["Jogador"].dropna().unique()), key="jogo_jog")

                jogo_jog   = jogos_mc[jogos_mc["Jogador"] == jog_jogo]
                treino_jog = treinos_mc[treinos_mc["Jogador"] == jog_jogo]

                if jogo_jog.empty or treino_jog.empty:
                    st.warning(f"Dados insuficientes para {jog_jogo} no MC {int(mc_jogo)}.")
    
                carga_jogo_val   = jogo_jog[met_jogo].sum()
                carga_treino_val = treino_jog[met_jogo].sum()
                carga_total      = carga_jogo_val + carga_treino_val
                pct_jogo         = (carga_jogo_val / carga_total * 100) if carga_total > 0 else 0
                pct_treino       = 100 - pct_jogo

                # KPIs
                k1, k2, k3, k4 = st.columns(4)
                k1.metric(f"Carga Jogo ({met_jogo})",   f"{carga_jogo_val:,.1f}")
                k2.metric(f"Carga Treino ({met_jogo})",  f"{carga_treino_val:,.1f}")
                k3.metric("Total Semanal",               f"{carga_total:,.1f}")
                k4.metric("% Jogo / Total",              f"{pct_jogo:.1f}%")

                st.divider()

                # Gráfico de rosca jogo vs treino
                col_pie, col_bar = st.columns(2)

                with col_pie:
                    st.markdown('<p class="section-title">Proporção Jogo vs Treino</p>', unsafe_allow_html=True)
                    fig_pie = go.Figure(go.Pie(
                        labels=["⚽ Jogo", "🏃 Treino"],
                        values=[carga_jogo_val, carga_treino_val],
                        hole=0.55,
                        marker_colors=["#e63946", "#457b9d"],
                        textinfo="label+percent",
                    ))
                    fig_pie.update_layout(
                        height=320, plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                        margin=dict(t=20),
                        annotations=[dict(text=f"{pct_jogo:.0f}%<br>Jogo", x=0.5, y=0.5,
                                           font_size=18, showarrow=False, font_color="rgba(255,255,255,0.85)")],
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

                with col_bar:
                    st.markdown('<p class="section-title">Distribuição por Dia MD</p>', unsafe_allow_html=True)
                    # Carga por dia MD
                    treino_dia = treino_jog.groupby("Dia MD")[met_jogo].sum().reset_index() if "Dia MD" in treino_jog.columns else pd.DataFrame()
                    jogo_dia   = jogo_jog.groupby("Dia MD")[met_jogo].sum().reset_index() if "Dia MD" in jogo_jog.columns else pd.DataFrame()

                    ordem_dias = ["MD-5","MD-4","MD-3","MD-2","MD-1","MD","MD+1"]

                    if not treino_dia.empty or not jogo_dia.empty:
                        all_dias = pd.DataFrame({"Dia MD": ordem_dias})
                        treino_dia_full = all_dias.merge(treino_dia, on="Dia MD", how="left").fillna(0)
                        jogo_dia_full   = all_dias.merge(jogo_dia,   on="Dia MD", how="left").fillna(0)

                        fig_dias_bar = go.Figure()
                        fig_dias_bar.add_trace(go.Bar(
                            x=treino_dia_full["Dia MD"], y=treino_dia_full[met_jogo],
                            name="Treino", marker_color="#457b9d",
                        ))
                        fig_dias_bar.add_trace(go.Bar(
                            x=jogo_dia_full["Dia MD"], y=jogo_dia_full[met_jogo],
                            name="Jogo", marker_color="#e63946",
                        ))
                        fig_dias_bar.update_layout(
                            barmode="stack", height=320,
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                            font_color="rgba(255,255,255,0.85)", yaxis_title=met_jogo, margin=dict(t=10),
                        )
                        st.plotly_chart(fig_dias_bar, use_container_width=True)

                # Contexto histórico — % jogo ao longo dos microciclos
                st.divider()
                st.markdown('<p class="section-title">📈 Evolução da % de Carga de Jogo ao longo dos Microciclos</p>', unsafe_allow_html=True)

                rows_hist = []
                for mc in sorted(df["Microciclo (Nr)"].dropna().unique()):
                    j_mc = df_jogos[(df_jogos["Microciclo (Nr)"] == mc) & (df_jogos["Jogador"] == jog_jogo)]
                    t_mc = df_treinos[(df_treinos["Microciclo (Nr)"] == mc) & (df_treinos["Jogador"] == jog_jogo)]
                    if j_mc.empty or t_mc.empty:
                        continue
                    cj = j_mc[met_jogo].sum()
                    ct = t_mc[met_jogo].sum()
                    total = cj + ct
                    rows_hist.append({
                        "Microciclo": int(mc),
                        "Carga Jogo": round(cj, 1),
                        "Carga Treino": round(ct, 1),
                        "% Jogo": round(cj / total * 100, 1) if total > 0 else 0,
                    })

                if rows_hist:
                    df_hist = pd.DataFrame(rows_hist)
                    fig_hist_jogo = go.Figure()
                    fig_hist_jogo.add_trace(go.Scatter(
                        x=df_hist["Microciclo"], y=df_hist["% Jogo"],
                        mode="lines+markers+text",
                        text=[f"{v:.0f}%" for v in df_hist["% Jogo"]],
                        textposition="top center",
                        line_color="#e63946", line_width=2, marker_size=8, name="% Jogo",
                    ))
                    fig_hist_jogo.add_hline(y=30, line_dash="dash", line_color="#f39c12",
                                             annotation_text="30% referência")
                    fig_hist_jogo.update_layout(
                        yaxis=dict(title="% Carga de Jogo", range=[0, 100]),
                        xaxis_title="Microciclo",
                        height=320, plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)", margin=dict(t=10),
                    )
                    st.plotly_chart(fig_hist_jogo, use_container_width=True)

            # ── MODO: EQUIPA ─────────────────────────────────────────────────────────
            else:
                st.markdown('<p class="section-title">% Carga de Jogo vs Treino por Jogador — Equipa</p>', unsafe_allow_html=True)

                rows_eq = []
                for jog in sorted(df["Jogador"].dropna().unique()):
                    j = jogos_mc[jogos_mc["Jogador"] == jog]
                    t = treinos_mc[treinos_mc["Jogador"] == jog]
                    if j.empty or t.empty or met_jogo not in j.columns:
                        continue
                    cj = j[met_jogo].sum()
                    ct = t[met_jogo].sum()
                    total = cj + ct
                    pos = j["Posição"].iloc[0] if "Posição" in j.columns else "—"
                    rows_eq.append({
                        "Jogador": jog,
                        "Posição": pos,
                        "Carga Jogo": round(cj, 1),
                        "Carga Treino": round(ct, 1),
                        "Total Semanal": round(total, 1),
                        "% Jogo": round(cj / total * 100, 1) if total > 0 else 0,
                    })

                if not rows_eq:
                    st.warning("Sem dados suficientes para a equipa neste microciclo.")
    
                df_eq = pd.DataFrame(rows_eq).sort_values("% Jogo", ascending=False)

                # KPIs equipa
                k1, k2, k3 = st.columns(3)
                k1.metric("% Jogo Média da Equipa", f"{df_eq['% Jogo'].mean():.1f}%")
                k2.metric("Carga Jogo Média",        f"{df_eq['Carga Jogo'].mean():,.1f}")
                k3.metric("Carga Treino Média",      f"{df_eq['Carga Treino'].mean():,.1f}")

                # Gráfico barras empilhadas
                cores_eq = ["#e74c3c" if v > 40 else "#f39c12" if v > 30 else "#2ecc71" for v in df_eq["% Jogo"]]
                fig_eq = go.Figure()
                fig_eq.add_trace(go.Bar(
                    x=df_eq["Jogador"], y=df_eq["Carga Jogo"],
                    name="⚽ Jogo", marker_color="#e63946",
                ))
                fig_eq.add_trace(go.Bar(
                    x=df_eq["Jogador"], y=df_eq["Carga Treino"],
                    name="🏃 Treino", marker_color="#457b9d",
                ))
                fig_eq.update_layout(
                    barmode="stack", height=380,
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)", yaxis_title=met_jogo,
                    legend=dict(orientation="h", y=1.05), margin=dict(t=30),
                )
                st.plotly_chart(fig_eq, use_container_width=True)

                # % Jogo por jogador
                fig_pct_eq = go.Figure(go.Bar(
                    x=df_eq["Jogador"], y=df_eq["% Jogo"],
                    marker_color=["#e63946" if v > 40 else "#f39c12" if v > 30 else "#2ecc71" for v in df_eq["% Jogo"]],
                    text=[f"{v:.1f}%" for v in df_eq["% Jogo"]],
                    textposition="outside",
                ))
                fig_pct_eq.add_hline(y=30, line_dash="dash", line_color="#f39c12", annotation_text="30% referência")
                fig_pct_eq.update_layout(
                    yaxis=dict(title="% Jogo / Total", range=[0, max(df_eq["% Jogo"]) + 15]),
                    height=340, plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                    showlegend=False, margin=dict(t=20),
                )
                st.plotly_chart(fig_pct_eq, use_container_width=True)

                # Tabela completa
                st.dataframe(df_eq.set_index("Jogador"), use_container_width=True)

                # Conclusões equipa
                st.divider()
                st.markdown('<p class="section-title">🧠 Conclusões</p>', unsafe_allow_html=True)
                alto_jogo  = df_eq[df_eq["% Jogo"] > 40]["Jogador"].tolist()
                medio_jogo = df_eq[df_eq["% Jogo"].between(30, 40)]["Jogador"].tolist()
                baixo_jogo = df_eq[df_eq["% Jogo"] < 30]["Jogador"].tolist()

                if alto_jogo:
                    st.markdown(f"🔴 **Carga de jogo muito elevada** (>40%): {', '.join(alto_jogo)} — estes jogadores fizeram grande parte do esforço semanal no jogo. Atenção à recuperação.")
                if medio_jogo:
                    st.markdown(f"🟡 **Proporção equilibrada** (30-40%): {', '.join(medio_jogo)} — valores dentro do esperado.")
                if baixo_jogo:
                    st.markdown(f"🔵 **Pouca exposição em jogo** (<30%): {', '.join(baixo_jogo)} — baixo volume de jogo relativamente ao treino (lesão, banco, rotação?).")
                st.markdown(f"📊 **Média da equipa**: {df_eq['% Jogo'].mean():.1f}% da carga semanal correspondeu ao jogo.")




        # ═══════════════════════════════════════════════════════════════════════════════
        # VISTA: PERFIL DE REFERÊNCIA INDIVIDUAL (Z-Score pessoal)
        # ═══════════════════════════════════════════════════════════════════════════════

            METS_PERFIL = [
                "Distância Total (m)", "HSR (m)", "Sprint (m)", "Vel. Máx (km/h)",
                "Acc (n)", "Dcc (n)", "PSE Sessão", "Carga Interna",
                "Hooper Index", "Sono (1-5)", "Dor Musc. (1-5)", "Stress (1-5)", "Humor (1-5)",
            ]
            mets_disp = [m for m in METS_PERFIL if m in df.columns]

            tab_p1, tab_p2 = st.tabs(["👤 Análise Individual", "🏟️ Semáforo da Equipa"])

            # ── TAB 1: Individual ────────────────────────────────────────────────────
            with tab_p1:
                col_a, col_b = st.columns(2)
                jog_p = col_a.selectbox("Jogador", sorted(df["Jogador"].dropna().unique()), key="perf_jog")
                n_semanas = col_b.slider("Semanas de histórico como referência", 4, 20, 8, key="perf_sem")

                df_jog_p = df[df["Jogador"] == jog_p].dropna(subset=["Data"]).sort_values("Data").copy()
                if df_jog_p.empty:
                    st.warning("Sem dados para este jogador.")
    
                # Referência = primeiras n_semanas × 7 dias de dados
                data_corte = df_jog_p["Data"].min() + pd.Timedelta(weeks=n_semanas)
                df_ref  = df_jog_p[df_jog_p["Data"] <= data_corte]
                df_recente = df_jog_p[df_jog_p["Data"] > data_corte]

                if df_ref.empty or df_recente.empty:
                    st.warning("Histórico insuficiente. Tenta reduzir o número de semanas de referência.")
                else:
                    st.info(f"📐 Referência baseada em **{len(df_ref)} sessões** ({df_ref['Data'].min().strftime('%d/%m/%y')} – {df_ref['Data'].max().strftime('%d/%m/%y')})")

                    # Calcular perfil de referência
                    perfil_rows = []
                    for met in mets_disp:
                        if df_ref[met].notna().sum() < 3:
                            continue
                        mu  = df_ref[met].mean()
                        sig = df_ref[met].std()
                        ult = df_recente[met].dropna()
                        if ult.empty: continue
                        ult_val = ult.iloc[-1]
                        z = (ult_val - mu) / sig if sig > 0 else 0
                        if z > 2:    estado = "🔴 Muito Acima"; cor = "#e74c3c"
                        elif z > 1:  estado = "🟡 Acima";       cor = "#f39c12"
                        elif z >= -1: estado = "🟢 Normal";      cor = "#2ecc71"
                        elif z >= -2: estado = "🔵 Abaixo";      cor = "#3498db"
                        else:         estado = "🟣 Muito Abaixo"; cor = "#9b59b6"
                        perfil_rows.append({
                            "Métrica": met,
                            "Ref. Média": round(mu, 1),
                            "Ref. ±DP": round(sig, 1),
                            "Último Valor": round(ult_val, 1),
                            "Z-Score": round(z, 2),
                            "Estado": estado,
                            "_cor": cor,
                        })

                    if perfil_rows:
                        df_perf = pd.DataFrame(perfil_rows)

                        # Cards de semáforo
                        st.markdown('<p class="section-title">Semáforo — Última Sessão vs Perfil Pessoal</p>', unsafe_allow_html=True)
                        n_cols = 4
                        cols_p = st.columns(n_cols)
                        for i, row in df_perf.iterrows():
                            cols_p[i % n_cols].markdown(
                                f'<div style="background:{row["_cor"]}22;border:2px solid {row["_cor"]};border-radius:10px;'
                                f'padding:10px;text-align:center;margin:4px">'
                                f'<div style="font-size:0.75rem;font-weight:700;color:#ccc">{row["Métrica"]}</div>'
                                f'<div style="font-size:1.4rem;font-weight:900;color:{row["_cor"]}">{row["Último Valor"]}</div>'
                                f'<div style="font-size:0.7rem;color:#aaa">Ref: {row["Ref. Média"]} ± {row["Ref. ±DP"]}</div>'
                                f'<div style="font-size:0.85rem;color:{row["_cor"]}">{row["Estado"]} (z={row["Z-Score"]})</div>'
                                f'</div>',
                                unsafe_allow_html=True
                            )

                        st.divider()

                        # Gráfico de barras Z-Score
                        st.markdown('<p class="section-title">Z-Score vs Perfil de Referência</p>', unsafe_allow_html=True)
                        fig_perf = go.Figure(go.Bar(
                            y=df_perf["Métrica"],
                            x=df_perf["Z-Score"],
                            orientation="h",
                            marker_color=df_perf["_cor"].tolist(),
                            text=df_perf["Z-Score"].round(2),
                            textposition="outside",
                        ))
                        fig_perf.add_vline(x=0,  line_color="white", line_width=1)
                        fig_perf.add_vline(x=1,  line_dash="dot", line_color="#f39c12", annotation_text="+1σ")
                        fig_perf.add_vline(x=-1, line_dash="dot", line_color="#3498db", annotation_text="-1σ")
                        fig_perf.add_vline(x=2,  line_dash="dash", line_color="#e74c3c", annotation_text="+2σ")
                        fig_perf.add_vline(x=-2, line_dash="dash", line_color="#9b59b6", annotation_text="-2σ")
                        fig_perf.update_layout(
                            height=max(300, len(df_perf)*50),
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                            font_color="rgba(255,255,255,0.85)", xaxis_title="Z-Score", margin=dict(t=10),
                        )
                        st.plotly_chart(fig_perf, use_container_width=True)

                        # Evolução histórica de uma métrica
                        st.divider()
                        st.markdown('<p class="section-title">Evolução Histórica com Bandas de Referência</p>', unsafe_allow_html=True)
                        met_ev = st.selectbox("Métrica", df_perf["Métrica"].tolist(), key="perf_ev")
                        mu_ev  = float(df_perf[df_perf["Métrica"] == met_ev]["Ref. Média"].iloc[0])
                        sig_ev = float(df_perf[df_perf["Métrica"] == met_ev]["Ref. ±DP"].iloc[0])

                        fig_ev = go.Figure()
                        fig_ev.add_hrect(y0=mu_ev-sig_ev, y1=mu_ev+sig_ev,   fillcolor="#2ecc71", opacity=0.08, line_width=0)
                        fig_ev.add_hrect(y0=mu_ev+sig_ev, y1=mu_ev+2*sig_ev, fillcolor="#f39c12", opacity=0.08, line_width=0)
                        fig_ev.add_hrect(y0=mu_ev-2*sig_ev, y1=mu_ev-sig_ev, fillcolor="#3498db", opacity=0.08, line_width=0)
                        fig_ev.add_trace(go.Scatter(
                            x=df_jog_p["Data"], y=df_jog_p[met_ev],
                            mode="lines+markers", line_color="#e63946", line_width=2, marker_size=6,
                            name=met_ev,
                        ))
                        fig_ev.add_hline(y=mu_ev, line_dash="dash", line_color="white", line_width=1, annotation_text="Média ref.")
                        fig_ev.add_hline(y=mu_ev+sig_ev,   line_dash="dot", line_color="#f39c12")
                        fig_ev.add_hline(y=mu_ev-sig_ev,   line_dash="dot", line_color="#3498db")
                        try:
                            fig_ev.add_vline(x=data_corte.timestamp()*1000, line_dash="dash", line_color="#888",
                                              annotation_text="Fim período ref.")
                        except Exception:
                            pass
                        fig_ev.update_layout(
                            height=360, yaxis_title=met_ev,
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                            font_color="rgba(255,255,255,0.85)", margin=dict(t=20), showlegend=False,
                        )
                        st.plotly_chart(fig_ev, use_container_width=True)

                        # Exportar relatório
                        st.divider()
                        linhas_tab = "".join([
                            f'<tr><td>{r["Métrica"]}</td><td>{r["Ref. Média"]} ± {r["Ref. ±DP"]}</td>'
                            f'<td>{r["Último Valor"]}</td><td>{r["Z-Score"]}</td><td>{r["Estado"]}</td></tr>'
                            for _, r in df_perf.iterrows()
                        ])
                        html_perf = gerar_pdf_html(f"""
        <h1>Perfil de Referência — {jog_p}</h1>
        <p>Referência: {df_ref["Data"].min().strftime("%d/%m/%Y")} a {df_ref["Data"].max().strftime("%d/%m/%Y")} ({len(df_ref)} sessões)</p>
        <table><tr><th>Métrica</th><th>Ref. Média ± DP</th><th>Último Valor</th><th>Z-Score</th><th>Estado</th></tr>
        {linhas_tab}</table>
        """, f"Perfil_{jog_p}.html")
                        botao_download_html(html_perf, f"Perfil_{jog_p.replace(' ','_')}.html", f"📥 Exportar Perfil de {jog_p}")

            # ── TAB 2: Semáforo da equipa ─────────────────────────────────────────────
            with tab_p2:
                st.markdown('<p class="section-title">Semáforo de Z-Score Pessoal — Última Sessão vs Perfil Próprio</p>', unsafe_allow_html=True)
                met_eq_p = st.selectbox("Métrica", mets_disp, key="perf_eq_met")
                semanas_ref = st.slider("Semanas de referência", 4, 20, 8, key="perf_eq_sem")

                equipa_perfil = []
                for jog in sorted(df["Jogador"].dropna().unique()):
                    df_j = df[df["Jogador"] == jog].dropna(subset=["Data", met_eq_p]).sort_values("Data")
                    if len(df_j) < 5: continue
                    corte = df_j["Data"].min() + pd.Timedelta(weeks=semanas_ref)
                    ref = df_j[df_j["Data"] <= corte][met_eq_p]
                    rec = df_j[df_j["Data"] > corte][met_eq_p]
                    if ref.empty or rec.empty: continue
                    mu, sig = ref.mean(), ref.std()
                    if sig == 0: continue
                    ult = rec.iloc[-1]
                    z = (ult - mu) / sig
                    if z > 2:     estado, cor = "🔴 Muito Acima", "#e74c3c"
                    elif z > 1:   estado, cor = "🟡 Acima",       "#f39c12"
                    elif z >= -1: estado, cor = "🟢 Normal",      "#2ecc71"
                    elif z >= -2: estado, cor = "🔵 Abaixo",      "#3498db"
                    else:         estado, cor = "🟣 Muito Abaixo","#9b59b6"
                    pos = df_j["Posição"].iloc[-1] if "Posição" in df_j.columns else "—"
                    equipa_perfil.append({"Jogador": jog, "Posição": pos, "Ref. Média": round(mu,1),
                                           "Último": round(ult,1), "Z-Score": round(z,2),
                                           "Estado": estado, "_cor": cor})

                if equipa_perfil:
                    df_ep = pd.DataFrame(equipa_perfil).sort_values("Z-Score", ascending=False)
                    cols_sem = st.columns(min(len(df_ep), 5))
                    for i, (_, row) in enumerate(df_ep.iterrows()):
                        cols_sem[i % 5].markdown(
                            f'<div style="background:{row["_cor"]}22;border:2px solid {row["_cor"]};border-radius:10px;'
                            f'padding:10px;text-align:center;margin:4px">'
                            f'<b style="font-size:0.9rem">{row["Jogador"]}</b><br>'
                            f'<span style="font-size:0.75rem;color:#aaa">{row["Posição"]}</span><br>'
                            f'<b style="font-size:1.3rem;color:{row["_cor"]}">{row["Z-Score"]:+.2f}</b><br>'
                            f'<span style="font-size:0.7rem">{row["Estado"]}</span></div>',
                            unsafe_allow_html=True
                        )

                    st.divider()
                    fig_eq_perf = go.Figure(go.Bar(
                        x=df_ep["Jogador"], y=df_ep["Z-Score"],
                        marker_color=df_ep["_cor"].tolist(),
                        text=df_ep["Z-Score"].round(2), textposition="outside",
                    ))
                    fig_eq_perf.add_hline(y=1,  line_dash="dot", line_color="#f39c12")
                    fig_eq_perf.add_hline(y=-1, line_dash="dot", line_color="#3498db")
                    fig_eq_perf.add_hline(y=0,  line_color="white", line_width=1)
                    fig_eq_perf.update_layout(
                        yaxis_title=f"Z-Score ({met_eq_p})", height=380,
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font_color="rgba(255,255,255,0.85)", margin=dict(t=20), showlegend=False,
                    )
                    st.plotly_chart(fig_eq_perf, use_container_width=True)
                else:
                    st.warning("Dados insuficientes para calcular perfis individuais.")


        # ═══════════════════════════════════════════════════════════════════════════════
        # VISTA: LESÕES & DISPONIBILIDADE
        # ═══════════════════════════════════════════════════════════════════════════════

            # Tentar ler folha de Lesões
            try:
                df_les = pd.read_excel(excel_path, sheet_name="Lesões", engine="openpyxl")
                df_les.columns = [str(c).strip() for c in df_les.columns]
                tem_folha_lesoes = True
            except Exception:
                tem_folha_lesoes = False
                df_les = pd.DataFrame()

            if not tem_folha_lesoes:
                st.warning("""
        ### ⚠️ Folha 'Lesões' não encontrada no Excel

        Para usar esta funcionalidade, adiciona uma folha chamada **Lesões** ao teu ficheiro Excel com estas colunas:

        | Jogador | Data Lesão | Data Retorno | Tipo de Lesão | Zona Corporal | Diagnóstico | Dias de Paragem | Estado |
        |---|---|---|---|---|---|---|---|
        | Paulino | 12/01/2025 | 25/01/2025 | Muscular | Isquiotibial | Elongação grau I | 13 | Recuperado |
        | ... | | | | | | | Ativo |

        O campo **Estado** deve ser: `Ativo` (ainda lesionado) ou `Recuperado`.

        Depois de criar a folha, clica em **🔄 Atualizar Dados**.
                """)

                # Mesmo sem folha de lesões, mostrar análise de ausências (sessões em falta)
                st.divider()
                st.markdown('<p class="section-title">📊 Análise de Participação nos Treinos</p>', unsafe_allow_html=True)
                st.caption("Jogadores com menos sessões que a média podem indicar períodos de indisponibilidade")

                if "Microciclo (Nr)" in df.columns:
                    mc_disp = sorted(df["Microciclo (Nr)"].dropna().unique(), reverse=True)
                    mc_les = st.selectbox("Microciclo a analisar", mc_disp, key="les_mc")
                    df_mc_les = df[df["Microciclo (Nr)"] == mc_les]
                    todos_jogs = sorted(df["Jogador"].dropna().unique())

                    participacao = []
                    max_sess = df_mc_les.groupby("Jogador").size().max() if not df_mc_les.empty else 0
                    for jog in todos_jogs:
                        sess = len(df_mc_les[df_mc_les["Jogador"] == jog])
                        pos  = df[df["Jogador"] == jog]["Posição"].iloc[-1] if "Posição" in df.columns and not df[df["Jogador"] == jog].empty else "—"
                        pct  = sess / max_sess * 100 if max_sess > 0 else 0
                        participacao.append({"Jogador": jog, "Posição": pos, "Sessões": sess,
                                              "% Participação": round(pct, 0),
                                              "Estado": "⚠️ Ausente/Indisponível" if pct < 50 else "✅ Presente"})

                    df_part = pd.DataFrame(participacao).sort_values("% Participação")
                    fig_part = go.Figure(go.Bar(
                        y=df_part["Jogador"], x=df_part["% Participação"],
                        orientation="h",
                        marker_color=["#e74c3c" if v < 50 else "#f39c12" if v < 80 else "#2ecc71"
                                       for v in df_part["% Participação"]],
                        text=[f"{int(v)}%" for v in df_part["% Participação"]],
                        textposition="outside",
                    ))
                    fig_part.add_vline(x=80, line_dash="dash", line_color="#f39c12", annotation_text="80%")
                    fig_part.add_vline(x=50, line_dash="dash", line_color="#e74c3c", annotation_text="50%")
                    fig_part.update_layout(
                        xaxis=dict(range=[0, 115], title="% Participação"),
                        height=max(300, len(df_part)*40),
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font_color="rgba(255,255,255,0.85)", margin=dict(t=10),
                    )
                    st.plotly_chart(fig_part, use_container_width=True)
                    ausentes = df_part[df_part["% Participação"] < 50]["Jogador"].tolist()
                    if ausentes:
                        st.warning(f"⚠️ **Possível indisponibilidade** no MC {int(mc_les)}: {', '.join(ausentes)} (menos de 50% das sessões)")

            # ── Com folha de Lesões ────────────────────────────────────────────────────
            # Normalizar colunas esperadas
            col_jog    = next((c for c in df_les.columns if "jogador" in c.lower()), None)
            col_data_l = next((c for c in df_les.columns if "data" in c.lower() and "lesão" in c.lower()), None) or                  next((c for c in df_les.columns if "data" in c.lower() and "inicio" in c.lower()), None)
            col_retorno = next((c for c in df_les.columns if "retorno" in c.lower() or "regresso" in c.lower()), None)
            col_dias    = next((c for c in df_les.columns if "dias" in c.lower()), None)
            col_tipo    = next((c for c in df_les.columns if "tipo" in c.lower()), None)
            col_zona    = next((c for c in df_les.columns if "zona" in c.lower() or "local" in c.lower()), None)
            col_estado  = next((c for c in df_les.columns if "estado" in c.lower() or "situação" in c.lower()), None)

            if col_jog is None:
                st.error("Coluna 'Jogador' não encontrada na folha Lesões.")

            if col_data_l:
                df_les[col_data_l] = pd.to_datetime(df_les[col_data_l], errors="coerce")
            if col_retorno:
                df_les[col_retorno] = pd.to_datetime(df_les[col_retorno], errors="coerce")

            tab_l1, tab_l2, tab_l3 = st.tabs(["📋 Registo de Lesões", "📈 Correlação com Carga", "📊 Epidemiologia"])

            with tab_l1:
                # Lesões ativas
                st.markdown('<p class="section-title">🩹 Lesões Ativas</p>', unsafe_allow_html=True)
                if col_estado:
                    ativas = df_les[df_les[col_estado].astype(str).str.lower().isin(["ativo","activo","sim","yes","1","true","ativa","activa"])]
                else:
                    ativas = df_les[df_les[col_retorno].isna()] if col_retorno else df_les

                if not ativas.empty:
                    for _, row in ativas.iterrows():
                        jog = row[col_jog]
                        tipo = row[col_tipo] if col_tipo else "—"
                        zona = row[col_zona] if col_zona else "—"
                        dias = row[col_dias] if col_dias else "—"
                        data_l = row[col_data_l].strftime("%d/%m/%Y") if col_data_l and pd.notna(row[col_data_l]) else "—"
                        st.markdown(
                            f'<div style="background:#7b1d1d33;border-left:4px solid #e74c3c;border-radius:8px;padding:12px;margin:6px 0">'
                            f'🩹 <b>{jog}</b> — {tipo} ({zona}) · desde {data_l} · {dias} dias de paragem'
                            f'</div>', unsafe_allow_html=True
                        )
                else:
                    st.success("✅ Sem lesões ativas no momento.")

                st.divider()
                st.markdown('<p class="section-title">📋 Histórico Completo</p>', unsafe_allow_html=True)
                st.dataframe(df_les, use_container_width=True)

                # Exportar
                linhas_les = "".join([
                    f'<tr>{"".join(f"<td>{row[c]}</td>" for c in df_les.columns)}</tr>'
                    for _, row in df_les.iterrows()
                ])
                headers_les = "".join([f"<th>{c}</th>" for c in df_les.columns])
                html_les = gerar_pdf_html(f"""
        <h1>Relatório de Lesões</h1>
        <table><tr>{headers_les}</tr>{linhas_les}</table>
        """, "Relatorio_Lesoes.html")
                botao_download_html(html_les, "Relatorio_Lesoes.html", "📥 Exportar Registo de Lesões")

            with tab_l2:
                st.markdown('<p class="section-title">⚡ Carga nas 4 Semanas Antes da Lesão</p>', unsafe_allow_html=True)
                if col_data_l is None:
                    st.warning("Coluna de data de lesão não encontrada.")
                else:
                    lesoes_com_data = df_les.dropna(subset=[col_data_l])
                    if lesoes_com_data.empty:
                        st.info("Sem lesões com data registada.")
                    else:
                        jog_sel_les = st.selectbox("Jogador", lesoes_com_data[col_jog].unique(), key="les_jog")
                        lesoes_jog = lesoes_com_data[lesoes_com_data[col_jog] == jog_sel_les]
                        data_les_sel = st.selectbox("Lesão (data)", lesoes_jog[col_data_l].dt.strftime("%d/%m/%Y").tolist(), key="les_data")
                        data_les_dt = pd.to_datetime(data_les_sel, format="%d/%m/%Y")

                        df_antes = df[
                            (df["Jogador"] == jog_sel_les) &
                            (df["Data"] >= data_les_dt - pd.Timedelta(weeks=4)) &
                            (df["Data"] < data_les_dt)
                        ].sort_values("Data")

                        if df_antes.empty:
                            st.info("Sem dados de carga nas 4 semanas anteriores à lesão.")
                        else:
                            fig_les_carga = go.Figure()
                            if "Carga Interna" in df_antes.columns:
                                fig_les_carga.add_trace(go.Bar(
                                    x=df_antes["Data"], y=df_antes["Carga Interna"],
                                    name="Carga Interna", marker_color="#e63946",
                                ))
                            if "ACWR" not in df_antes.columns:
                                df_jog_acwr = calcular_acwr(df[df["Jogador"] == jog_sel_les], jog_sel_les)
                                df_jog_acwr = df_jog_acwr[
                                    (df_jog_acwr["Data"] >= data_les_dt - pd.Timedelta(weeks=4)) &
                                    (df_jog_acwr["Data"] < data_les_dt)
                                ]
                                if "ACWR" in df_jog_acwr.columns:
                                    fig_les_carga.add_trace(go.Scatter(
                                        x=df_jog_acwr["Data"], y=df_jog_acwr["ACWR"] * 100,
                                        mode="lines+markers", name="ACWR ×100", line_color="#f39c12",
                                        yaxis="y2",
                                    ))
                            fig_les_carga.add_vline(x=data_les_dt, line_dash="dash", line_color="#e74c3c",
                                                     annotation_text="Lesão", annotation_position="top right")
                            fig_les_carga.update_layout(
                                height=360,
                                yaxis=dict(title="Carga Interna"),
                                yaxis2=dict(title="ACWR ×100", overlaying="y", side="right"),
                                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                font_color="rgba(255,255,255,0.85)", margin=dict(t=30),
                            )
                            st.plotly_chart(fig_les_carga, use_container_width=True)

            with tab_l3:
                st.markdown('<p class="section-title">📊 Distribuição de Lesões por Tipo e Zona</p>', unsafe_allow_html=True)

                c1_e, c2_e = st.columns(2)
                if col_tipo and not df_les[col_tipo].isna().all():
                    with c1_e:
                        tipo_count = df_les[col_tipo].value_counts().reset_index()
                        tipo_count.columns = ["Tipo", "Nº"]
                        fig_tipo = px.pie(tipo_count, names="Tipo", values="Nº", hole=0.4,
                                           color_discrete_sequence=px.colors.qualitative.Bold)
                        fig_tipo.update_layout(height=300, plot_bgcolor="rgba(0,0,0,0)",
                                                paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)", margin=dict(t=10))
                        st.plotly_chart(fig_tipo, use_container_width=True)

                if col_zona and not df_les[col_zona].isna().all():
                    with c2_e:
                        zona_count = df_les[col_zona].value_counts().reset_index()
                        zona_count.columns = ["Zona", "Nº"]
                        fig_zona = px.bar(zona_count, x="Nº", y="Zona", orientation="h",
                                           color="Nº", color_continuous_scale="Reds")
                        fig_zona.update_layout(height=300, plot_bgcolor="rgba(0,0,0,0)",
                                                paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                                                coloraxis_showscale=False, margin=dict(t=10))
                        st.plotly_chart(fig_zona, use_container_width=True)

                if col_dias and not df_les[col_dias].isna().all():
                    st.markdown('<p class="section-title">Dias de Paragem por Jogador</p>', unsafe_allow_html=True)
                    dias_jog = df_les.groupby(col_jog)[col_dias].sum().sort_values(ascending=False).reset_index()
                    dias_jog.columns = ["Jogador", "Total Dias"]
                    fig_dias_les = px.bar(dias_jog, x="Jogador", y="Total Dias",
                                           color="Total Dias", color_continuous_scale="Reds",
                                           text="Total Dias")
                    fig_dias_les.update_layout(height=320, plot_bgcolor="rgba(0,0,0,0)",
                                                paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                                                coloraxis_showscale=False, margin=dict(t=10))
                    st.plotly_chart(fig_dias_les, use_container_width=True)




        # ═══════════════════════════════════════════════════════════════════════════════
        # VISTA: TREINO VS JOGO — % MÉTRICAS GPS
        # ═══════════════════════════════════════════════════════════════════════════════

    with tab_plan[1]:

            METS_GPS = [
                "Distância Total (m)", "HSR (m)", "Sprint (m)", "Acc (n)", "Dcc (n)",
                "Carga Interna", "PSE Sessão",
            ]
            mets_gps_disp = [m for m in METS_GPS if m in df.columns]

            if "Tipo" not in df.columns:
                st.error("Coluna 'Tipo' não encontrada. Certifica-te que o Excel tem a coluna 'Tipo' com 'Treino' e 'Jogo'.")

            df_jogos_all   = df[df["Tipo"].str.strip().str.lower() == "jogo"].copy()
            df_treinos_all = df[df["Tipo"].str.strip().str.lower() == "treino"].copy()

            if df_jogos_all.empty:
                st.warning("Sem registos com Tipo = 'Jogo' encontrados.")

            # ── Filtros ───────────────────────────────────────────────────────────────
            col_f1, col_f2, col_f3 = st.columns(3)
            mc_tvj   = col_f1.selectbox("Microciclo", sorted(df["Microciclo (Nr)"].dropna().unique(), reverse=True), key="tvj_mc")
            modo_tvj = col_f2.radio("Modo", ["Por Jogador", "Equipa (média)"], key="tvj_modo")
            referencia_tvj = col_f3.radio("Referência de jogo", ["Média de todos os jogos", "Top 5 jogos mais exigentes", "Último jogo"], key="tvj_ref")

            st.divider()

            # Calcular referência de jogo
            def media_jogos(df_j, met, jogador=None):
                """Calcula a referência de jogo conforme opção selecionada."""
                sub = df_j if jogador is None else df_j[df_j["Jogador"] == jogador]
                if sub.empty or met not in sub.columns:
                    return np.nan
                if referencia_tvj == "Último jogo":
                    sub = sub.sort_values("Data").tail(1)
                elif referencia_tvj == "Top 5 jogos mais exigentes":
                    # Top 5 baseado na métrica selecionada (mais exigente = maior valor)
                    sub = sub.nlargest(5, met) if len(sub) >= 5 else sub
                # Média de todos os jogos: usa sub completo
                return sub[met].mean()

            df_treinos_mc = df_treinos_all[df_treinos_all["Microciclo (Nr)"] == mc_tvj]

            if df_treinos_mc.empty:
                st.warning(f"Sem sessões de treino no Microciclo {int(mc_tvj)}.")

            # ── MODO EQUIPA ───────────────────────────────────────────────────────────
            if modo_tvj == "Equipa (média)":

                # Média de cada métrica por dia MD nos treinos
                dias_md_ordem = ["MD-5","MD-4","MD-3","MD-2","MD-1","MD+1","MD+2"]
                dias_presentes = [d for d in dias_md_ordem if d in df_treinos_mc["Dia MD"].values]                          if "Dia MD" in df_treinos_mc.columns else []

                # ── Cards de % total do microciclo vs jogo ────────────────────────────
                st.markdown('<p class="section-title">% Total do Microciclo vs Média de Jogos</p>', unsafe_allow_html=True)

                n_cols = len(mets_gps_disp)
                cols_cards = st.columns(n_cols)
                for i, met in enumerate(mets_gps_disp):
                    # Média por sessão de treino (para comparar com um jogo individual)
                    media_treino = df_treinos_mc.groupby("Jogador")[met].mean().mean()
                    total_treino = df_treinos_mc[met].sum()
                    ref_jogo     = media_jogos(df_jogos_all, met)
                    if pd.isna(ref_jogo) or ref_jogo == 0:
                        pct = None
                    else:
                        pct = media_treino / ref_jogo * 100

                    if pct is None:
                        cor, emoji = "#555", "❓"
                    elif pct >= 150: cor, emoji = "#e74c3c", "🔴"
                    elif pct >= 100: cor, emoji = "#f39c12", "🟡"
                    elif pct >= 70:  cor, emoji = "#2ecc71", "🟢"
                    else:            cor, emoji = "#3498db", "🔵"

                    label = met.replace(" (m)","").replace(" (n)","")
                    # PSE: só faz sentido como média por sessão (não soma)
                    is_pse = met == "PSE Sessão"
                    agg_label = "Média/sessão" if is_pse else "Média treino"
                    cols_cards[i].markdown(
                        f'<div style="background:{cor}22;border:2px solid {cor};border-radius:12px;'
                        f'padding:14px;text-align:center;margin:4px">'
                        f'<div style="font-size:0.75rem;font-weight:700;color:#ccc;margin-bottom:4px">{label}</div>'
                        f'<div style="font-size:2rem;font-weight:900;color:{cor}">'
                        f'{"—" if pct is None else f"{pct:.0f}%"}</div>'
                        f'<div style="font-size:0.65rem;color:#aaa">{agg_label} / {"último jogo" if referencia_tvj=="Último jogo" else "top 5" if "Top 5" in referencia_tvj else "média jogos"}</div>'
                        f'<div style="font-size:0.75rem;color:#eee;margin-top:4px">'
                        f'Treino: {media_treino:,.1f if is_pse else f"{media_treino:,.0f}"} | Ref.: {ref_jogo:,.1f if is_pse else f"{ref_jogo:,.0f}"}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                st.divider()

                # ── Gráfico por Dia MD — todas as métricas ─────────────────────────────
                if dias_presentes:
                    st.markdown('<p class="section-title">% por Dia do Microciclo vs Média de Jogos</p>', unsafe_allow_html=True)
                    met_sel = st.selectbox("Métrica", mets_gps_disp, key="tvj_eq_met")

                    ref_val = media_jogos(df_jogos_all, met_sel)
                    dias_vals, dias_pcts, dias_abs = [], [], []

                    for dia in dias_presentes:
                        sub_dia = df_treinos_mc[df_treinos_mc["Dia MD"] == dia]
                        # Média por jogador primeiro, depois média do grupo
                        val = sub_dia.groupby("Jogador")[met_sel].mean().mean()
                        dias_vals.append(dia)
                        dias_abs.append(round(val, 1))
                        dias_pcts.append(round(val / ref_val * 100, 1) if (ref_val and ref_val > 0) else 0)

                    cores_dias = []
                    for p in dias_pcts:
                        if p >= 300:   cores_dias.append("#e74c3c")
                        elif p >= 200: cores_dias.append("#f39c12")
                        elif p >= 100: cores_dias.append("#2ecc71")
                        else:          cores_dias.append("#3498db")

                    fig_dias_tvj = go.Figure()
                    fig_dias_tvj.add_trace(go.Bar(
                        x=dias_vals, y=dias_pcts,
                        marker_color=cores_dias,
                        text=[f"{p:.0f}%" for p in dias_pcts],
                        textposition="outside",
                        name="% vs Jogo",
                    ))
                    fig_dias_tvj.add_hline(y=100, line_dash="dash", line_color="#2ecc71",
                                            annotation_text="100% = equivalente ao jogo")
                    fig_dias_tvj.add_hline(y=200, line_dash="dot", line_color="#f39c12",
                                            annotation_text="200%")
                    fig_dias_tvj.update_layout(
                        yaxis=dict(title="% vs Média de Jogos", range=[0, max(dias_pcts + [110]) * 1.15]),
                        xaxis_title="Dia MD", height=380,
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font_color="rgba(255,255,255,0.85)", showlegend=False, margin=dict(t=20),
                    )
                    st.plotly_chart(fig_dias_tvj, use_container_width=True)

                    # Tabela dia a dia
                    df_tabela_dias = pd.DataFrame({
                        "Dia MD": dias_vals,
                        met_sel: dias_abs,
                        "Ref. Jogo": [round(ref_val, 1)] * len(dias_vals),
                        "% vs Jogo": [f"{p:.0f}%" for p in dias_pcts],
                    })
                    st.dataframe(df_tabela_dias.set_index("Dia MD"), use_container_width=True)

                st.divider()

                # ── Radar — todas as métricas por dia MD ─────────────────────────────
                if dias_presentes and len(dias_presentes) >= 2:
                    st.markdown('<p class="section-title">Radar — % vs Jogo por Dia MD (todas as métricas)</p>', unsafe_allow_html=True)
                    dias_radar_sel = st.multiselect("Dias a comparar", dias_presentes,
                                                     default=dias_presentes[:min(3, len(dias_presentes))],
                                                     key="tvj_radar_dias")
                    fig_radar_tvj = go.Figure()
                    cores_r = ["#e63946","#457b9d","#2ecc71","#f39c12","#9b59b6","#1abc9c"]
                    labels_r = [m.replace(" (m)","").replace(" (n)","") for m in mets_gps_disp]

                    for k, dia in enumerate(dias_radar_sel):
                        sub_dia = df_treinos_mc[df_treinos_mc["Dia MD"] == dia]
                        vals_r = []
                        for met in mets_gps_disp:
                            ref = media_jogos(df_jogos_all, met)
                            val = sub_dia.groupby("Jogador")[met].mean().mean()
                            vals_r.append(round(val / ref * 100, 1) if (ref and ref > 0 and pd.notna(val)) else 0)
                        vals_r_closed = vals_r + [vals_r[0]]
                        labels_closed = labels_r + [labels_r[0]]
                        fig_radar_tvj.add_trace(go.Scatterpolar(
                            r=vals_r_closed, theta=labels_closed,
                            fill="toself", name=dia,
                            line_color=cores_r[k % len(cores_r)], opacity=0.75,
                        ))
                    # Jogo = 100% linha de referência
                    fig_radar_tvj.add_trace(go.Scatterpolar(
                        r=[100] * (len(labels_r) + 1), theta=labels_r + [labels_r[0]],
                        mode="lines", name="⚽ Jogo (100%)",
                        line=dict(color="white", dash="dash", width=2),
                    ))
                    fig_radar_tvj.update_layout(
                        polar=dict(radialaxis=dict(visible=True, ticksuffix="%")),
                        height=460, plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                    )
                    st.plotly_chart(fig_radar_tvj, use_container_width=True)

                st.divider()

                # ── Heatmap — dia MD × métrica ────────────────────────────────────────
                st.markdown('<p class="section-title">Heatmap — % vs Jogo (Dia MD × Métrica)</p>', unsafe_allow_html=True)
                if dias_presentes:
                    heat_data, heat_text = [], []
                    for dia in dias_presentes:
                        row_vals, row_text = [], []
                        sub_dia = df_treinos_mc[df_treinos_mc["Dia MD"] == dia]
                        for met in mets_gps_disp:
                            ref = media_jogos(df_jogos_all, met)
                            val = sub_dia.groupby("Jogador")[met].mean().mean()
                            p = round(val / ref * 100, 0) if (ref and ref > 0 and pd.notna(val)) else 0
                            row_vals.append(p)
                            row_text.append(f"{p:.0f}%")
                        heat_data.append(row_vals)
                        heat_text.append(row_text)

                    labels_heat = [m.replace(" (m)","").replace(" (n)","") for m in mets_gps_disp]
                    fig_heat_tvj = go.Figure(go.Heatmap(
                        z=heat_data, x=labels_heat, y=dias_presentes,
                        text=heat_text, texttemplate="%{text}",
                        colorscale="RdYlGn", zmid=100,
                        colorbar=dict(title="% Jogo", ticksuffix="%"),
                    ))
                    fig_heat_tvj.update_layout(
                        height=max(250, len(dias_presentes)*65),
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font_color="rgba(255,255,255,0.85)", margin=dict(t=10),
                    )
                    st.plotly_chart(fig_heat_tvj, use_container_width=True)

                # ── Exportar ──────────────────────────────────────────────────────────
                st.divider()
                linhas_export = ""
                for met in mets_gps_disp:
                    total_t = df_treinos_mc[met].sum()
                    ref_j   = media_jogos(df_jogos_all, met)
                    pct_e   = f"{total_t/ref_j*100:.0f}%" if (ref_j and ref_j > 0) else "—"
                    linhas_export += f"<tr><td>{met}</td><td>{total_t:,.0f}</td><td>{ref_j:,.0f}</td><td><b>{pct_e}</b></td></tr>"
                html_tvj = gerar_pdf_html(f"""
        <h1>Treino vs Jogo — MC {int(mc_tvj)}</h1>
        <p><b>Referência:</b> {referencia_tvj}</p>
        <table><tr><th>Métrica</th><th>Total Treino</th><th>Ref. Jogo</th><th>% vs Jogo</th></tr>
        {linhas_export}</table>
        """, f"TreinoVsJogo_MC{int(mc_tvj)}.html")
                botao_download_html(html_tvj, f"TreinoVsJogo_MC{int(mc_tvj)}.html", "📥 Exportar Relatório (PDF)")

            # ── MODO JOGADOR ──────────────────────────────────────────────────────────
            else:
                jog_tvj = st.selectbox("Jogador", sorted(df["Jogador"].dropna().unique()), key="tvj_jog")

                df_t_jog = df_treinos_mc[df_treinos_mc["Jogador"] == jog_tvj]
                df_j_jog = df_jogos_all[df_jogos_all["Jogador"] == jog_tvj]

                if df_t_jog.empty:
                    st.warning(f"Sem treinos para {jog_tvj} no MC {int(mc_tvj)}.")
    
                # Cards
                st.markdown('<p class="section-title">% Total do Microciclo vs Média de Jogos</p>', unsafe_allow_html=True)
                cols_jog = st.columns(len(mets_gps_disp))
                for i, met in enumerate(mets_gps_disp):
                    total_t = df_t_jog[met].sum()
                    ref_j   = media_jogos(df_j_jog, met)
                    pct     = total_t / ref_j * 100 if (ref_j and ref_j > 0) else None

                    if pct is None: cor, emoji = "#555", "❓"
                    elif pct >= 300: cor, emoji = "#e74c3c", "🔴"
                    elif pct >= 200: cor, emoji = "#f39c12", "🟡"
                    elif pct >= 100: cor, emoji = "#2ecc71", "🟢"
                    else:            cor, emoji = "#3498db", "🔵"

                    label = met.replace(" (m)","").replace(" (n)","")
                    cols_jog[i].markdown(
                        f'<div style="background:{cor}22;border:2px solid {cor};border-radius:12px;'
                        f'padding:14px;text-align:center;margin:4px">'
                        f'<div style="font-size:0.75rem;font-weight:700;color:#ccc">{label}</div>'
                        f'<div style="font-size:2rem;font-weight:900;color:{cor}">'
                        f'{"—" if pct is None else f"{pct:.0f}%"}</div>'
                        f'<div style="font-size:0.7rem;color:#aaa">treino / jogo</div>'
                        f'<div style="font-size:0.75rem;color:#eee;margin-top:2px">'
                        f'T: {total_t:,.0f} | J: {ref_j:,.0f}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                st.divider()

                # Por Dia MD
                if "Dia MD" in df_t_jog.columns:
                    st.markdown('<p class="section-title">% por Dia do Microciclo</p>', unsafe_allow_html=True)
                    met_jog_sel = st.selectbox("Métrica", mets_gps_disp, key="tvj_jog_met")
                    ref_jog_val = media_jogos(df_j_jog, met_jog_sel)

                    dias_jog_ord = ["MD-5","MD-4","MD-3","MD-2","MD-1","MD+1","MD+2"]
                    dias_jog_pres = [d for d in dias_jog_ord if d in df_t_jog["Dia MD"].values]

                    pcts_jog, vals_jog = [], []
                    for dia in dias_jog_pres:
                        val = df_t_jog[df_t_jog["Dia MD"] == dia][met_jog_sel].mean()
                        vals_jog.append(round(val, 1))
                        pcts_jog.append(round(val / ref_jog_val * 100, 1) if (ref_jog_val and ref_jog_val > 0) else 0)

                    cores_jog_dias = ["#e74c3c" if p>=300 else "#f39c12" if p>=200 else "#2ecc71" if p>=100 else "#3498db" for p in pcts_jog]

                    fig_jog_dias = go.Figure(go.Bar(
                        x=dias_jog_pres, y=pcts_jog,
                        marker_color=cores_jog_dias,
                        text=[f"{p:.0f}%" for p in pcts_jog],
                        textposition="outside",
                    ))
                    fig_jog_dias.add_hline(y=100, line_dash="dash", line_color="#2ecc71",
                                            annotation_text="100% = equivalente ao jogo")
                    fig_jog_dias.update_layout(
                        yaxis=dict(title="% vs Jogo", range=[0, max(pcts_jog + [110]) * 1.15]),
                        height=360, plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                        showlegend=False, margin=dict(t=20),
                    )
                    st.plotly_chart(fig_jog_dias, use_container_width=True)

                # Comparação entre jogadores da mesma posição
                st.divider()
                st.markdown('<p class="section-title">Comparação com Jogadores da Mesma Posição</p>', unsafe_allow_html=True)
                met_pos_tvj = st.selectbox("Métrica", mets_gps_disp, key="tvj_pos_met")

                pos_jog_tvj = df[df["Jogador"] == jog_tvj]["Posição"].iloc[-1] if "Posição" in df.columns else None
                if pos_jog_tvj:
                    jogs_pos = df[df["Posição"] == pos_jog_tvj]["Jogador"].dropna().unique()
                    rows_pos_tvj = []
                    for jog_p in jogs_pos:
                        t_p = df_treinos_mc[df_treinos_mc["Jogador"] == jog_p]
                        j_p = df_jogos_all[df_jogos_all["Jogador"] == jog_p]
                        if t_p.empty: continue
                        total_p = t_p[met_pos_tvj].sum()
                        ref_p   = media_jogos(j_p, met_pos_tvj)
                        pct_p   = total_p / ref_p * 100 if (ref_p and ref_p > 0) else None
                        rows_pos_tvj.append({"Jogador": jog_p, met_pos_tvj: round(total_p,1),
                                              "Ref. Jogo": round(ref_p,1) if ref_p else 0,
                                              "% vs Jogo": round(pct_p,1) if pct_p else 0})

                    if rows_pos_tvj:
                        df_pos_tvj = pd.DataFrame(rows_pos_tvj).sort_values("% vs Jogo", ascending=True)
                        cores_pos_tvj = ["#e74c3c" if p>=300 else "#f39c12" if p>=200 else "#2ecc71" if p>=100 else "#3498db"
                                          for p in df_pos_tvj["% vs Jogo"]]
                        fig_pos_tvj = go.Figure(go.Bar(
                            y=df_pos_tvj["Jogador"], x=df_pos_tvj["% vs Jogo"],
                            orientation="h", marker_color=cores_pos_tvj,
                            text=[f"{p:.0f}%" for p in df_pos_tvj["% vs Jogo"]],
                            textposition="outside",
                        ))
                        fig_pos_tvj.add_vline(x=100, line_dash="dash", line_color="#2ecc71",
                                               annotation_text="100% = jogo")
                        fig_pos_tvj.update_layout(
                            xaxis_title="% vs Média de Jogos", height=max(250, len(df_pos_tvj)*50),
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                            font_color="rgba(255,255,255,0.85)", showlegend=False, margin=dict(t=10),
                        )
                        # Destaque o jogador selecionado
                        idx_jog = df_pos_tvj["Jogador"].tolist().index(jog_tvj) if jog_tvj in df_pos_tvj["Jogador"].tolist() else -1
                        if idx_jog >= 0:
                            cores_pos_tvj[idx_jog] = "#e63946"
                        st.plotly_chart(fig_pos_tvj, use_container_width=True)




        # ═══════════════════════════════════════════════════════════════════════════════
        # VISTA: MONOTONIA & STRAIN (FOSTER)
        # ═══════════════════════════════════════════════════════════════════════════════

    with tab_plan[2]:
        # Interpretação no topo
        st.info("📚 **Referência:** Borresen & Lambert (2009) · Clemente et al. (2014) — Distância: 70–90% do jogo/sessão · HSR: 30–60% · Sprint: 15–40% · CI: 60–90%")

        # ════════════════════════════════════════════════════════════════════
        # PLANEADO VS REALIZADO — Carga semanal como % do jogo de referência
        # ════════════════════════════════════════════════════════════════════
        st.markdown("""
        **Lógica:** defines a carga semanal planeada como percentagem de um jogo de referência.
        Por exemplo: CI = 300%, HSR = 250%, Sprint = 100%, Acc/Dcc = 350%.
        Compara depois com o que foi realmente executado no microciclo.
        """)
        st.caption("Baseado na lógica de periodização em relação à exigência do jogo (Borresen & Lambert, 2009)")

        # Planeado vs Realizado — apenas métricas de carga externa relevantes
        METS_PVR_FIXED = ["Carga Interna", "Distância Total (m)", "HSR (m)",
                           "Sprint (m)", "Acc (n)", "Dcc (n)"]
        mets_pvr_disp = [m for m in METS_PVR_FIXED if m in df.columns and df[m].notna().any()]
        # Se nenhuma das fixas existir, usar todas as numéricas como fallback
        if not mets_pvr_disp:
            mets_pvr_disp = get_mets_gps(df_treinos_pvr_all if "df_treinos_pvr_all" in dir() else df)

        if "Tipo" not in df.columns or "Microciclo (Nr)" not in df.columns:
            st.error("Colunas 'Tipo' e 'Microciclo (Nr)' necessárias.")
    
        if len(mets_pvr_disp) == 0:
            st.error("Nenhuma das métricas GPS encontrada no Excel.")
    
        # Separar jogos e treinos
        df_jogos_pvr   = df[df["Tipo"].str.strip().str.lower() == "jogo"].copy() if "Tipo" in df.columns else pd.DataFrame()
        df_treinos_pvr_all = df[df["Tipo"].str.strip().str.lower() == "treino"].copy() if "Tipo" in df.columns else df

        col_p1, col_p2, col_p3 = st.columns(3)
        mcs_pvr = sorted(df["Microciclo (Nr)"].dropna().unique(), reverse=True)
        mc_pvr = col_p1.selectbox("Microciclo a analisar", mcs_pvr, key="pvr_mc")

        ref_pvr = col_p2.radio(
            "Jogo de referência",
            ["Média de todos os jogos", "Top 5 jogos mais exigentes", "Último jogo"],
            key="pvr_ref_jogo"
        )

        df_mc_treinos = df_treinos_pvr_all[df_treinos_pvr_all["Microciclo (Nr)"] == mc_pvr]

        if df_mc_treinos.empty:
            st.warning(f"Sem treinos no Microciclo {int(mc_pvr)}.")
    
        # ── Calcular referência do jogo ───────────────────────────────────
        def get_ref_jogo_pvr(met):
            if df_jogos_pvr.empty or met not in df_jogos_pvr.columns:
                return np.nan
            if ref_pvr == "Último jogo":
                sub = df_jogos_pvr.sort_values("Data").tail(1) if "Data" in df_jogos_pvr.columns else df_jogos_pvr
            elif ref_pvr == "Top 5 jogos mais exigentes":
                sub = df_jogos_pvr.nlargest(5, met) if len(df_jogos_pvr) >= 5 else df_jogos_pvr
            else:
                sub = df_jogos_pvr
            return sub[met].mean()

        # ── Totais reais do microciclo (soma por jogador, depois média) ───
        def get_real_mc(met):
            """Soma total do microciclo por jogador (média do grupo)."""
            if met not in df_mc_treinos.columns:
                return np.nan
            if met == "PSE Sessão":
                # PSE: média por sessão, não soma
                return df_mc_treinos[met].mean()
            return df_mc_treinos.groupby("Jogador")[met].sum().mean()

        st.divider()
        st.markdown('<p class="section-title">🎯 Definir Carga Planeada (% do Jogo de Referência)</p>', unsafe_allow_html=True)
        st.caption("Define a percentagem-alvo para cada métrica. Compara depois com o realizado.")

        # Cards de input — um por métrica
        cols_plan = st.columns(len(mets_pvr_disp))
        planeado_pct = {}
        defaults_pct = {
            "Carga Interna": 300.0, "Distância Total (m)": 280.0,
            "HSR (m)": 250.0, "Sprint (m)": 100.0,
            "Acc (n)": 350.0, "Dcc (n)": 350.0,
        }

        for i, met in enumerate(mets_pvr_disp):
            ref_val = get_ref_jogo_pvr(met)
            ref_str = f"Ref. jogo: {ref_val:,.0f}" if not pd.isna(ref_val) else "Ref. jogo: sem dados"
            default = defaults_pct.get(met, 200.0)
            pct_input = cols_plan[i].number_input(
                f"{met.split('(')[0].strip()} (%)",
                min_value=0.0, max_value=1000.0,
                value=default, step=10.0,
                key=f"pvr_pct_{i}",
                help=f"% do jogo de referência · {ref_str}"
            )
            planeado_pct[met] = pct_input
            # Show reference
            cols_plan[i].caption(ref_str)

        st.divider()

        # ── Gráfico principal: Planeado vs Realizado ──────────────────────
        st.markdown('<p class="section-title">📊 Planeado vs Realizado — Microciclo vs Jogo</p>', unsafe_allow_html=True)

        rows_pvr = []
        for met in mets_pvr_disp:
            ref_val    = get_ref_jogo_pvr(met)
            plan_abs   = ref_val * planeado_pct[met] / 100 if not pd.isna(ref_val) else np.nan
            real_val   = get_real_mc(met)
            pct_real   = (real_val / ref_val * 100) if (not pd.isna(ref_val) and ref_val > 0 and not pd.isna(real_val)) else np.nan
            exec_rate  = (real_val / plan_abs * 100) if (not pd.isna(plan_abs) and plan_abs > 0 and not pd.isna(real_val)) else np.nan

            rows_pvr.append({
                "Métrica": met.split("(")[0].strip(),
                "% Planeado": round(planeado_pct[met], 0),
                "% Real vs Jogo": round(pct_real, 1) if not pd.isna(pct_real) else np.nan,
                "% Execução": round(exec_rate, 1) if not pd.isna(exec_rate) else np.nan,
                "Valor Planeado": round(plan_abs, 0) if not pd.isna(plan_abs) else np.nan,
                "Valor Real": round(real_val, 0) if not pd.isna(real_val) else np.nan,
                "Ref. Jogo": round(ref_val, 0) if not pd.isna(ref_val) else np.nan,
                "_met": met,
            })

        if rows_pvr:
            df_pvr2 = pd.DataFrame(rows_pvr)

            # Cards de % execução por métrica
            cols_cards_pvr2 = st.columns(len(rows_pvr))
            for i, row in enumerate(rows_pvr):
                exec_p = row["% Execução"]
                plan_p = row["% Planeado"]
                real_p = row["% Real vs Jogo"]
                if pd.isna(exec_p):     cor2 = "#555"; badge = "—"
                elif exec_p >= 110:     cor2 = "#e74c3c"; badge = f"{exec_p:.0f}% 🔴"
                elif exec_p >= 95:      cor2 = "#2ecc71"; badge = f"{exec_p:.0f}% 🟢"
                elif exec_p >= 80:      cor2 = "#f39c12"; badge = f"{exec_p:.0f}% 🟡"
                else:                   cor2 = "#3498db"; badge = f"{exec_p:.0f}% 🔵"

                cols_cards_pvr2[i].markdown(
                    f'<div style="background:{cor2}18;border:2px solid {cor2};border-radius:12px;'
                    f'padding:12px 8px;text-align:center">'
                    f'<div style="font-size:0.72rem;font-weight:700;color:#ccc;margin-bottom:4px">{row["Métrica"]}</div>'
                    f'<div style="font-size:1.6rem;font-weight:900;color:{cor2}">{badge}</div>'
                    f'<div style="font-size:0.62rem;color:#888;margin-top:4px">Plan: {plan_p:.0f}% jogo</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                val_r_str = f"{int(row['Valor Real']):,}" if not pd.isna(row["Valor Real"]) else "—"
                val_p_str = f"{int(row['Valor Planeado']):,}" if not pd.isna(row["Valor Planeado"]) else "—"
                cols_cards_pvr2[i].caption(f"Real: {val_r_str} | Plan: {val_p_str}")
            st.divider()

            # Gráfico de barras — Plan vs Real como % do jogo
            fig_pvr2 = go.Figure()
            labels2 = df_pvr2["Métrica"].tolist()
            fig_pvr2.add_trace(go.Bar(
                x=labels2, y=df_pvr2["% Planeado"],
                name="🎯 Planeado (%)", marker_color="#457b9d", opacity=0.8,
            ))
            fig_pvr2.add_trace(go.Scatter(
                x=labels2, y=df_pvr2["% Real vs Jogo"],
                name="✅ Realizado (% do jogo)",
                mode="lines+markers+text",
                text=df_pvr2["% Real vs Jogo"].apply(lambda v: f"{v:.0f}%" if not pd.isna(v) else "—"),
                textposition="top center",
                textfont=dict(size=11, color="white"),
                line=dict(color="#e63946", width=3),
                marker=dict(size=12, color="#e63946", line=dict(width=2, color="white")),
            ))
            fig_pvr2.add_hline(y=100, line_dash="dash", line_color="rgba(255,255,255,0.3)",
                                annotation_text="= 1 Jogo (100%)")
            fig_pvr2.update_layout(
                height=420, yaxis_title="% do Jogo de Referência",
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="rgba(255,255,255,0.85)", margin=dict(t=20),
                legend=dict(orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)"),
            )
            st.plotly_chart(fig_pvr2, use_container_width=True)
            st.caption(f"Barras azuis = % planeada · Linha vermelha = % real atingida · Tudo expresso em % do jogo de referência ({ref_pvr})")

            st.divider()

            # ── Análise por jogador ───────────────────────────────────────
            st.markdown('<p class="section-title">👥 Carga Real por Jogador vs Jogo de Referência</p>', unsafe_allow_html=True)
            met_jog_pvr = st.selectbox("Métrica", mets_pvr_disp, key="pvr_met_jog")
            ref_jog_val = get_ref_jogo_pvr(met_jog_pvr)
            plan_pct_jog = planeado_pct.get(met_jog_pvr, 200)
            plan_abs_jog = ref_jog_val * plan_pct_jog / 100 if not pd.isna(ref_jog_val) else np.nan

            if met_jog_pvr in df_mc_treinos.columns:
                if met_jog_pvr == "PSE Sessão":
                    df_jog_pvr2 = df_mc_treinos.groupby("Jogador")[met_jog_pvr].mean().reset_index()
                else:
                    df_jog_pvr2 = df_mc_treinos.groupby("Jogador")[met_jog_pvr].sum().reset_index()
                df_jog_pvr2.columns = ["Jogador", "Real"]
                df_jog_pvr2["% vs Jogo"] = (df_jog_pvr2["Real"] / ref_jog_val * 100).round(1) if not pd.isna(ref_jog_val) else np.nan
                df_jog_pvr2["% Execução"] = (df_jog_pvr2["Real"] / plan_abs_jog * 100).round(1) if not pd.isna(plan_abs_jog) else np.nan
                df_jog_pvr2 = df_jog_pvr2.sort_values("% vs Jogo", ascending=False)

                cores_j2 = []
                for v in df_jog_pvr2["% Execução"].fillna(0):
                    if v >= 110:   cores_j2.append("#e74c3c")
                    elif v >= 95:  cores_j2.append("#2ecc71")
                    elif v >= 80:  cores_j2.append("#f39c12")
                    else:          cores_j2.append("#3498db")

                fig_jog_pvr2 = go.Figure()
                fig_jog_pvr2.add_trace(go.Bar(
                    x=df_jog_pvr2["Jogador"], y=df_jog_pvr2["% vs Jogo"],
                    marker_color=cores_j2,
                    text=df_jog_pvr2["% vs Jogo"].apply(lambda v: f"{v:.0f}%" if not pd.isna(v) else "—"),
                    textposition="outside", name="% vs Jogo",
                ))
                if not pd.isna(plan_pct_jog):
                    fig_jog_pvr2.add_hline(y=plan_pct_jog, line_dash="dash", line_color="#f39c12",
                                            annotation_text=f"Planeado {plan_pct_jog:.0f}%")
                fig_jog_pvr2.add_hline(y=100, line_dash="dot", line_color="rgba(255,255,255,0.3)",
                                        annotation_text="100% = 1 Jogo")
                fig_jog_pvr2.update_layout(
                    height=360, yaxis_title="% do Jogo de Referência",
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)", showlegend=False, margin=dict(t=20),
                )
                st.plotly_chart(fig_jog_pvr2, use_container_width=True)

                st.divider()
                # Tabela resumo
                if not pd.isna(ref_jog_val):
                    st.caption(f"Jogo de referência ({ref_pvr}): **{ref_jog_val:,.0f}** · Planeado: **{plan_pct_jog:.0f}%** = {plan_abs_jog:,.0f}")
                st.dataframe(df_jog_pvr2.set_index("Jogador").rename(columns={"Real": met_jog_pvr}), use_container_width=True)

            # ── Conclusões automáticas ─────────────────────────────────────
            st.divider()
            st.markdown('<p class="section-title">🧠 Conclusões</p>', unsafe_allow_html=True)
            for row in rows_pvr:
                exec_p = row["% Execução"]
                if pd.isna(exec_p): continue
                if exec_p >= 110:
                    st.markdown(f"🔴 **{row['Métrica']}**: executado {exec_p:.0f}% do planeado — acima do objetivo. Reduzir neste microciclo.")
                elif exec_p >= 95:
                    st.markdown(f"🟢 **{row['Métrica']}**: executado {exec_p:.0f}% do planeado — dentro do objetivo.")
                elif exec_p >= 80:
                    st.markdown(f"🟡 **{row['Métrica']}**: executado {exec_p:.0f}% do planeado — ligeiramente abaixo.")
                else:
                    st.markdown(f"🔵 **{row['Métrica']}**: executado {exec_p:.0f}% do planeado — abaixo do objetivo. Verificar ausências ou gestão de carga.")


    with st.expander("🧮 Calculadora de Exercícios Científica", expanded=False):
            st.markdown("> **Casamichana & Castellano (2010)** · **Dellal et al. (2012)** · **Hill-Haas et al. (2011)** · **Owen et al. (2011)**")

            EXERCICIOS_REF = {
                "Rondo / Posse fechada":           {"dist_min":82,  "acc_min":1.8, "frac_hsr":0.015,"frac_spr":0.003,"frac_dcc":0.85,"vmax_ref":23,"metabolico":"Aeróbia lática mista","neuro":"Força-Velocidade"},
                "Jogo Posicional (5-8v5-8)":       {"dist_min":110, "acc_min":2.4, "frac_hsr":0.060,"frac_spr":0.010,"frac_dcc":0.82,"vmax_ref":26,"metabolico":"Aeróbia-Anaeróbia","neuro":"Potência"},
                "Jogo Reduzido Pequeno (3-4v)":    {"dist_min":130, "acc_min":3.6, "frac_hsr":0.035,"frac_spr":0.008,"frac_dcc":0.88,"vmax_ref":25,"metabolico":"Anaeróbia lática","neuro":"Força-Velocidade"},
                "Jogo Reduzido Médio (5-7v)":      {"dist_min":118, "acc_min":2.8, "frac_hsr":0.065,"frac_spr":0.018,"frac_dcc":0.85,"vmax_ref":27,"metabolico":"Aeróbia-Anaeróbia mista","neuro":"Potência-Velocidade"},
                "Jogo Reduzido Grande (8-10v)":    {"dist_min":108, "acc_min":2.0, "frac_hsr":0.090,"frac_spr":0.030,"frac_dcc":0.80,"vmax_ref":29,"metabolico":"Predominantemente aeróbia","neuro":"Resistência"},
                "Jogo Formal (11v11)":             {"dist_min":115, "acc_min":1.6, "frac_hsr":0.110,"frac_spr":0.038,"frac_dcc":0.80,"vmax_ref":31,"metabolico":"Aeróbia com picos","neuro":"Velocidade-Resistência"},
                "Sprint / Velocidade":             {"dist_min":145, "acc_min":4.5, "frac_hsr":0.280,"frac_spr":0.180,"frac_dcc":0.88,"vmax_ref":32,"metabolico":"Anaeróbia alática","neuro":"Velocidade máxima"},
                "Físico / Resistência":            {"dist_min":185, "acc_min":0.8, "frac_hsr":0.020,"frac_spr":0.002,"frac_dcc":0.80,"vmax_ref":20,"metabolico":"Aeróbia extensiva","neuro":"Resistência"},
                "Técnico-Tático":                  {"dist_min":70,  "acc_min":1.2, "frac_hsr":0.010,"frac_spr":0.002,"frac_dcc":0.82,"vmax_ref":22,"metabolico":"Aeróbia leve","neuro":"Coordenação"},
                "Ativação / Aquecimento":          {"dist_min":55,  "acc_min":0.6, "frac_hsr":0.005,"frac_spr":0.001,"frac_dcc":0.80,"vmax_ref":19,"metabolico":"Aeróbia leve","neuro":"Ativação"},
                "Retorno à Calma":                 {"dist_min":30,  "acc_min":0.2, "frac_hsr":0.002,"frac_spr":0.000,"frac_dcc":0.80,"vmax_ref":14,"metabolico":"Recuperação","neuro":"Recuperação"},
            }

            tab_c1, tab_c2 = st.tabs(["🧮 Calculadora", "📋 Tabela de Referência"])

            with tab_c1:
                col_c1, col_c2 = st.columns(2)
                tipo_ex = col_c1.selectbox("Tipo de Exercício", list(EXERCICIOS_REF.keys()), key="calc_tipo")
                n_jog   = col_c2.number_input("Nº de Jogadores", 2, 22, 8, key="calc_njog")
                duracao = col_c1.number_input("Duração (min)", 1, 60, 15, key="calc_dur")
                espaco  = col_c2.number_input("Espaço total (m²)", 50, 10000, 800, key="calc_esp")

                ref = EXERCICIOS_REF[tipo_ex]
                esp_jog = espaco / n_jog if n_jog > 0 else 100
                fator_esp = max(0.6, min(1.0 + (esp_jog - 100)/100 * 0.18, 1.6))
                fator_acc = max(0.5, min(1.0 + (100 - esp_jog)/100 * 0.25, 1.5))

                dist_jog   = ref["dist_min"] * duracao * fator_esp
                hsr_jog    = dist_jog * ref["frac_hsr"]
                sprint_jog = dist_jog * ref["frac_spr"]
                acc_jog    = ref["acc_min"] * fator_acc * duracao
                dcc_jog    = acc_jog * ref["frac_dcc"]
                vmax_ref   = ref["vmax_ref"]

                st.divider()
                st.markdown('<p class="section-title">📊 Previsão por Jogador</p>', unsafe_allow_html=True)
                k1,k2,k3,k4,k5,k6 = st.columns(6)
                for col_k, lbl, val, unit, hlp in [
                    (k1,"Distância",      f"{dist_jog:,.0f}","m",   "Distância total estimada"),
                    (k2,"HSR",            f"{hsr_jog:,.0f}", "m",   "Alta Velocidade"),
                    (k3,"Sprint",         f"{sprint_jog:,.0f}","m", "Velocidade máxima"),
                    (k4,"Acc (n)",        f"{acc_jog:.0f}",  "",    "Acelerações estimadas"),
                    (k5,"Dcc (n)",        f"{dcc_jog:.0f}",  "",    "Desacelerações estimadas"),
                    (k6,"Vmáx esperada",  f"{vmax_ref}",     "km/h","Velocidade máxima de referência"),
                ]:
                    col_k.metric(f"{lbl} {unit}".strip(), val, help=hlp)

                st.markdown('<p class="section-title">📦 Total da Equipa</p>', unsafe_allow_html=True)
                te1,te2,te3,te4,te5 = st.columns(5)
                te1.metric("Distância Total", f"{dist_jog*n_jog/1000:.2f} km")
                te2.metric("HSR Total",       f"{hsr_jog*n_jog:,.0f} m")
                te3.metric("Sprint Total",    f"{sprint_jog*n_jog:,.0f} m")
                te4.metric("Acc Total",       f"{acc_jog*n_jog:.0f}")
                te5.metric("Dcc Total",       f"{dcc_jog*n_jog:.0f}")

                col_i1,col_i2,col_i3 = st.columns(3)
                col_i1.info(f"⚗️ **Perfil Metabólico:** {ref['metabolico']}")
                col_i2.info(f"💪 **Perfil Neuromuscular:** {ref['neuro']}")
                col_i3.info(f"📐 **m²/jog:** {esp_jog:.0f} · Fator: {fator_esp:.2f}×")

            with tab_c2:
                df_ref_tab = pd.DataFrame([{
                    "Tipo": k, "Dist/min (m)": v["dist_min"],
                    "Acc/min": v["acc_min"], "Frac. HSR": f"{v['frac_hsr']*100:.1f}%",
                    "Frac. Sprint": f"{v['frac_spr']*100:.1f}%",
                    "Vmáx Ref (km/h)": v["vmax_ref"],
                    "Perfil Metabólico": v["metabolico"], "Perfil Neuro": v["neuro"],
                } for k,v in EXERCICIOS_REF.items()])
                st.dataframe(df_ref_tab.set_index("Tipo"), use_container_width=True)
                st.caption("Fonte: Casamichana & Castellano (2010) · Dellal et al. (2012) · Hill-Haas et al. (2011)")


        # ═══════════════════════════════════════════════════════════════════════════════
        # 📐 ESPAÇO & CARGA EXTERNA
        # ═══════════════════════════════════════════════════════════════════════════════

    with st.expander("📐 Espaço & Carga Externa", expanded=False):
            st.markdown("> **Casamichana & Castellano (2010)** · **Dellal et al. (2012)** · **Hill-Haas et al. (2011)** · *'Duplicar o espaço → +15–25% distância'* (r=0.76)")

            ZONAS_ESP = [
                {"zona":"ZONA 1 — < 30 m²/jog",    "esp_min":0,   "esp_max":30,  "dist":"70–90 m/min",  "hsr":"<1%",    "sprint":"<0.3%",  "acc":"4–6/min",    "exemplos":"Rondos, posses fechadas","cor":"#2ecc71"},
                {"zona":"ZONA 2 — 30–100 m²/jog",  "esp_min":30,  "esp_max":100, "dist":"90–115 m/min", "hsr":"3–7%",   "sprint":"0.5–1%", "acc":"2–4/min",    "exemplos":"Jogos reduzidos 4v4–7v7","cor":"#f39c12"},
                {"zona":"ZONA 3 — 100–200 m²/jog", "esp_min":100, "esp_max":200, "dist":"110–130 m/min","hsr":"7–12%",  "sprint":"1.5–3%", "acc":"1–2/min",    "exemplos":"Jogos 8v8–10v10",        "cor":"#e67e22"},
                {"zona":"ZONA 4 — > 200 m²/jog",   "esp_min":200, "esp_max":999, "dist":">130 m/min",   "hsr":">12%",   "sprint":">3%",    "acc":"<1/min",     "exemplos":"Jogo formal",            "cor":"#e74c3c"},
            ]

            tab_esp1, tab_esp2 = st.tabs(["📊 Matriz de Referência", "🧮 Simulador"])

            with tab_esp1:
                cols_z = st.columns(4)
                for i, zona in enumerate(ZONAS_ESP):
                    cor_z = zona["cor"]
                    cols_z[i].markdown(
                        f'<div style="background:{cor_z}18;border:1px solid {cor_z}44;border-top:3px solid {cor_z};border-radius:10px;padding:14px;margin:4px">'
                        f'<div style="font-size:0.72rem;font-weight:700;color:{cor_z};margin-bottom:10px">{zona["zona"]}</div>'
                        f'<div style="font-size:0.68rem;color:rgba(255,255,255,0.8);margin:5px 0"><b>Distância:</b> {zona["dist"]}</div>'
                        f'<div style="font-size:0.68rem;color:rgba(255,255,255,0.8);margin:5px 0"><b>HSR:</b> {zona["hsr"]}</div>'
                        f'<div style="font-size:0.68rem;color:rgba(255,255,255,0.8);margin:5px 0"><b>Sprint:</b> {zona["sprint"]}</div>'
                        f'<div style="font-size:0.68rem;color:rgba(255,255,255,0.8);margin:5px 0"><b>Acc/Dcc:</b> {zona["acc"]}</div>'
                        f'<div style="font-size:0.62rem;color:rgba(255,255,255,0.4);margin-top:8px;padding-top:6px;border-top:1px solid rgba(255,255,255,0.06)">{zona["exemplos"]}</div>'
                        f'</div>', unsafe_allow_html=True)

            with tab_esp2:
                col_s1,col_s2,col_s3 = st.columns(3)
                s_x    = col_s1.number_input("Comprimento (m)", 10, 120, 40, key="esp_x")
                s_y    = col_s2.number_input("Largura (m)", 5, 80, 30, key="esp_y")
                s_njog = col_s3.number_input("Nº Jogadores em campo", 4, 22, 10, key="esp_njog_total")
                s_dur  = col_s1.number_input("Duração (min)", 1, 60, 12, key="esp_dur")
                s_tipo = col_s2.selectbox("Tipo", ["Jogo Reduzido","Jogo Posicional","Jogo Formal","Sprint"], key="esp_tipo")

                area_total = s_x * s_y
                area_jog   = area_total / s_njog if s_njog > 0 else 100
                base_dist  = {"Jogo Reduzido":100,"Jogo Posicional":110,"Jogo Formal":115,"Sprint":145}.get(s_tipo,110)
                fator_s    = max(0.6, min(1.0 + (area_jog - 100)/100 * 0.18, 1.6))
                fator_a    = max(0.5, min(1.0 + (100 - area_jog)/100 * 0.25, 1.5))
                frac_hsr   = {"Jogo Reduzido":0.065,"Jogo Posicional":0.060,"Jogo Formal":0.110,"Sprint":0.280}.get(s_tipo,0.065)
                frac_spr   = {"Jogo Reduzido":0.018,"Jogo Posicional":0.010,"Jogo Formal":0.038,"Sprint":0.180}.get(s_tipo,0.018)
                acc_min    = {"Jogo Reduzido":2.8,"Jogo Posicional":2.4,"Jogo Formal":1.6,"Sprint":4.5}.get(s_tipo,2.8)

                dist_s = base_dist * fator_s * s_dur
                hsr_s  = dist_s * frac_hsr
                spr_s  = dist_s * frac_spr
                acc_s  = acc_min * fator_a * s_dur
                dcc_s  = acc_s * 0.85

                zona_id = next((z for z in ZONAS_ESP if z["esp_min"] <= area_jog < z["esp_max"]), ZONAS_ESP[-1])
                cor_z2 = zona_id["cor"]
                st.markdown(f'<div style="background:{cor_z2}18;border:2px solid {cor_z2}55;border-radius:12px;padding:14px;margin:10px 0"><div style="font-size:0.75rem;font-weight:700;color:{cor_z2}">{zona_id["zona"]} — {area_jog:.0f} m²/jogador</div><div style="font-size:0.78rem;color:rgba(255,255,255,0.7);margin-top:4px">{s_x}×{s_y}m = {area_total} m² · {s_njog} jogadores</div></div>', unsafe_allow_html=True)

                k1e,k2e,k3e,k4e,k5e,k6e = st.columns(6)
                for col_ke, lbl_e, val_e in [
                    (k1e,"Distância/jog",f"{dist_s:,.0f} m"),
                    (k2e,"HSR/jog",      f"{hsr_s:,.0f} m"),
                    (k3e,"Sprint/jog",   f"{spr_s:,.0f} m"),
                    (k4e,"Acc/jog",      f"{acc_s:.0f}"),
                    (k5e,"Dcc/jog",      f"{dcc_s:.0f}"),
                    (k6e,"Fator Espaço", f"{fator_s:.2f}×"),
                ]:
                    col_ke.metric(lbl_e, val_e)


        # ═══════════════════════════════════════════════════════════════════════════════
        # ✅ VALIDAÇÃO DE DADOS
        # ═══════════════════════════════════════════════════════════════════════════════

elif seccao == "avancado":
    lm_header("Análise Avançada", "Z-Score, normalização por limiares individuais e análise GPS", "Avançado")
    tab_av = st.tabs(["📐 Z-Score", "🏃 Normalização HSR/Sprint"])

    with tab_av[0]:

            METRICAS_ZSCORE = [
                "Distância Total (m)", "HSR (m)", "Sprint (m)", "Vel. Máx (km/h)",
                "Acc (n)", "Dcc (n)", "PSE Sessão", "Carga Interna",
                "Hooper Index", "Sono (1-5)", "Dor Musc. (1-5)", "Stress (1-5)", "Humor (1-5)",
            ]
            metricas_disp = [m for m in METRICAS_ZSCORE if m in df.columns]

            def zscore_serie(serie: pd.Series) -> pd.Series:
                mu, sigma = serie.mean(), serie.std()
                if sigma == 0:
                    return pd.Series([0.0] * len(serie), index=serie.index)
                return (serie - mu) / sigma

            def cor_zscore(z):
                if z > 2:    return "#e74c3c"
                if z > 1:    return "#f39c12"
                if z >= -1:  return "#2ecc71"
                if z >= -2:  return "#3498db"
                return "#9b59b6"

            # ── Tabs ─────────────────────────────────────────────────────────────────
            tab1, tab2 = st.tabs(["👤 Jogador ao longo dos Microciclos", "📊 Comparação entre Jogadores da mesma Posição"])

            # ── TAB 1: Jogador ao longo dos microciclos ───────────────────────────────
            with tab1:
                st.markdown('<p class="section-title">Evolução do Z-Score do Jogador por Microciclo</p>', unsafe_allow_html=True)
                col_a, col_b = st.columns(2)
                jog_z  = col_a.selectbox("Jogador", sorted(df["Jogador"].dropna().unique()), key="z_jog")
                met_z  = col_b.selectbox("Métrica", metricas_disp, key="z_met1")

                df_jog_z = df[df["Jogador"] == jog_z].copy()
                # Dia MD já filtrado via df_f_dia na sidebar

                if met_z in df_jog_z.columns and df_jog_z[met_z].notna().sum() > 1:
                    # Z-Score calculado sobre todos os dados do jogador
                    df_jog_z = df_jog_z.dropna(subset=[met_z, "Microciclo (Nr)"]).copy()
                    df_jog_z["Z-Score"] = zscore_serie(df_jog_z[met_z])

                    # Média por microciclo
                    mc_z = df_jog_z.groupby("Microciclo (Nr)").agg(
                        Z_medio=("Z-Score", "mean"),
                        Valor_medio=(met_z, "mean"),
                        n=("Z-Score", "count"),
                    ).reset_index()
                    mc_z.columns = ["Microciclo (Nr)", "Z-Score Médio", f"{met_z} Médio", "Sessões"]
                    mc_z = mc_z.sort_values("Microciclo (Nr)")

                    cores_z = [cor_zscore(z) for z in mc_z["Z-Score Médio"]]

                    fig_z1 = go.Figure()
                    fig_z1.add_trace(go.Bar(
                        x=mc_z["Microciclo (Nr)"].astype(str),
                        y=mc_z["Z-Score Médio"],
                        marker_color=cores_z,
                        text=mc_z["Z-Score Médio"].round(2),
                        textposition="outside",
                        name="Z-Score",
                    ))
                    fig_z1.add_hline(y=2,  line_dash="dash", line_color="#e74c3c",  annotation_text="+2σ")
                    fig_z1.add_hline(y=1,  line_dash="dot",  line_color="#f39c12",  annotation_text="+1σ")
                    fig_z1.add_hline(y=0,  line_dash="solid",line_color="white",    line_width=1)
                    fig_z1.add_hline(y=-1, line_dash="dot",  line_color="#3498db",  annotation_text="-1σ")
                    fig_z1.add_hline(y=-2, line_dash="dash", line_color="#9b59b6",  annotation_text="-2σ")
                    fig_z1.update_layout(
                        xaxis_title="Microciclo", yaxis_title="Z-Score",
                        height=400, plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)", margin=dict(t=30),
                    )
                    st.plotly_chart(fig_z1, use_container_width=True)

                    # Interpretação automática
                    z_ultimo = mc_z.iloc[-1]["Z-Score Médio"]
                    mc_ultimo = int(mc_z.iloc[-1]["Microciclo (Nr)"])
                    if z_ultimo > 2:
                        st.markdown(f"🔴 **MC {mc_ultimo}**: Z-Score de **{z_ultimo:.2f}** — valor **muito acima** da média do jogador (>+2σ). Risco de sobrecarga.")
                    elif z_ultimo > 1:
                        st.markdown(f"🟡 **MC {mc_ultimo}**: Z-Score de **{z_ultimo:.2f}** — valor **acima** da média (+1σ a +2σ). Monitorizar.")
                    elif z_ultimo >= -1:
                        st.markdown(f"🟢 **MC {mc_ultimo}**: Z-Score de **{z_ultimo:.2f}** — valor **dentro da média** (±1σ). Normal.")
                    elif z_ultimo >= -2:
                        st.markdown(f"🔵 **MC {mc_ultimo}**: Z-Score de **{z_ultimo:.2f}** — valor **abaixo** da média (-1σ a -2σ). Sub-estimulação.")
                    else:
                        st.markdown(f"🟣 **MC {mc_ultimo}**: Z-Score de **{z_ultimo:.2f}** — valor **muito abaixo** da média (<-2σ). Possível recuperação/lesão.")

                    # Tabela detalhada
                    with st.expander("📋 Ver tabela completa de Z-Scores por Microciclo"):
                        st.dataframe(mc_z.set_index("Microciclo (Nr)"), use_container_width=True)

                    # Múltiplas métricas — radar por microciclo
                    st.divider()
                    st.markdown('<p class="section-title">Radar de Z-Scores — Múltiplas Métricas (último vs penúltimo MC)</p>', unsafe_allow_html=True)
                    mcs_disponiveis = sorted(df_jog_z["Microciclo (Nr)"].unique(), reverse=True)
                    if len(mcs_disponiveis) >= 2:
                        mc_A = st.selectbox("Microciclo A", mcs_disponiveis, index=0, key="radar_mcA")
                        mc_B = st.selectbox("Microciclo B", mcs_disponiveis, index=1, key="radar_mcB")

                        # Métricas disponíveis — apenas as que existem em df_radar
                        # e que não são colunas calculadas como "Z-Score"
                        EXCLUIR_RADAR = {"Z-Score","Z-Score Médio","Microciclo (Nr)",
                                          "Jogador","Posição","Tipo","Dia MD","Data"}
                        radar_mets = [m for m in get_mets_gps(df_jog_z)
                                      if m not in EXCLUIR_RADAR]

                        df_radar = df[df["Jogador"] == jog_z].copy()
                        if "Dia MD" in df_radar.columns and dia_md_sel:
                            df_radar = df_radar[df_radar["Dia MD"].isin(dia_md_sel)]

                        # Filtrar radar_mets para só incluir colunas que existem em df_radar
                        radar_mets = [m for m in radar_mets if m in df_radar.columns]

                        # Z-score calculado sobre toda a série do jogador
                        zscores_A, zscores_B = [], []
                        for m in radar_mets:
                            if m in df_radar.columns and df_radar[m].notna().sum() > 1:
                                z_all = zscore_serie(df_radar[m])
                                sub_A = z_all[df_radar["Microciclo (Nr)"] == mc_A]
                                sub_B = z_all[df_radar["Microciclo (Nr)"] == mc_B]
                                zscores_A.append(round(sub_A.mean(), 2) if not sub_A.empty else 0)
                                zscores_B.append(round(sub_B.mean(), 2) if not sub_B.empty else 0)
                            else:
                                zscores_A.append(0); zscores_B.append(0)

                        fig_radar_z = go.Figure()
                        fig_radar_z.add_trace(go.Scatterpolar(
                            r=zscores_A + [zscores_A[0]], theta=radar_mets + [radar_mets[0]],
                            fill="toself", name=f"MC {mc_A}", line_color="#e63946", opacity=0.8,
                        ))
                        fig_radar_z.add_trace(go.Scatterpolar(
                            r=zscores_B + [zscores_B[0]], theta=radar_mets + [radar_mets[0]],
                            fill="toself", name=f"MC {mc_B}", line_color="#457b9d", opacity=0.8,
                        ))
                        fig_radar_z.update_layout(
                            polar=dict(radialaxis=dict(visible=True)),
                            height=420, plot_bgcolor="rgba(0,0,0,0)",
                            paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                        )
                        st.plotly_chart(fig_radar_z, use_container_width=True)
                else:
                    st.warning(f"Dados insuficientes para calcular Z-Score de '{met_z}' para {jog_z}.")

            # ── TAB 2: Comparação entre jogadores da mesma posição ────────────────────
            with tab2:
                st.markdown('<p class="section-title">Z-Score por Posição — Onde se posiciona cada jogador?</p>', unsafe_allow_html=True)
                col_c, col_d = st.columns(2)
                pos_z  = col_c.selectbox("Posição", posicoes if posicoes else ["—"], key="z_pos")
                met_z2 = col_d.selectbox("Métrica", metricas_disp, key="z_met2")
                mc_z2  = col_c.selectbox("Microciclo", sorted(df["Microciclo (Nr)"].dropna().unique(), reverse=True), key="z_mc2")

                df_pos_z = df[
                    (df["Posição"] == pos_z) &
                    (df["Microciclo (Nr)"] == mc_z2)
                ].copy()
                # Dia MD já filtrado via df_f_dia

                if met_z2 in df_pos_z.columns and df_pos_z[met_z2].notna().sum() > 1:
                    # Z-Score calculado dentro do grupo da posição
                    df_pos_z["Z-Score"] = zscore_serie(df_pos_z[met_z2])
                    df_pos_z_mc = df_pos_z.groupby("Jogador").agg(
                        Z_medio=("Z-Score", "mean"),
                        Valor_medio=(met_z2, "mean"),
                    ).reset_index().sort_values("Z_medio", ascending=True)
                    df_pos_z_mc.columns = ["Jogador", "Z-Score", f"Média {met_z2}"]

                    cores_pos = [cor_zscore(z) for z in df_pos_z_mc["Z-Score"]]

                    fig_pos_z = go.Figure(go.Bar(
                        y=df_pos_z_mc["Jogador"],
                        x=df_pos_z_mc["Z-Score"],
                        orientation="h",
                        marker_color=cores_pos,
                        text=df_pos_z_mc["Z-Score"].round(2),
                        textposition="outside",
                    ))
                    fig_pos_z.add_vline(x=0,  line_dash="solid", line_color="white", line_width=1)
                    fig_pos_z.add_vline(x=1,  line_dash="dot",   line_color="#f39c12", annotation_text="+1σ")
                    fig_pos_z.add_vline(x=-1, line_dash="dot",   line_color="#3498db", annotation_text="-1σ")
                    fig_pos_z.update_layout(
                        xaxis_title="Z-Score", height=max(280, len(df_pos_z_mc)*55),
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font_color="rgba(255,255,255,0.85)", margin=dict(t=20),
                    )
                    st.plotly_chart(fig_pos_z, use_container_width=True)

                    st.markdown(f"**Referência do grupo ({pos_z}) — MC {int(mc_z2)}:**")
                    st.dataframe(df_pos_z_mc.set_index("Jogador"), use_container_width=True)

                    # Conclusões por posição
                    st.divider()
                    st.markdown('<p class="section-title">🧠 Conclusões</p>', unsafe_allow_html=True)
                    acima = df_pos_z_mc[df_pos_z_mc["Z-Score"] > 1]["Jogador"].tolist()
                    abaixo = df_pos_z_mc[df_pos_z_mc["Z-Score"] < -1]["Jogador"].tolist()
                    normal = df_pos_z_mc[df_pos_z_mc["Z-Score"].between(-1, 1)]["Jogador"].tolist()
                    media_val = df_pos_z[met_z2].mean()

                    if acima:
                        st.markdown(f"🟡 **Acima da média do grupo** (>+1σ): {', '.join(acima)}")
                    if abaixo:
                        st.markdown(f"🔵 **Abaixo da média do grupo** (<-1σ): {', '.join(abaixo)}")
                    if normal:
                        st.markdown(f"🟢 **Dentro da média** (±1σ): {', '.join(normal)}")
                    st.markdown(f"📊 **Média do grupo** para {met_z2} no MC {int(mc_z2)}: **{media_val:.1f}**")

                    # Heatmap — todos os microciclos × jogadores da posição
                    st.divider()
                    st.markdown('<p class="section-title">🗺️ Heatmap Z-Score — Todos os Microciclos</p>', unsafe_allow_html=True)
                    df_heat = df[df["Posição"] == pos_z].copy()
                    # Dia MD já filtrado via df_f_dia

                    if met_z2 in df_heat.columns:
                        df_heat = df_heat.dropna(subset=[met_z2, "Microciclo (Nr)", "Jogador"])
                        pivot = df_heat.groupby(["Jogador", "Microciclo (Nr)"])[met_z2].mean(numeric_only=True).unstack()
                        # Z-score por coluna (microciclo) dentro da posição
                        pivot_z = pivot.apply(
                            lambda col: (col - col.mean()) / col.std() if col.std() > 0 and col.notna().sum() > 1 else col * 0,
                            axis=0
                        )

                        fig_heat = go.Figure(go.Heatmap(
                            z=pivot_z.values,
                            x=[f"MC {int(c)}" for c in pivot_z.columns],
                            y=pivot_z.index.tolist(),
                            colorscale="RdYlGn",
                            zmid=0,
                            text=pivot_z.round(1).values,
                            texttemplate="%{text}",
                            colorbar=dict(title="Z-Score"),
                        ))
                        fig_heat.update_layout(
                            height=max(280, len(pivot_z)*50),
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                            font_color="rgba(255,255,255,0.85)", margin=dict(t=10),
                            xaxis_title="Microciclo", yaxis_title="Jogador",
                        )
                        st.plotly_chart(fig_heat, use_container_width=True)
                else:
                    st.warning(f"Dados insuficientes para '{met_z2}' na posição '{pos_z}' no MC {int(mc_z2)}.")


        # ═══════════════════════════════════════════════════════════════════════════════
        # VISTA: CARGA JOGO VS TREINO
        # ═══════════════════════════════════════════════════════════════════════════════

    with tab_av[1]:
        st.info("📊 **Tabela de referência Z-Score:** >+2σ=Sobrecarga · +1σ a +2σ=Monitorizar · ±1σ=Normal · -1σ a -2σ=Sub-carga · <-2σ=Verificar contexto")


        st.markdown("> Ref.: **Pimenta et al.** — *Sprint and High-Speed Running: Should We Use Absolute or Normalized Thresholds?* · Journal of Human Kinetics")

        if "Vel. Máx (km/h)" not in df.columns:
            st.error("Coluna 'Vel. Máx (km/h)' necessária.")

        vmaxes = df.groupby("Jogador")["Vel. Máx (km/h)"].max().reset_index()
        vmaxes.columns = ["Jogador","Vmáx Record (km/h)"]
        for pct in [85,90,95]:
            vmaxes[f"Lim {pct}% (km/h)"] = (vmaxes["Vmáx Record (km/h)"] * pct/100).round(1)
        if "Posição" in df.columns:
            vmaxes["Posição"] = vmaxes["Jogador"].map(df.groupby("Jogador")["Posição"].last())

        tab_nh1, tab_nh2 = st.tabs(["📊 Limiares Individuais", "📐 Absoluto vs Normalizado"])

        with tab_nh1:
            df_vs = vmaxes.sort_values("Vmáx Record (km/h)", ascending=True)
            fig_vn = go.Figure()
            fig_vn.add_trace(go.Bar(y=df_vs["Jogador"], x=df_vs["Vmáx Record (km/h)"],
                orientation="h", marker_color="#e63946", name="Vmáx Record",
                text=df_vs["Vmáx Record (km/h)"].round(1), textposition="outside"))
            fig_vn.add_trace(go.Bar(y=df_vs["Jogador"], x=df_vs["Lim 90% (km/h)"],
                orientation="h", marker_color="rgba(255,255,255,0.15)", name="Limiar 90%"))
            fig_vn.update_layout(barmode="overlay", height=max(300,len(df_vs)*42),
                xaxis_title="km/h", yaxis=dict(autorange="reversed"),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="rgba(255,255,255,0.85)", margin=dict(t=5))
            st.plotly_chart(fig_vn, use_container_width=True)
            st.dataframe(vmaxes.set_index("Jogador"), use_container_width=True)

        with tab_nh2:
            if "Posição" in vmaxes.columns:
                pos_vmax = vmaxes.groupby("Posição").agg(
                    Vmáx_media=("Vmáx Record (km/h)","mean"),
                    Vmáx_max=("Vmáx Record (km/h)","max"),
                    Vmáx_min=("Vmáx Record (km/h)","min"),
                    n=("Jogador","count"),
                ).reset_index().sort_values("Vmáx_media", ascending=False)
                fig_pos_vn = go.Figure()
                fig_pos_vn.add_trace(go.Bar(x=pos_vmax["Posição"], y=pos_vmax["Vmáx_media"],
                    name="Vmáx Média", marker_color="#e63946",
                    text=pos_vmax["Vmáx_media"].round(1), textposition="outside",
                    error_y=dict(type="data",
                        array=(pos_vmax["Vmáx_max"]-pos_vmax["Vmáx_media"]).tolist(),
                        arrayminus=(pos_vmax["Vmáx_media"]-pos_vmax["Vmáx_min"]).tolist(),
                        visible=True, color="rgba(255,255,255,0.4)"),
                ))
                fig_pos_vn.add_hline(y=25, line_dash="dash", line_color="#f39c12", annotation_text="Limiar absoluto 25 km/h")
                fig_pos_vn.add_hline(y=19.8, line_dash="dot", line_color="#3498db", annotation_text="Limiar absoluto 19.8 km/h")
                fig_pos_vn.update_layout(height=380, yaxis_title="Velocidade Máxima (km/h)",
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)", showlegend=False, margin=dict(t=20))
                st.plotly_chart(fig_pos_vn, use_container_width=True)
                st.caption("Barras de erro = min–max · Linhas = limiares absolutos standard")


        # ═══════════════════════════════════════════════════════════════════════════════
        # 🧮 CALCULADORA DE EXERCÍCIOS
        # ═══════════════════════════════════════════════════════════════════════════════

    with st.expander("🏋️ Análise de Exercícios GPS", expanded=False):

            df_ex = carregar_exercicios(excel_path)

            METS_EX = get_mets_gps(df_ex) if not df_ex.empty else []

            if df_ex.empty:
                st.info("""
        ### 📋 Folha de Exercícios vazia

        Abre o Excel e preenche a folha **Exercícios** com os dados de cada exercício.
        As linhas a azul claro são exemplos — podes apagá-las e começar a preencher a partir da linha 10.

        **Colunas a preencher:**
        - **Data** — data do treino
        - **Microciclo (Nr)** — número do microciclo
        - **Dia MD** — ex: MD-3, MD-2, MD-1
        - **Nome do Exercício** — ex: "Joguinho posicional 4x4"
        - **Categoria** — ex: Jogo Reduzido, Físico, Técnico-Tático
        - **Duração (min)** — duração do exercício
        - **Nº Jogadores** — número de jogadores
        - **Distância Total, HSR, Sprint, Acc, Dcc, Vel. Máx** — médias por jogador no exercício

        Depois guarda o Excel e clica em **🔄 Atualizar Dados**.
                """)

            mets_ex_disp = [m for m in METS_EX if m in df_ex.columns and df_ex[m].notna().any()]

            # ── Filtros ───────────────────────────────────────────────────────────────
            col_f1, col_f2, col_f3 = st.columns(3)

            datas_ex = sorted(df_ex["Data"].dropna().dt.date.unique(), reverse=True) if "Data" in df_ex.columns else []
            mcs_ex   = sorted(df_ex["Microciclo (Nr)"].dropna().unique(), reverse=True) if "Microciclo (Nr)" in df_ex.columns else []
            cats_ex  = sorted(df_ex["Categoria"].dropna().unique()) if "Categoria" in df_ex.columns else []

            modo_ex = col_f1.radio("Modo de análise", ["📅 Por sessão (dia)", "📆 Por microciclo", "📊 Geral"], horizontal=True)

            if modo_ex == "📅 Por sessão (dia)":
                if not datas_ex:
                    st.warning("Sem datas disponíveis nos dados de exercícios.")
                    data_ex_sel = None
                else:
                    data_ex_sel = col_f2.selectbox(
                        "Data", datas_ex,
                        format_func=lambda d: d.strftime("%d/%m/%Y"),
                        key="ex_data"
                    )
                df_ex_f = df_ex[df_ex["Data"].dt.date == data_ex_sel] if ("Data" in df_ex.columns and data_ex_sel) else df_ex
                titulo_ctx = f"Treino de {data_ex_sel.strftime('%d/%m/%Y')}" if data_ex_sel else "Sem dados"

            elif modo_ex == "📆 Por microciclo":
                mc_ex_sel = col_f2.selectbox("Microciclo", mcs_ex, key="ex_mc")
                df_ex_f = df_ex[df_ex["Microciclo (Nr)"] == mc_ex_sel] if "Microciclo (Nr)" in df_ex.columns else df_ex
                titulo_ctx = f"Microciclo {int(mc_ex_sel)}"
            else:
                df_ex_f = df_ex.copy()
                titulo_ctx = "Todos os exercícios"

            cat_sel = col_f3.multiselect("Categoria", cats_ex, default=cats_ex, key="ex_cat")
            if cat_sel and "Categoria" in df_ex_f.columns:
                df_ex_f = df_ex_f[df_ex_f["Categoria"].isin(cat_sel)]

            if df_ex_f.empty:
                st.warning("Sem exercícios para os filtros selecionados.")

            if not mets_ex_disp:
                st.warning("Sem métricas numéricas na folha 'Exercícios'. Verifica o formato do Excel.")
                met_ex = None
            else:
                met_ex = st.selectbox("Métrica de análise", mets_ex_disp, key="ex_met",
                                       help="Métrica usada para ordenar e comparar exercícios")

            st.divider()

            # ── Exercício mais exigente ────────────────────────────────────────────────
            st.markdown(f'<p class="section-title">🏆 Exercício Mais Exigente — {titulo_ctx}</p>', unsafe_allow_html=True)

            df_ex_rank = df_ex_f.dropna(subset=[met_ex]).sort_values(met_ex, ascending=False).copy() if (mets_ex_disp and met_ex and met_ex in df_ex_f.columns) else pd.DataFrame()

            if not df_ex_rank.empty:
                top = df_ex_rank.iloc[0]
                segundo = df_ex_rank.iloc[1] if len(df_ex_rank) > 1 else None
                terceiro = df_ex_rank.iloc[2] if len(df_ex_rank) > 2 else None

                c1, c2, c3 = st.columns(3)
                def card_ex(col, row, medal, cor):
                    nome = str(row["Exercício"])[:30] if "Exercício" in df_ex_rank.columns else "—"
                    cat  = row.get("Categoria","—")
                    dur  = row.get("Duração (min)","—")
                    val  = row[met_ex]
                    col.markdown(
                        f'<div style="background:{cor}22;border:2px solid {cor};border-radius:12px;'
                        f'padding:14px;text-align:center;margin:4px">'
                        f'<div style="font-size:1.4rem">{medal}</div>'
                        f'<div style="font-size:1rem;font-weight:700;color:{cor}">{nome}</div>'
                        f'<div style="font-size:0.75rem;color:#aaa">{cat} · {dur} min</div>'
                        f'<div style="font-size:1.6rem;font-weight:900;color:{cor};margin:6px 0">{val:,.1f}</div>'
                        f'<div style="font-size:0.7rem;color:#888">{met_ex}</div>'
                        f'</div>', unsafe_allow_html=True
                    )

                card_ex(c1, top,      "🥇", "#f39c12")
                if segundo  is not None: card_ex(c2, segundo,  "🥈", "#95a5a6")
                if terceiro is not None: card_ex(c3, terceiro, "🥉", "#cd7f32")

                st.markdown("")

                # Gráfico ranking completo
                cores_ex = []
                max_v = df_ex_rank[met_ex].max()
                for v in df_ex_rank[met_ex]:
                    pct = v / max_v if max_v > 0 else 0
                    if pct >= 0.85:   cores_ex.append("#f39c12")
                    elif pct >= 0.65: cores_ex.append("#e63946")
                    else:             cores_ex.append("#457b9d")

                nomes = df_ex_rank["Exercício"].astype(str) if "Exercício" in df_ex_rank.columns else df_ex_rank.index.astype(str)
                fig_rank_ex = go.Figure(go.Bar(
                    y=nomes, x=df_ex_rank[met_ex],
                    orientation="h",
                    marker_color=cores_ex,
                    text=df_ex_rank[met_ex].round(1),
                    textposition="outside",
                ))
                fig_rank_ex.add_vline(x=df_ex_rank[met_ex].mean(), line_dash="dash", line_color="white",
                                       annotation_text=f"Média: {df_ex_rank[met_ex].mean():.1f}")
                fig_rank_ex.update_layout(
                    height=max(300, len(df_ex_rank)*50),
                    xaxis_title=met_ex, yaxis=dict(autorange="reversed"),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)", showlegend=False, margin=dict(t=10),
                )
                st.plotly_chart(fig_rank_ex, use_container_width=True)

            st.divider()

            # ── Heatmap exercícios × métricas ─────────────────────────────────────────
            st.markdown('<p class="section-title">🗺️ Perfil de Exigência — Todos os Exercícios</p>', unsafe_allow_html=True)
            st.caption("Valores normalizados 0–100% (100% = exercício com valor máximo nessa métrica)")

            if "Exercício" in df_ex_f.columns and len(mets_ex_disp) >= 2:
                df_heat_ex = df_ex_f.groupby("Exercício")[mets_ex_disp].mean()
                # Normalizar 0–100 por coluna
                df_heat_norm = df_heat_ex.apply(
                    lambda col: (col / col.max() * 100).round(0) if col.max() > 0 else col * 0, axis=0
                )
                labels_heat_ex = [m.replace(" (m)","").replace(" (n)","").replace(" (km/h)","").replace(" Ex.","") for m in mets_ex_disp]
                df_heat_norm.columns = labels_heat_ex

                fig_heat_ex = go.Figure(go.Heatmap(
                    z=df_heat_norm.values,
                    x=df_heat_norm.columns.tolist(),
                    y=df_heat_norm.index.tolist(),
                    text=df_heat_ex.round(1).values,
                    texttemplate="%{text}",
                    colorscale="YlOrRd",
                    zmin=0, zmax=100,
                    colorbar=dict(title="% do máx", ticksuffix="%"),
                ))
                fig_heat_ex.update_layout(
                    height=max(280, len(df_heat_norm)*55),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)", margin=dict(t=10),
                    xaxis_title="Métrica GPS", yaxis_title="Exercício",
                )
                st.plotly_chart(fig_heat_ex, use_container_width=True)
                st.caption("Valores reais dentro de cada célula · Cor = % do máximo nessa métrica")

            st.divider()

            # ── Comparação por categoria ──────────────────────────────────────────────
            if "Categoria" in df_ex_f.columns and df_ex_f["Categoria"].notna().any():
                st.markdown('<p class="section-title">📊 Comparação por Categoria</p>', unsafe_allow_html=True)

                df_cat = df_ex_f.groupby("Categoria")[mets_ex_disp].mean().reset_index()
                fig_cat = px.bar(
                    df_cat.melt(id_vars="Categoria", value_vars=mets_ex_disp[:5]),
                    x="variable", y="value", color="Categoria",
                    barmode="group",
                    labels={"variable": "Métrica", "value": "Média", "Categoria": "Categoria"},
                    color_discrete_sequence=px.colors.qualitative.Bold,
                )
                fig_cat.update_layout(
                    height=380, plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                    margin=dict(t=10), legend_title="",
                )
                st.plotly_chart(fig_cat, use_container_width=True)

                # Radar por categoria
                st.markdown('<p class="section-title">📡 Radar de Perfil por Categoria</p>', unsafe_allow_html=True)
                if len(mets_ex_disp) >= 3:
                    df_radar_cat = df_ex_f.groupby("Categoria")[mets_ex_disp].mean()
                    # Normalizar
                    df_radar_norm = df_radar_cat.apply(
                        lambda col: col / col.max() * 100 if col.max() > 0 else col * 0, axis=0
                    )
                    labels_r = [m.replace(" (m)","").replace(" (n)","").replace(" Ex.","") for m in mets_ex_disp]
                    fig_radar_cat = go.Figure()
                    cores_r = px.colors.qualitative.Bold
                    for i, (cat, row) in enumerate(df_radar_norm.iterrows()):
                        vals = list(row.values) + [row.values[0]]
                        labs = labels_r + [labels_r[0]]
                        fig_radar_cat.add_trace(go.Scatterpolar(
                            r=vals, theta=labs, fill="toself",
                            name=cat, line_color=cores_r[i % len(cores_r)], opacity=0.75,
                        ))
                    fig_radar_cat.update_layout(
                        polar=dict(radialaxis=dict(visible=True, ticksuffix="%", range=[0,100])),
                        height=440, plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                    )
                    st.plotly_chart(fig_radar_cat, use_container_width=True)

            st.divider()

            # ── Evolução ao longo da sessão (ordem dos exercícios) ────────────────────
            if modo_ex == "📅 Por sessão (dia)" and "Exercício" in df_ex_f.columns:
                st.markdown('<p class="section-title">📈 Curva de Intensidade ao Longo da Sessão</p>', unsafe_allow_html=True)
                st.caption("Ordem dos exercícios tal como foram registados no Excel")

                met_ev_ex = st.selectbox("Métrica", mets_ex_disp, key="ex_ev_met")
                df_ev_ex = df_ex_f.reset_index(drop=True)
                df_ev_ex["Ordem"] = range(1, len(df_ev_ex)+1)
                df_ev_ex["Label"] = df_ev_ex["Exercício"].astype(str).str[:20]

                cores_ev = []
                max_ev = df_ev_ex[met_ev_ex].max() if df_ev_ex[met_ev_ex].notna().any() else 1
                for v in df_ev_ex[met_ev_ex]:
                    pct = v / max_ev if max_ev > 0 and pd.notna(v) else 0
                    if pct >= 0.85:   cores_ev.append("#f39c12")
                    elif pct >= 0.65: cores_ev.append("#e63946")
                    else:              cores_ev.append("#457b9d")

                fig_ev_ex = go.Figure()
                fig_ev_ex.add_trace(go.Bar(
                    x=df_ev_ex["Label"], y=df_ev_ex[met_ev_ex],
                    marker_color=cores_ev,
                    text=df_ev_ex[met_ev_ex].round(1), textposition="outside",
                    customdata=df_ev_ex[["Categoria","Duração (min)"]].values if "Categoria" in df_ev_ex.columns else None,
                    hovertemplate="<b>%{x}</b><br>%{y:.1f}<br>%{customdata[0]} · %{customdata[1]} min<extra></extra>"
                    if "Categoria" in df_ev_ex.columns else None,
                ))
                fig_ev_ex.add_hline(y=df_ev_ex[met_ev_ex].mean(), line_dash="dash", line_color="white",
                                     annotation_text=f"Média: {df_ev_ex[met_ev_ex].mean():.1f}")
                fig_ev_ex.update_layout(
                    height=360, yaxis_title=met_ev_ex,
                    xaxis_title="Exercício (por ordem da sessão)",
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)", showlegend=False, margin=dict(t=10),
                )
                st.plotly_chart(fig_ev_ex, use_container_width=True)

            st.divider()

            # ── Tabela completa ───────────────────────────────────────────────────────
            with st.expander("📋 Ver todos os registos"):
                cols_show = ["Exercício","Categoria","Duração (min)","Nº Jogadores"] + mets_ex_disp
                cols_show = [c for c in cols_show if c in df_ex_f.columns]
                sort_col = met_ex if (mets_ex_disp and "met_ex" in dir() and met_ex and met_ex in df_ex_f.columns) else (cols_show[0] if cols_show else None)
                st.dataframe(
                    df_ex_f[cols_show].sort_values(sort_col, ascending=False).reset_index(drop=True) if sort_col else df_ex_f[cols_show],
                    use_container_width=True
                )

            # ── Exportar relatório ────────────────────────────────────────────────────
            st.divider()
            if not df_ex_rank.empty:
                cols_exp = ["Exercício","Categoria","Duração (min)"] + mets_ex_disp
                cols_exp = [c for c in cols_exp if c in df_ex_f.columns]
                headers_e = "".join(f"<th>{c}</th>" for c in cols_exp)
                linhas_e  = "".join(
                    f'<tr>{"".join(f"<td>{round(row[c],1) if isinstance(row[c], float) else row[c]}</td>" for c in cols_exp)}</tr>'
                    for _, row in df_ex_f[cols_exp].sort_values(met_ex, ascending=False).iterrows()
                )
                html_ex = gerar_pdf_html(f"""
        <h1>Análise de Exercícios — {titulo_ctx}</h1>
        <h2>🥇 Exercício mais exigente ({met_ex}): {str(top["Exercício"])}</h2>
        <p>Valor: {top[met_ex]:,.1f} | Categoria: {top.get("Categoria","—")} | Duração: {top.get("Duração (min)","—")} min</p>
        <h2>Ranking Completo</h2>
        <table><tr>{headers_e}</tr>{linhas_e}</table>
        """, f"Exercicios_{titulo_ctx.replace(' ','_')}.html")
                botao_download_html(html_ex, f"Exercicios_{titulo_ctx.replace(' ','_')}.html",
                                    "📥 Exportar Relatório de Exercícios")




        # ═══════════════════════════════════════════════════════════════════════════════
        # VISTA: COMPARAÇÃO DE MICROCICLOS
        # ═══════════════════════════════════════════════════════════════════════════════

    with st.expander("🩺 Lesões & Disponibilidade", expanded=False):

            # Tentar ler folha de Lesões
            try:
                df_les = pd.read_excel(excel_path, sheet_name="Lesões", engine="openpyxl")
                df_les.columns = [str(c).strip() for c in df_les.columns]
                tem_folha_lesoes = True
            except Exception:
                tem_folha_lesoes = False
                df_les = pd.DataFrame()

            if not tem_folha_lesoes:
                st.warning("""
        ### ⚠️ Folha 'Lesões' não encontrada no Excel

        Para usar esta funcionalidade, adiciona uma folha chamada **Lesões** ao teu ficheiro Excel com estas colunas:

        | Jogador | Data Lesão | Data Retorno | Tipo de Lesão | Zona Corporal | Diagnóstico | Dias de Paragem | Estado |
        |---|---|---|---|---|---|---|---|
        | Paulino | 12/01/2025 | 25/01/2025 | Muscular | Isquiotibial | Elongação grau I | 13 | Recuperado |
        | ... | | | | | | | Ativo |

        O campo **Estado** deve ser: `Ativo` (ainda lesionado) ou `Recuperado`.

        Depois de criar a folha, clica em **🔄 Atualizar Dados**.
                """)

                # Mesmo sem folha de lesões, mostrar análise de ausências (sessões em falta)
                st.divider()
                st.markdown('<p class="section-title">📊 Análise de Participação nos Treinos</p>', unsafe_allow_html=True)
                st.caption("Jogadores com menos sessões que a média podem indicar períodos de indisponibilidade")

                if "Microciclo (Nr)" in df.columns:
                    mc_disp = sorted(df["Microciclo (Nr)"].dropna().unique(), reverse=True)
                    mc_les = st.selectbox("Microciclo a analisar", mc_disp, key="les_mc")
                    df_mc_les = df[df["Microciclo (Nr)"] == mc_les]
                    todos_jogs = sorted(df["Jogador"].dropna().unique())

                    participacao = []
                    max_sess = df_mc_les.groupby("Jogador").size().max() if not df_mc_les.empty else 0
                    for jog in todos_jogs:
                        sess = len(df_mc_les[df_mc_les["Jogador"] == jog])
                        pos  = df[df["Jogador"] == jog]["Posição"].iloc[-1] if "Posição" in df.columns and not df[df["Jogador"] == jog].empty else "—"
                        pct  = sess / max_sess * 100 if max_sess > 0 else 0
                        participacao.append({"Jogador": jog, "Posição": pos, "Sessões": sess,
                                              "% Participação": round(pct, 0),
                                              "Estado": "⚠️ Ausente/Indisponível" if pct < 50 else "✅ Presente"})

                    df_part = pd.DataFrame(participacao).sort_values("% Participação")
                    fig_part = go.Figure(go.Bar(
                        y=df_part["Jogador"], x=df_part["% Participação"],
                        orientation="h",
                        marker_color=["#e74c3c" if v < 50 else "#f39c12" if v < 80 else "#2ecc71"
                                       for v in df_part["% Participação"]],
                        text=[f"{int(v)}%" for v in df_part["% Participação"]],
                        textposition="outside",
                    ))
                    fig_part.add_vline(x=80, line_dash="dash", line_color="#f39c12", annotation_text="80%")
                    fig_part.add_vline(x=50, line_dash="dash", line_color="#e74c3c", annotation_text="50%")
                    fig_part.update_layout(
                        xaxis=dict(range=[0, 115], title="% Participação"),
                        height=max(300, len(df_part)*40),
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font_color="rgba(255,255,255,0.85)", margin=dict(t=10),
                    )
                    st.plotly_chart(fig_part, use_container_width=True)
                    ausentes = df_part[df_part["% Participação"] < 50]["Jogador"].tolist()
                    if ausentes:
                        st.warning(f"⚠️ **Possível indisponibilidade** no MC {int(mc_les)}: {', '.join(ausentes)} (menos de 50% das sessões)")

            # ── Com folha de Lesões ────────────────────────────────────────────────────
            # Normalizar colunas esperadas
            col_jog    = next((c for c in df_les.columns if "jogador" in c.lower()), None)
            col_data_l = next((c for c in df_les.columns if "data" in c.lower() and "lesão" in c.lower()), None) or                  next((c for c in df_les.columns if "data" in c.lower() and "inicio" in c.lower()), None)
            col_retorno = next((c for c in df_les.columns if "retorno" in c.lower() or "regresso" in c.lower()), None)
            col_dias    = next((c for c in df_les.columns if "dias" in c.lower()), None)
            col_tipo    = next((c for c in df_les.columns if "tipo" in c.lower()), None)
            col_zona    = next((c for c in df_les.columns if "zona" in c.lower() or "local" in c.lower()), None)
            col_estado  = next((c for c in df_les.columns if "estado" in c.lower() or "situação" in c.lower()), None)

            if col_jog is None:
                st.error("Coluna 'Jogador' não encontrada na folha Lesões.")

            if col_data_l:
                df_les[col_data_l] = pd.to_datetime(df_les[col_data_l], errors="coerce")
            if col_retorno:
                df_les[col_retorno] = pd.to_datetime(df_les[col_retorno], errors="coerce")

            tab_l1, tab_l2, tab_l3 = st.tabs(["📋 Registo de Lesões", "📈 Correlação com Carga", "📊 Epidemiologia"])

            with tab_l1:
                # Lesões ativas
                st.markdown('<p class="section-title">🩹 Lesões Ativas</p>', unsafe_allow_html=True)
                if col_estado:
                    ativas = df_les[df_les[col_estado].astype(str).str.lower().isin(["ativo","activo","sim","yes","1","true","ativa","activa"])]
                else:
                    ativas = df_les[df_les[col_retorno].isna()] if col_retorno else df_les

                if not ativas.empty:
                    for _, row in ativas.iterrows():
                        jog = row[col_jog]
                        tipo = row[col_tipo] if col_tipo else "—"
                        zona = row[col_zona] if col_zona else "—"
                        dias = row[col_dias] if col_dias else "—"
                        data_l = row[col_data_l].strftime("%d/%m/%Y") if col_data_l and pd.notna(row[col_data_l]) else "—"
                        st.markdown(
                            f'<div style="background:#7b1d1d33;border-left:4px solid #e74c3c;border-radius:8px;padding:12px;margin:6px 0">'
                            f'🩹 <b>{jog}</b> — {tipo} ({zona}) · desde {data_l} · {dias} dias de paragem'
                            f'</div>', unsafe_allow_html=True
                        )
                else:
                    st.success("✅ Sem lesões ativas no momento.")

                st.divider()
                st.markdown('<p class="section-title">📋 Histórico Completo</p>', unsafe_allow_html=True)
                st.dataframe(df_les, use_container_width=True)

                # Exportar
                linhas_les = "".join([
                    f'<tr>{"".join(f"<td>{row[c]}</td>" for c in df_les.columns)}</tr>'
                    for _, row in df_les.iterrows()
                ])
                headers_les = "".join([f"<th>{c}</th>" for c in df_les.columns])
                html_les = gerar_pdf_html(f"""
        <h1>Relatório de Lesões</h1>
        <table><tr>{headers_les}</tr>{linhas_les}</table>
        """, "Relatorio_Lesoes.html")
                botao_download_html(html_les, "Relatorio_Lesoes.html", "📥 Exportar Registo de Lesões")

            with tab_l2:
                st.markdown('<p class="section-title">⚡ Carga nas 4 Semanas Antes da Lesão</p>', unsafe_allow_html=True)
                if col_data_l is None:
                    st.warning("Coluna de data de lesão não encontrada.")
                else:
                    lesoes_com_data = df_les.dropna(subset=[col_data_l])
                    if lesoes_com_data.empty:
                        st.info("Sem lesões com data registada.")
                    else:
                        jog_sel_les = st.selectbox("Jogador", lesoes_com_data[col_jog].unique(), key="les_jog")
                        lesoes_jog = lesoes_com_data[lesoes_com_data[col_jog] == jog_sel_les]
                        data_les_sel = st.selectbox("Lesão (data)", lesoes_jog[col_data_l].dt.strftime("%d/%m/%Y").tolist(), key="les_data")
                        data_les_dt = pd.to_datetime(data_les_sel, format="%d/%m/%Y")

                        df_antes = df[
                            (df["Jogador"] == jog_sel_les) &
                            (df["Data"] >= data_les_dt - pd.Timedelta(weeks=4)) &
                            (df["Data"] < data_les_dt)
                        ].sort_values("Data")

                        if df_antes.empty:
                            st.info("Sem dados de carga nas 4 semanas anteriores à lesão.")
                        else:
                            fig_les_carga = go.Figure()
                            if "Carga Interna" in df_antes.columns:
                                fig_les_carga.add_trace(go.Bar(
                                    x=df_antes["Data"], y=df_antes["Carga Interna"],
                                    name="Carga Interna", marker_color="#e63946",
                                ))
                            if "ACWR" not in df_antes.columns:
                                df_jog_acwr = calcular_acwr(df[df["Jogador"] == jog_sel_les], jog_sel_les)
                                df_jog_acwr = df_jog_acwr[
                                    (df_jog_acwr["Data"] >= data_les_dt - pd.Timedelta(weeks=4)) &
                                    (df_jog_acwr["Data"] < data_les_dt)
                                ]
                                if "ACWR" in df_jog_acwr.columns:
                                    fig_les_carga.add_trace(go.Scatter(
                                        x=df_jog_acwr["Data"], y=df_jog_acwr["ACWR"] * 100,
                                        mode="lines+markers", name="ACWR ×100", line_color="#f39c12",
                                        yaxis="y2",
                                    ))
                            fig_les_carga.add_vline(x=data_les_dt, line_dash="dash", line_color="#e74c3c",
                                                     annotation_text="Lesão", annotation_position="top right")
                            fig_les_carga.update_layout(
                                height=360,
                                yaxis=dict(title="Carga Interna"),
                                yaxis2=dict(title="ACWR ×100", overlaying="y", side="right"),
                                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                font_color="rgba(255,255,255,0.85)", margin=dict(t=30),
                            )
                            st.plotly_chart(fig_les_carga, use_container_width=True)

            with tab_l3:
                st.markdown('<p class="section-title">📊 Distribuição de Lesões por Tipo e Zona</p>', unsafe_allow_html=True)

                c1_e, c2_e = st.columns(2)
                if col_tipo and not df_les[col_tipo].isna().all():
                    with c1_e:
                        tipo_count = df_les[col_tipo].value_counts().reset_index()
                        tipo_count.columns = ["Tipo", "Nº"]
                        fig_tipo = px.pie(tipo_count, names="Tipo", values="Nº", hole=0.4,
                                           color_discrete_sequence=px.colors.qualitative.Bold)
                        fig_tipo.update_layout(height=300, plot_bgcolor="rgba(0,0,0,0)",
                                                paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)", margin=dict(t=10))
                        st.plotly_chart(fig_tipo, use_container_width=True)

                if col_zona and not df_les[col_zona].isna().all():
                    with c2_e:
                        zona_count = df_les[col_zona].value_counts().reset_index()
                        zona_count.columns = ["Zona", "Nº"]
                        fig_zona = px.bar(zona_count, x="Nº", y="Zona", orientation="h",
                                           color="Nº", color_continuous_scale="Reds")
                        fig_zona.update_layout(height=300, plot_bgcolor="rgba(0,0,0,0)",
                                                paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                                                coloraxis_showscale=False, margin=dict(t=10))
                        st.plotly_chart(fig_zona, use_container_width=True)

                if col_dias and not df_les[col_dias].isna().all():
                    st.markdown('<p class="section-title">Dias de Paragem por Jogador</p>', unsafe_allow_html=True)
                    dias_jog = df_les.groupby(col_jog)[col_dias].sum().sort_values(ascending=False).reset_index()
                    dias_jog.columns = ["Jogador", "Total Dias"]
                    fig_dias_les = px.bar(dias_jog, x="Jogador", y="Total Dias",
                                           color="Total Dias", color_continuous_scale="Reds",
                                           text="Total Dias")
                    fig_dias_les.update_layout(height=320, plot_bgcolor="rgba(0,0,0,0)",
                                                paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                                                coloraxis_showscale=False, margin=dict(t=10))
                    st.plotly_chart(fig_dias_les, use_container_width=True)




        # ═══════════════════════════════════════════════════════════════════════════════
        # VISTA: TREINO VS JOGO — % MÉTRICAS GPS
        # ═══════════════════════════════════════════════════════════════════════════════

elif seccao == "sistema":
    lm_header("Sistema", "Configurações, histórico de alertas e glossário", "Sistema")
    tab_sys = st.tabs(["✅ Validação de Dados", "🔔 Notificações"])

    with st.expander("🕓 Histórico de Alertas", expanded=False):

            log = carregar_log()

            col_l1, col_l2 = st.columns([3,1])
            with col_l2:
                if st.button("🗑️ Limpar todo o histórico", type="secondary"):
                    if not os.path.exists(EXCEL_PATH):
                        st.session_state["alertas_log"] = []
                    else:
                        LOG_PATH.write_text("[]", encoding="utf-8")
                    st.rerun()
                if st.button("📥 Exportar histórico", type="secondary"):
                    if log:
                        df_log_exp = pd.DataFrame(log)
                        linhas_log = "".join([
                            f'<tr><td>{r["data"]}</td><td>{r["jogador"]}</td>'
                            f'<td>{r["tipo"]}</td><td>{r["descricao"]}</td><td>{r["valor"]}</td></tr>'
                            for r in log
                        ])
                        html_log = gerar_pdf_html(f"""
        <h1>Histórico de Alertas</h1>
        <table><tr><th>Data</th><th>Jogador</th><th>Tipo</th><th>Descrição</th><th>Valor</th></tr>
        {linhas_log}</table>""", "Historico_Alertas.html")
                        botao_download_html(html_log, "Historico_Alertas.html", "📥 Exportar (PDF)")

            if not log:
                st.info("Ainda não há alertas registados. Abre a página **🚨 Alertas do Dia** para gerar os primeiros alertas.")

            df_log = pd.DataFrame(log)
            df_log["data"] = pd.to_datetime(df_log["data"])
            df_log = df_log.sort_values("data", ascending=False)

            # ── Filtros ───────────────────────────────────────────────────────────────
            col_f1, col_f2, col_f3 = st.columns(3)
            tipos_log  = ["Todos"] + sorted(df_log["tipo"].unique().tolist())
            jogs_log   = ["Todos"] + sorted(df_log["jogador"].unique().tolist())
            tipo_sel_l = col_f1.selectbox("Tipo de alerta", tipos_log, key="log_tipo")
            jog_sel_l  = col_f2.selectbox("Jogador",        jogs_log,  key="log_jog")

            df_log_f = df_log.copy()
            if tipo_sel_l != "Todos": df_log_f = df_log_f[df_log_f["tipo"] == tipo_sel_l]
            if jog_sel_l  != "Todos": df_log_f = df_log_f[df_log_f["jogador"] == jog_sel_l]

            # ── KPIs ─────────────────────────────────────────────────────────────────
            k1,k2,k3,k4 = st.columns(4)
            k1.metric("Total de alertas",        len(df_log_f))
            k2.metric("Jogadores com alertas",   df_log_f["jogador"].nunique())
            k3.metric("Alertas hoje",
                      len(df_log_f[df_log_f["data"].dt.date == date.today()]))
            k4.metric("Alerta mais recente",
                      df_log_f["data"].max().strftime("%d/%m %H:%M") if not df_log_f.empty else "—")

            st.divider()

            # ── Gráfico de frequência de alertas no tempo ────────────────────────────
            st.markdown('<p class="section-title">Frequência de Alertas ao Longo do Tempo</p>', unsafe_allow_html=True)
            df_log_f["dia"] = df_log_f["data"].dt.date
            freq = df_log_f.groupby(["dia","tipo"]).size().reset_index(name="n")
            if not freq.empty:
                fig_freq = px.bar(freq, x="dia", y="n", color="tipo",
                                  color_discrete_sequence=px.colors.qualitative.Bold,
                                  labels={"dia":"Data","n":"Nº Alertas","tipo":"Tipo"})
                fig_freq.update_layout(
                    height=300, plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                    margin=dict(t=10), legend_title="",
                )
                st.plotly_chart(fig_freq, use_container_width=True)

            # ── Alertas por jogador ───────────────────────────────────────────────────
            st.markdown('<p class="section-title">Alertas por Jogador</p>', unsafe_allow_html=True)
            jog_count = df_log_f.groupby("jogador").size().sort_values(ascending=True).reset_index(name="n")
            fig_jog_log = go.Figure(go.Bar(
                y=jog_count["jogador"], x=jog_count["n"],
                orientation="h", marker_color="#e63946",
                text=jog_count["n"], textposition="outside",
            ))
            fig_jog_log.update_layout(
                height=max(200, len(jog_count)*40),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="rgba(255,255,255,0.85)", xaxis_title="Nº de alertas", margin=dict(t=10),
            )
            st.plotly_chart(fig_jog_log, use_container_width=True)

            # ── Timeline de alertas ───────────────────────────────────────────────────
            st.divider()
            st.markdown('<p class="section-title">📋 Registo Detalhado</p>', unsafe_allow_html=True)

            COR_TIPO = {"ACWR": "#e74c3c", "Wellness": "#f39c12", "Vmáx": "#3498db"}
            for _, row in df_log_f.head(100).iterrows():
                cor_t = COR_TIPO.get(row["tipo"], "#888")
                st.markdown(
                    f'<div style="border-left:4px solid {cor_t};padding:8px 12px;margin:4px 0;'
                    f'background:{cor_t}15;border-radius:0 8px 8px 0">'
                    f'<span style="font-size:0.75rem;color:#aaa">{row["data"].strftime("%d/%m/%Y %H:%M")}</span> '
                    f'<span style="background:{cor_t};color:white;padding:2px 8px;border-radius:4px;'
                    f'font-size:0.75rem;font-weight:700;margin:0 6px">{row["tipo"]}</span>'
                    f'<b>{row["jogador"]}</b> — {row["descricao"]} '
                    f'<span style="color:{cor_t};font-weight:700">({row["valor"]})</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            if len(df_log_f) > 100:
                st.caption(f"A mostrar os 100 alertas mais recentes de {len(df_log_f)} total.")


        # ═══════════════════════════════════════════════════════════════════════════════
        # VISTA: GLOSSÁRIO
        # ═══════════════════════════════════════════════════════════════════════════════

    with tab_sys[0]:

            if st.button("🔍 Validar agora", type="primary"):
                with st.spinner("A analisar..."):
                    erros, avisos, ok_list = validar_dados(df)

                total = len(erros) + len(avisos) + len(ok_list)
                score = int(len(ok_list)/total*100) if total > 0 else 0
                cor_s = "#2ecc71" if score>=80 else "#f39c12" if score>=60 else "#e74c3c"

                col_sc, col_res = st.columns([1,3])
                col_sc.markdown(f'<div style="background:{cor_s}22;border:3px solid {cor_s};border-radius:16px;padding:20px;text-align:center"><div style="font-size:0.9rem;color:#aaa">Qualidade</div><div style="font-size:3rem;font-weight:900;color:{cor_s}">{score}%</div></div>', unsafe_allow_html=True)
                col_res.metric("❌ Erros críticos", len(erros))
                col_res.metric("⚠️ Avisos", len(avisos))
                col_res.metric("✅ OK", len(ok_list))

                st.divider()
                for e in erros:   st.error(e)
                for a in avisos:  st.warning(a)
                for o in ok_list: st.success(o)

                st.divider()
                st.markdown("### 🔍 Valores únicos por coluna crítica")
                for col in ["Tipo","Dia MD","Posição","Microciclo (Nr)"]:
                    if col in df.columns:
                        vals = df[col].dropna().unique()
                        with st.expander(f"**{col}** — {len(vals)} valores únicos"):
                            st.write(sorted([str(v) for v in vals]))

                cols_crit = get_mets_gps(df)
                df_nulos = df[df[cols_crit].isna().any(axis=1)][cols_crit]
                if df_nulos.empty:
                    st.success("✅ Nenhum registo com campos críticos em falta!")
                else:
                    st.warning(f"{len(df_nulos)} registos com campos críticos em falta:")
                    st.dataframe(df_nulos, use_container_width=True)
            else:
                st.info("Clica em **🔍 Validar agora** para analisar a qualidade dos dados.")






    with tab_sys[1]:

            tab_n1, tab_n2 = st.tabs(["📧 Email", "📱 WhatsApp"])

            with tab_n1:
                st.markdown("### Configuração de Email (Gmail)")
                with st.expander("ℹ️ Como criar uma App Password no Gmail"):
                    st.markdown("""
        1. Vai a **https://myaccount.google.com**
        2. Clica em **Segurança** → **Palavras-passe para apps**
        3. Seleciona **Outra (nome personalizado)** → escreve "LoadMonitor"
        4. Copia a password de 16 caracteres e usa-a abaixo
                    """)
                col_e1, col_e2 = st.columns(2)
                smtp_user = col_e1.text_input("📧 Email Gmail", placeholder="preparadorfisico@gmail.com", key="smtp_user")
                smtp_pass = col_e2.text_input("🔑 App Password", type="password", key="smtp_pass")
                destinatarios = st.text_input("📨 Destinatários (separar por vírgula)", placeholder="treinador@clube.pt, medico@clube.pt", key="smtp_dest")

                st.divider()
                acwr_dict_n = calcular_acwr_global(df)
                alertas_atuais = []
                for jog, dados in acwr_dict_n.items():
                    v = dados["acwr"]; estado = cor_acwr(v)
                    if "RISCO" in estado or "ATENÇÃO" in estado:
                        alertas_atuais.append({"jogador": jog, "tipo": "ACWR", "descricao": f"ACWR = {v:.2f} — {estado}", "valor": f"{v:.2f}"})
                ultima_n = df.sort_values("Data").groupby("Jogador").last().reset_index()
                for _, row in ultima_n.iterrows():
                    hi = row.get("Hooper Index", np.nan)
                    if pd.notna(hi) and hi >= 14:
                        alertas_atuais.append({"jogador": row["Jogador"], "tipo": "Wellness", "descricao": f"Hooper Index elevado ({hi:.0f}/20)", "valor": f"{hi:.0f}"})

                st.markdown(f"**{len(alertas_atuais)} alertas ativos:**")
                for a in alertas_atuais:
                    cor_a = "#e74c3c" if a["tipo"] == "ACWR" else "#f39c12"
                    st.markdown(f'<div style="border-left:3px solid {cor_a};padding:6px 12px;margin:3px 0;background:{cor_a}15;border-radius:0 8px 8px 0;font-size:0.82rem"><b>{a["jogador"]}</b> — {a["descricao"]}</div>', unsafe_allow_html=True)
                if not alertas_atuais:
                    st.success("✅ Nenhum alerta ativo.")

                st.divider()
                if st.button("📧 Enviar Email Agora", type="primary", disabled=not (smtp_user and smtp_pass and destinatarios)):
                    dests = [d.strip() for d in destinatarios.split(",") if d.strip()]
                    with st.spinner("A enviar..."):
                        for dest in dests:
                            ok, msg = enviar_email_alertas(dest, smtp_user, smtp_pass, alertas_atuais)
                            st.caption(f"{dest}: {msg}")
                    if any(ok for ok, _ in [enviar_email_alertas(d.strip(), smtp_user, smtp_pass, alertas_atuais) for d in dests]):
                        st.success("✅ Email enviado!")

            with tab_n2:
                st.markdown("### Partilhar Alertas via WhatsApp")
                acwr_dict_wa = calcular_acwr_global(df)
                linhas_wa = [f"🚨 *Alertas de Carga — {datetime.now().strftime('%d/%m/%Y')}*\n"]
                for jog, dados in acwr_dict_wa.items():
                    v = dados["acwr"]; estado = cor_acwr(v)
                    if "RISCO" in estado: linhas_wa.append(f"🔴 *{jog}* — ACWR {v:.2f} (RISCO)")
                    elif "ATENÇÃO" in estado: linhas_wa.append(f"🟡 *{jog}* — ACWR {v:.2f} (ATENÇÃO)")
                ultima_wa = df.sort_values("Data").groupby("Jogador").last().reset_index()
                for _, row in ultima_wa.iterrows():
                    hi = row.get("Hooper Index", np.nan)
                    if pd.notna(hi) and hi >= 14:
                        linhas_wa.append(f"⚠️ *{row['Jogador']}* — Hooper {hi:.0f}/20")
                if len(linhas_wa) == 1:
                    linhas_wa.append("✅ Sem alertas ativos — equipa OK!")
                import urllib.parse
                mensagem_wa = "\n".join(linhas_wa)
                wa_url = f"https://wa.me/?text={urllib.parse.quote(mensagem_wa)}"
                st.markdown(f'<a href="{wa_url}" target="_blank" style="display:inline-block;padding:14px 28px;background:#25D366;color:white;border-radius:10px;text-decoration:none;font-weight:bold;font-size:1rem">📱 Abrir WhatsApp com os Alertas</a>', unsafe_allow_html=True)
                st.code(mensagem_wa, language=None)


        # ═══════════════════════════════════════════════════════════════════════════════
        # 🦵 TESTES NEUROMUSCULARES
        # ═══════════════════════════════════════════════════════════════════════════════

    with st.expander("📖 Glossário", expanded=False):

            nivel = st.radio("Nível de explicação", ["🟢 Simples (não-especialista)", "🔵 Técnico (especialista)"],
                             horizontal=True, key="gloss_nivel")
            simples = nivel.startswith("🟢")

            pesquisa = st.text_input("🔍 Pesquisar métrica...", key="gloss_pesq").lower()

            st.divider()

            for nome, info in GLOSSARIO.items():
                if pesquisa and pesquisa not in nome.lower() and pesquisa not in info["simples"].lower():
                    continue
                with st.expander(f"**{nome}**"):
                    if simples:
                        st.markdown(f"📌 {info['simples']}")
                    else:
                        st.markdown(f"🔬 **Definição técnica:** {info['tecnico']}")
                        st.markdown(f"📌 **Em linguagem simples:** {info['simples']}")

                    if info["zonas"]:
                        st.markdown("**Zonas de referência:**")
                        cols_z = st.columns(len(info["zonas"]))
                        for i, (zona, valor) in enumerate(info["zonas"].items()):
                            cols_z[i].markdown(
                                f'<div style="background:#1e2330;border-radius:8px;padding:8px;text-align:center">'
                                f'<div style="font-size:0.85rem;font-weight:700">{zona}</div>'
                                f'<div style="font-size:0.8rem;color:#aaa">{valor}</div>'
                                f'</div>',
                                unsafe_allow_html=True
                            )

            st.divider()
            st.markdown("""
            ### 📚 Referências Bibliográficas
            - **Foster et al. (2001)** — A New Approach to Monitoring Exercise Training. *Journal of Strength and Conditioning Research.*
            - **Gabbett (2016)** — The training-injury prevention paradox. *British Journal of Sports Medicine.*
            - **Malone et al. (2017)** — High chronic training loads and exposure to bouts of maximal velocity running. *Journal of Science and Medicine in Sport.*
            - **Hooper & Mackinnon (1995)** — Monitoring overtraining in athletes. *Sports Medicine.*
            """)




        # ═══════════════════════════════════════════════════════════════════════════════
        # VISTA: RESUMO DO DIA
        # ═══════════════════════════════════════════════════════════════════════════════

# ── Rodapé ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("Dashboard de Monitorização de Carga · Belenenses · Gerado automaticamente a partir do ficheiro Excel · Para atualizar, clica em '🔄 Atualizar Dados' na barra lateral.")
