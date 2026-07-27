"""
LoadMonitorSystem — Ficheiro Principal
Arquitectura modular: utils/ + pages/
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os, io, json
from datetime import datetime

# ── Stripe ───────────────────────────────────────────────────────────────────
try:
    from auth_stripe import verificar_retorno_stripe
    STRIPE_DISPONIVEL = True
except ImportError:
    STRIPE_DISPONIVEL = False
    def verificar_retorno_stripe(): pass


# ── Módulos da app ───────────────────────────────────────────────────────────
from utils.dados import carregar_dados_safe, get_mets_gps
from utils.calculos import calcular_acwr_global, cor_acwr
from utils.ui_safe import aplicar_tema_graficos

aplicar_tema_graficos()

st.set_page_config(
    page_title="LoadMonitorSystem",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sentry — observabilidade de erros em produção ────────────────────────────
try:
    import sentry_sdk
    _sentry_dsn = ""
    try:
        _sentry_dsn = str(st.secrets.get("SENTRY_DSN", "")).strip()
    except Exception:
        pass
    if not _sentry_dsn:
        _sentry_dsn = os.environ.get("SENTRY_DSN", "").strip()

    if _sentry_dsn:
        def _sentry_filtro(event, hint):
            """Filtra erros banais e protege PII. Devolve None para descartar."""
            exc_info = hint.get("exc_info") if hint else None
            if exc_info:
                exc_type, exc_value, _ = exc_info
                if exc_type:
                    msg = str(exc_value).lower()
                    if any(t in msg for t in ["password incorret", "sessão expir",
                                               "tentativas falhadas", "bloqueada"]):
                        return None
            if event.get("request") and event["request"].get("query_string"):
                event["request"]["query_string"] = "[Filtered]"
            return event

        sentry_sdk.init(
            dsn=_sentry_dsn,
            traces_sample_rate=0.1,
            profiles_sample_rate=0.0,
            send_default_pii=False,
            environment=os.environ.get("ENVIRONMENT", "production"),
            release="loadmonitor@1.0.0",
            before_send=_sentry_filtro,
        )
except ImportError:
    pass


# ── CSS personalizado ─────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    :root {
        --lm-accent:#e63946;
        --lm-accent-2:#ff6b75;
        --lm-ink:#0f172a;
        --lm-surface:#111827;
        --lm-panel:#ffffff;
        --lm-mono:'JetBrains Mono',ui-monospace,monospace;
        --lm-sans:'Inter',-apple-system,BlinkMacSystemFont,system-ui,sans-serif;
    }
    html, body, .stApp, .stMainBlockContainer, [data-testid="stSidebar"], [data-testid="stVerticalBlock"] {
        background: linear-gradient(135deg, #0f172a 0%, #111827 45%, #1e293b 100%) !important;
        color: #f8fafc !important;
        font-family: var(--lm-sans) !important;
    }
    .stApp {
        background-image: radial-gradient(circle at top right, rgba(230,57,70,0.26), transparent 28%),
                          radial-gradient(circle at bottom left, rgba(37,99,235,0.20), transparent 24%);
    }
    .block-container {
        padding-top: 1.4rem !important;
        padding-bottom: 2rem !important;
    }
    .stMetric, div[data-testid="stMetric"], [data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255,255,255,0.96) !important;
        color: #0f172a !important;
        border: 1px solid rgba(15,23,42,0.08) !important;
        border-radius: 18px !important;
        box-shadow: 0 14px 30px rgba(0,0,0,0.16) !important;
    }
    div[data-testid="stPlotlyChart"] > div {
        border-radius: 18px !important;
        overflow: hidden !important;
        box-shadow: 0 16px 36px rgba(0,0,0,0.18) !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        background: #ffffff !important;
    }
    .stButton > button {
        border-radius: 999px !important;
        background: linear-gradient(135deg, #e63946 0%, #ff6b75 100%) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 10px 24px rgba(230,57,70,0.25) !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 999px !important;
        background: rgba(255,255,255,0.10) !important;
        color: #e2e8f0 !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #e63946 0%, #ff6b75 100%) !important;
        color: white !important;
    }
    h1, h2, h3, h4, h5, h6, .stMarkdown {
        color: #f8fafc !important;
        font-family: var(--lm-sans) !important;
    }
    .section-title {
        color: #f8fafc !important;
        font-weight: 800 !important;
        letter-spacing: 0.02em !important;
        font-size: 1.05rem !important;
        margin-bottom: 10px !important;
    }
    .lm-hero {
        background: linear-gradient(135deg, rgba(230,57,70,0.20), rgba(37,99,235,0.18));
        border: 1px solid rgba(255,255,255,0.14);
        border-radius: 22px;
        padding: 20px 24px;
        margin-bottom: 18px;
        box-shadow: 0 18px 38px rgba(0,0,0,0.16);
    }
    .lm-hero-chip {
        display: inline-block;
        background: rgba(255,255,255,0.14);
        color: #f8fafc;
        border-radius: 999px;
        padding: 6px 12px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        margin-bottom: 10px;
    }
    .lm-hero-title {
        font-size: 1.45rem;
        font-weight: 800;
        color: #ffffff;
        margin-bottom: 6px;
    }
    .lm-hero-subtitle {
        color: #dbeafe;
        font-size: 0.98rem;
        line-height: 1.55;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="lm-hero">
        <div class="lm-hero-chip">Nova visão do dashboard</div>
        <div class="lm-hero-title">LoadMonitorSystem</div>
        <div class="lm-hero-subtitle">Painel de carga, recuperação e risco com uma apresentação mais clara, visual e orientada para decisão.</div>
    </div>
    """,
    unsafe_allow_html=True,
)
EXCEL_PATH = "LoadMonitorSystem_Template.xlsx"

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
    .main .block-container {
        padding-top: 8vh !important;
        padding-bottom: 5vh !important;
        max-width: 100% !important;
    }

    .login-container {
        max-width: 520px;
        margin: 0 auto 28px auto;
        padding: 0 20px;
        width: 100%;
    }
    .login-logo-wrap {
        display: flex; align-items: center; justify-content: center;
        gap: 14px; margin-bottom: 6px;
    }
    .login-mark {
        width: 40px; height: 40px;
        background: #ffffff;
        border-radius: 8px;
        position: relative;
    }
    .login-mark::before {
        content: ''; position: absolute; inset: 9px;
        background: #e63946; border-radius: 3px;
    }
    .login-logo {
        font-family: 'Inter', -apple-system, sans-serif;
        font-size: 2.4rem; font-weight: 700;
        letter-spacing: -0.025em; text-align: center;
    }
    .login-logo span { color: #e63946; }
    .login-tagline {
        text-align: center; color: #999; font-size: 0.85rem;
        letter-spacing: 2px; text-transform: uppercase;
        margin-bottom: 36px; font-weight: 600;
    }
    .trial-badge {
        background: linear-gradient(135deg, #e63946, #c0392b);
        color: white; text-align: center; padding: 14px 18px;
        border-radius: 10px; font-size: 0.95rem; font-weight: 600;
        margin-bottom: 24px; letter-spacing: 0.3px;
    }
    </style>
    <div class="login-container">
        <div class="login-logo-wrap">
            <div class="login-mark"></div>
            <div class="login-logo">Load<span>Monitor</span></div>
        </div>
        <div class="login-tagline">Monitorização de Carga Desportiva</div>
        <div class="trial-badge">🎉 Demo aberta — acesso completo a todas as funcionalidades</div>
    </div>
    """, unsafe_allow_html=True)

    col_center = st.columns([1, 3, 1])[1]
    with col_center:
        tab_login, tab_registo, tab_reset = st.tabs(["Entrar", "Criar Conta", "Esqueci-me"])

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

            st.markdown(
                "<div style='margin-top:8px;margin-bottom:4px'></div>",
                unsafe_allow_html=True
            )
            aceita_termos = st.checkbox(
                "Li e aceito os Termos de Utilização e a Política de Privacidade",
                key="reg_aceita_termos",
                value=False
            )
            st.markdown(
                "<p style='color:#888;font-size:0.78rem;margin-top:-8px;margin-bottom:14px;line-height:1.5'>"
                "Ver <a href='https://loadmonitorsystem.com/termos.html' target='_blank' style='color:#e63946;text-decoration:none'>Termos</a> "
                "· <a href='https://loadmonitorsystem.com/privacidade.html' target='_blank' style='color:#e63946;text-decoration:none'>Privacidade</a>"
                "</p>",
                unsafe_allow_html=True
            )

            if st.button("Criar conta grátis →", type="primary", use_container_width=True, key="btn_reg"):
                if not aceita_termos:
                    st.error("Para criar conta tens de aceitar os Termos e a Política de Privacidade.")
                elif pwd_r != pwd_r2:
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

        with tab_reset:
            st.markdown(
                "<p style='color:#888;font-size:0.88rem;margin-bottom:12px'>"
                "Insere o teu email e enviamos-te um link para repor a password."
                "</p>",
                unsafe_allow_html=True
            )
            email_reset = st.text_input("Email", key="reset_email", placeholder="preparador@email.com")
            if st.button("Enviar link →", type="primary", use_container_width=True, key="btn_reset_req"):
                if not email_reset or "@" not in email_reset:
                    st.error("Insere um email válido.")
                else:
                    try:
                        from auth import gerar_token_reset
                        gerar_token_reset(email_reset)
                    except Exception:
                        pass
                    st.success("Se o email estiver registado, vais receber um link em alguns segundos. Verifica a tua caixa de entrada (e spam).")
    st.stop()

# ── Verificar autenticação ────────────────────────────────────────────────────
_DEV_MODE = False
try:
    _DEV_MODE = str(st.secrets.get("DEV_MODE", "")).lower() in ["true", "1", "yes"]
except:
    _DEV_MODE = False

# ── Página de reset password ──────────────────────────────────────────────────
_qp = st.query_params
_reset_token_url = _qp.get("reset_token", "")
if _reset_token_url and not _DEV_MODE:
    st.markdown("""
    <div style="max-width:420px;margin:60px auto;padding:0 20px">
        <div style="display:flex;align-items:center;justify-content:center;gap:12px;margin-bottom:6px">
            <div style="width:30px;height:30px;background:#ffffff;border-radius:7px;position:relative">
                <div style="position:absolute;inset:7px;background:#e63946;border-radius:3px"></div>
            </div>
            <div style="font-family:'Inter',sans-serif;font-size:1.8rem;font-weight:600;
            letter-spacing:-0.025em">Load<span style="color:#e63946">Monitor</span></div>
        </div>
        <div style="text-align:center;color:#888;font-size:0.78rem;
        letter-spacing:2px;text-transform:uppercase;margin-bottom:24px;font-weight:500">
        Repor Password</div>
    </div>
    """, unsafe_allow_html=True)

    _col_rst = st.columns([1, 2, 1])[1]
    with _col_rst:
        st.markdown("Define a tua nova password (mínimo 8 caracteres).")
        _new_pwd  = st.text_input("Nova password", type="password", key="rst_new_pwd")
        _new_pwd2 = st.text_input("Confirmar password", type="password", key="rst_new_pwd2")
        if st.button("Repor password", type="primary", use_container_width=True, key="btn_rst_apply"):
            if _new_pwd != _new_pwd2:
                st.error("As passwords não coincidem.")
            elif len(_new_pwd) < 8:
                st.error("A password deve ter pelo menos 8 caracteres.")
            else:
                try:
                    from auth import aplicar_reset_password
                    res_rst = aplicar_reset_password(_reset_token_url, _new_pwd)
                except Exception as e:
                    res_rst = {"sucesso": False, "erro": str(e)}
                if res_rst.get("sucesso"):
                    st.success("✅ Password atualizada. Já podes fazer login com a nova password.")
                    st.markdown(
                        "<a href='/' style='display:inline-block;margin-top:8px;"
                        "color:#e63946;text-decoration:none;font-weight:600'>← Voltar ao login</a>",
                        unsafe_allow_html=True
                    )
                else:
                    st.error(res_rst.get("erro", "Não foi possível repor a password."))
    st.stop()

if _DEV_MODE:
    st.session_state["lm_user"] = {
        "id": 1, "nome": "Dev User", "email": "dev@loadmonitor.io",
        "clube": "Dev Mode", "plano": "pro",
        "trial_fim": None, "dias_trial": None,
    }
    st.session_state["lm_token"] = "dev_token_bypass"

elif not AUTH_DISPONIVEL:
    st.session_state["lm_user"] = {
        "id": 0, "nome": "Demo", "clube": "Demo",
        "plano": "pro", "trial_fim": None, "dias_trial": None,
    }
else:
    # Cache 60s — evita Postgres a cada render (Patch performance #1)
    @st.cache_data(ttl=60, show_spinner=False)
    def _ver_sessao_cached(_token):
        return verificar_sessao(_token)

    token = st.session_state.get("lm_token")
    if token:
        user = _ver_sessao_cached(token)
        if user:
            st.session_state["lm_user"] = user
        else:
            st.session_state.pop("lm_token", None)
            st.session_state.pop("lm_user", None)

    if "lm_user" not in st.session_state:
        ecrã_login()

# ── Verificar retorno do Stripe após pagamento ────────────────────────────────
verificar_retorno_stripe()

# ── DEBUG: botão para testar Sentry ───────────────────────────────────────────
try:
    if str(st.secrets.get("SENTRY_TEST", "")).lower() in ["true", "1"]:
        if st.button("🐛 Disparar erro de teste para Sentry"):
            try:
                raise RuntimeError("Teste manual Sentry — LoadMonitor — pode ser ignorado")
            except Exception as _e:
                try:
                    import sentry_sdk
                    event_id = sentry_sdk.capture_exception(_e)
                    st.success(f"✅ Erro enviado para Sentry. Event ID: {event_id}")
                    st.caption("Vai a sentry.io → Issues e procura este event ID. Aparece em 30-60s.")
                except ImportError:
                    st.error("❌ sentry_sdk não está instalado. Verifica requirements.txt.")
                except Exception as _se:
                    st.error(f"❌ Sentry com problema: {_se}")
except Exception:
    pass

# ── Mostrar página de upgrade se solicitado ───────────────────────────────────
if st.session_state.get("mostrar_upgrade") and STRIPE_DISPONIVEL:
    st.markdown("## 🚀 Plano Pro — Em desenvolvimento")
    st.markdown(
        "Estamos em fase de demonstração. Todas as funcionalidades estão "
        "disponíveis durante o desenvolvimento. Quando o Plano Pro abrir, "
        "avisamos com antecedência."
    )

    col_up1, col_up2 = st.columns([1, 1], gap="large")
    with col_up1:
        st.markdown("""**Funcionalidades já disponíveis durante a demo:**
- ✅ Atletas e equipas ilimitados
- ✅ Todos os alertas automáticos
- ✅ Análise GPS avançada (Vmáx, Sprint)
- ✅ Calculadora científica de exercícios
- ✅ Relatórios PDF personalizáveis
- ✅ Notificações email
- ✅ Planeado vs Realizado % do jogo""")

    with col_up2:
        st.markdown("**Recebe novidades**")
        st.markdown(
            "Estamos em desenvolvimento ativo. Inscreve-te na lista para "
            "seres avisado das novidades importantes — sem spam, só o que interessa."
        )
        st.markdown(
            '<a href="https://loadmonitorsystem.com/#waitlist" target="_blank" '
            'style="display:block;background:#e63946;color:white;text-align:center;'
            'padding:14px;border-radius:8px;font-weight:700;font-size:1rem;'
            'text-decoration:none;margin-top:12px">'
            '📋 Receber novidades →</a>',
            unsafe_allow_html=True
        )
        st.caption("Avisamos-te com novidades importantes do desenvolvimento.")

    st.divider()
    st.info(
        "💡 **Durante a fase de demo tens acesso completo gratuito** a todas as "
        "funcionalidades da app. Aproveita para testar e dar-nos feedback — "
        "o teu feedback é o nosso preço durante esta fase."
    )

    if st.button("← Voltar à app", key="btn_voltar_upgrade"):
        st.session_state.pop("mostrar_upgrade", None)
        st.rerun()
    st.stop()

# ── Fonte de dados ─────────────────────────────────────────────────────────────
IS_CLOUD = True

if IS_CLOUD:
    _uid = st.session_state.get("lm_user", {}).get("id", 0)
    _excel_key = f"excel_bytes_{_uid}"
    if _excel_key not in st.session_state:
        st.session_state[_excel_key] = None
    st.session_state["excel_bytes"] = st.session_state[_excel_key]
    st.session_state["_excel_key"]  = _excel_key

_lm_user = st.session_state.get("lm_user", {})
_lm_nome  = _lm_user.get("nome", "Utilizador")
_lm_clube = _lm_user.get("clube", "")
_lm_plano = _lm_user.get("plano", "free")
_lm_trial = _lm_user.get("dias_trial")

with st.sidebar:
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] {
        width: 320px !important;
        min-width: 320px !important;
        max-width: 320px !important;
        background: linear-gradient(180deg, #0a0e14 0%, #0d1421 50%, #0b1018 100%) !important;
        border-right: 1px solid rgba(255,255,255,0.04) !important;
    }

    section[data-testid="stSidebar"] > div:first-child {
        padding: 0 !important;
        width: 320px !important;
    }

    section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
        padding: 20px 16px 24px 16px !important;
    }

    section[data-testid="stSidebar"] [data-testid="stSidebarResizeHandle"] { display: none !important; }

    .lm-side-head {
        padding: 4px 4px 16px 4px;
        border-bottom: 1px solid rgba(255,255,255,0.06);
        margin-bottom: 16px;
    }
    .lm-side-logo-wrap {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 6px;
    }
    .lm-side-mark {
        width: 26px;
        height: 26px;
        border-radius: 6px;
        background: linear-gradient(135deg, #e63946, #c0392b);
        flex-shrink: 0;
    }
    .lm-side-logo {
        font-size: 1.05rem;
        font-weight: 800;
        color: white;
        letter-spacing: -0.3px;
    }
    .lm-side-logo span {
        color: #e63946;
    }
    .lm-side-tag {
        font-size: 0.65rem;
        font-weight: 700;
        color: rgba(255,255,255,0.4);
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-left: 36px;
    }

    .lm-side-user {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px;
        padding: 12px 14px;
        margin-bottom: 16px;
    }
    .lm-side-user-name {
        font-size: 0.88rem;
        font-weight: 600;
        color: white;
        margin-bottom: 4px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .lm-side-user-plan {
        display: inline-block;
        font-size: 0.62rem;
        font-weight: 700;
        letter-spacing: 1.5px;
        padding: 3px 8px;
        border-radius: 4px;
    }
    .lm-side-user-plan.free {
        background: rgba(255,255,255,0.08);
        color: rgba(255,255,255,0.6);
    }
    .lm-side-user-plan.pro {
        background: linear-gradient(135deg, #e63946, #c0392b);
        color: white;
    }

    section[data-testid="stSidebar"] hr {
        margin: 16px 0 !important;
        border-color: rgba(255,255,255,0.06) !important;
    }

    section[data-testid="stSidebar"] h3 {
        font-size: 0.7rem !important;
        font-weight: 700 !important;
        color: rgba(255,255,255,0.45) !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
        margin: 4px 0 12px 0 !important;
        padding: 0 !important;
    }

    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        font-size: 0.82rem !important;
        color: rgba(255,255,255,0.7) !important;
        margin: 0 0 8px 0 !important;
    }

    section[data-testid="stSidebar"] .stButton > button {
        width: 100% !important;
        padding: 9px 14px !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        transition: all 0.15s ease !important;
        margin: 0 !important;
    }
    section[data-testid="stSidebar"] .stButton > button[kind="secondary"] {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        color: rgba(255,255,255,0.85) !important;
    }
    section[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
        background: rgba(255,255,255,0.08) !important;
        border-color: rgba(230,57,70,0.4) !important;
        color: white !important;
    }
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #e63946, #c0392b) !important;
        border: none !important;
        color: white !important;
    }
    section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #f04050, #d04030) !important;
        transform: translateY(-1px);
    }

    section[data-testid="stSidebar"] [data-testid="stFileUploader"] {
        margin: 0 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
        background: rgba(230,57,70,0.04) !important;
        border: 1.5px dashed rgba(230,57,70,0.3) !important;
        border-radius: 10px !important;
        padding: 16px 12px !important;
        min-height: auto !important;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]:hover {
        background: rgba(230,57,70,0.08) !important;
        border-color: rgba(230,57,70,0.5) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] small,
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] span {
        font-size: 0.72rem !important;
        color: rgba(255,255,255,0.6) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {
        font-size: 0.78rem !important;
        padding: 6px 12px !important;
    }

    section[data-testid="stSidebar"] [data-testid="stMultiSelect"] label,
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] label,
    section[data-testid="stSidebar"] [data-testid="stTextInput"] label {
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        color: rgba(255,255,255,0.7) !important;
        margin-bottom: 4px !important;
    }

    section[data-testid="stSidebar"] [data-baseweb="select"] > div,
    section[data-testid="stSidebar"] [data-baseweb="input"] > div {
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 8px !important;
        font-size: 0.82rem !important;
    }

    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        font-size: 0.72rem !important;
        color: rgba(255,255,255,0.4) !important;
        margin-top: 4px !important;
    }

    section[data-testid="stSidebar"] ::-webkit-scrollbar { width: 4px; }
    section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb {
        background: rgba(230,57,70,0.2);
        border-radius: 2px;
    }
    section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb:hover {
        background: rgba(230,57,70,0.4);
    }

    .lm-login-wrap {
        min-height: 80vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        padding: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="lm-side-head">
        <div class="lm-side-logo-wrap">
            <div class="lm-side-mark"></div>
            <div class="lm-side-logo">Load<span>Monitor</span></div>
        </div>
        <div class="lm-side-tag">Análise de Carga</div>
    </div>
    """, unsafe_allow_html=True)

    plano_class = "pro" if _lm_plano == "pro" else "free"
    plano_label = "DEMO" if _lm_plano == "pro" else "FREE"
    st.markdown(f"""
    <div class="lm-side-user">
        <div class="lm-side-user-name">{_lm_nome}</div>
        <span class="lm-side-user-plan {plano_class}">{plano_label}</span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    if IS_CLOUD:
        st.markdown("### 📤 Carregar Excel")
        uploaded = st.file_uploader(
            "Faz upload do ficheiro Excel",
            type=["xlsx", "csv"],
            help="Carrega o teu ficheiro Excel com os dados de carga",
            key="uploader"
        )
        if uploaded is not None:
            _bytes = uploaded.read()
            _ek = st.session_state.get("_excel_key", "excel_bytes_0")
            st.session_state[_ek]            = _bytes
            st.session_state["excel_bytes"]  = _bytes
            st.session_state["excel_filename"] = uploaded.name
            st.cache_data.clear()
            st.success(f"✅ {uploaded.name}")

        _ek_chk = st.session_state.get("_excel_key", "excel_bytes_0")
        if st.session_state.get(_ek_chk) is None:
            st.session_state["excel_bytes"] = None

        if st.session_state["excel_bytes"] is None:
            st.caption("👈 Faz upload do Excel para começar a usar a app")
            _excel_carregado = False
        else:
            _excel_carregado = True
            excel_path = io.BytesIO(st.session_state["excel_bytes"])
            excel_path.name = st.session_state.get("excel_filename", "data.xlsx")
    else:
        _excel_carregado = True
        excel_path = EXCEL_PATH

if not _excel_carregado:
    _tmpl_data = None
    for _tmpl_path in ["LoadMonitorSystem_Template.xlsx", "template.xlsx"]:
        try:
            with open(_tmpl_path, "rb") as _f:
                _tmpl_data = _f.read()
            break
        except FileNotFoundError:
            continue

    st.markdown("""
<div style="
    position:relative;
    background:linear-gradient(135deg,#0a0e14 0%,#161b22 60%,#1c1413 100%);
    border:1px solid rgba(230,57,70,0.15);
    border-radius:20px;
    padding:48px 40px;
    margin:8px 0 24px;
    overflow:hidden">
<div style="
    position:absolute;top:-100px;right:-80px;width:300px;height:300px;
    background:radial-gradient(circle,rgba(230,57,70,0.12),transparent 70%);
    pointer-events:none"></div>
<div style="position:relative;z-index:1">
<div style="
    display:inline-block;background:rgba(230,57,70,0.15);
    border:1px solid rgba(230,57,70,0.3);border-radius:6px;
    padding:4px 12px;font-size:0.7rem;font-weight:700;
    color:#e63946;letter-spacing:2px;margin-bottom:18px">
LOADMONITORSYSTEM</div>
<div style="
    font-size:2.2rem;font-weight:800;color:white;
    line-height:1.15;margin-bottom:12px;letter-spacing:-0.5px">
Bem-vindo!</div>
<div style="
    font-size:1rem;color:rgba(255,255,255,0.55);
    line-height:1.6;max-width:600px">
A plataforma de monitorização de carga e tomada de decisão<br>
para preparadores físicos.
</div></div></div>""", unsafe_allow_html=True)

    st.markdown("""
<div style="margin:8px 0 16px">
<div style="font-size:0.7rem;font-weight:700;color:#e63946;
letter-spacing:2.5px;margin-bottom:6px">COMO COMEÇAR</div>
<div style="font-size:1.4rem;font-weight:700;color:white;margin-bottom:18px">
Apenas 3 passos</div>
</div>

<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px;margin-bottom:24px">

<div style="
    background:linear-gradient(180deg,#161b22,#0d1421);
    border:1px solid rgba(255,255,255,0.06);
    border-top:3px solid #e63946;
    border-radius:14px;padding:24px 22px;
    transition:all 0.2s">
<div style="
    width:42px;height:42px;background:rgba(230,57,70,0.12);
    border-radius:10px;display:flex;align-items:center;
    justify-content:center;font-size:1.2rem;margin-bottom:14px">📤</div>
<div style="
    font-size:0.65rem;font-weight:700;color:#e63946;
    letter-spacing:2px;margin-bottom:6px">PASSO 1</div>
<div style="
    font-weight:600;color:white;margin-bottom:8px;font-size:1rem">
Carrega o teu Excel</div>
<div style="
    font-size:0.82rem;color:rgba(255,255,255,0.5);line-height:1.55">
Catapult, STATSports, Polar, FieldWiz, WIMU ou registos manuais. Aceita o que já usas.</div>
</div>

<div style="
    background:linear-gradient(180deg,#161b22,#0d1421);
    border:1px solid rgba(255,255,255,0.06);
    border-top:3px solid #e63946;
    border-radius:14px;padding:24px 22px">
<div style="
    width:42px;height:42px;background:rgba(230,57,70,0.12);
    border-radius:10px;display:flex;align-items:center;
    justify-content:center;font-size:1.2rem;margin-bottom:14px">⚡</div>
<div style="
    font-size:0.65rem;font-weight:700;color:#e63946;
    letter-spacing:2px;margin-bottom:6px">PASSO 2</div>
<div style="
    font-weight:600;color:white;margin-bottom:8px;font-size:1rem">
A app analisa</div>
<div style="
    font-size:0.82rem;color:rgba(255,255,255,0.5);line-height:1.55">
Deteta colunas automaticamente. Calcula ACWR, Hooper, Foster e mais.</div>
</div>

<div style="
    background:linear-gradient(180deg,#161b22,#0d1421);
    border:1px solid rgba(255,255,255,0.06);
    border-top:3px solid #e63946;
    border-radius:14px;padding:24px 22px">
<div style="
    width:42px;height:42px;background:rgba(230,57,70,0.12);
    border-radius:10px;display:flex;align-items:center;
    justify-content:center;font-size:1.2rem;margin-bottom:14px">🎯</div>
<div style="
    font-size:0.65rem;font-weight:700;color:#e63946;
    letter-spacing:2px;margin-bottom:6px">PASSO 3</div>
<div style="
    font-weight:600;color:white;margin-bottom:8px;font-size:1rem">
Toma decisões</div>
<div style="
    font-size:0.82rem;color:rgba(255,255,255,0.5);line-height:1.55">
Ranking, semáforos, alertas e relatórios prontos para a equipa técnica.</div>
</div>

</div>""", unsafe_allow_html=True)

    st.markdown("""
<div style="
    background:linear-gradient(135deg,#0d1421,#0a0e14);
    border:1px solid rgba(255,255,255,0.06);
    border-radius:16px;padding:24px 28px 20px;
    margin:8px 0">
<div style="
    font-size:0.7rem;font-weight:700;color:rgba(255,255,255,0.45);
    letter-spacing:2.5px;margin-bottom:6px">AINDA NÃO TENS EXCEL?</div>
<div style="
    font-size:1.05rem;font-weight:600;color:white;margin-bottom:14px">
Descarrega o template oficial e começa do zero</div>
</div>""", unsafe_allow_html=True)

    col_dl1, col_dl2 = st.columns([1, 1.5], gap="medium")

    with col_dl1:
        if _tmpl_data:
            st.download_button(
                "⬇️  Descarregar Template",
                data=_tmpl_data,
                file_name="LoadMonitorSystem_Template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="secondary",
                use_container_width=True,
            )
            st.caption("Formato .xlsx · 4 folhas · Compatível com Excel e LibreOffice")
        else:
            st.warning("Template não disponível. Contacta o suporte.")

    with col_dl2:
        st.markdown("""
<div style="font-size:0.72rem;font-weight:700;color:rgba(255,255,255,0.4);
letter-spacing:1.5px;margin-bottom:10px">O TEMPLATE INCLUI</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:0.82rem;color:rgba(255,255,255,0.7)">
<div>📊 Carga interna automática</div>
<div>💤 Hooper Index calculado</div>
<div>🏋️ Testes neuromusculares</div>
<div>📋 Carga planeada por Dia MD</div>
<div>🏃 Exercícios e calculadora</div>
<div>📖 Instruções incluídas</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div style="
    background:linear-gradient(135deg, rgba(230,57,70,0.12), rgba(230,57,70,0.06));
    border:1px solid rgba(230,57,70,0.3);
    border-radius:12px;padding:18px 22px;margin:24px 0 8px;
    display:flex;align-items:center;gap:16px;flex-wrap:wrap">
<div style="
    background:rgba(230,57,70,0.25);
    border-radius:8px;padding:10px 14px;
    font-size:1.3rem">⚡</div>
<div style="flex:1;min-width:200px">
<div style="font-size:1rem;font-weight:600;color:#ffffff;margin-bottom:4px">
Já tens Excel próprio? Funciona logo.</div>
<div style="font-size:0.85rem;color:rgba(255,255,255,0.75);line-height:1.5">
Catapult · STATSports · Polar · FieldWiz · WIMU · Excel manual — a app deteta automaticamente as colunas do teu ficheiro.
</div></div></div>""", unsafe_allow_html=True)

    st.stop()

with st.sidebar:

    if st.button("🔄 Atualizar Dados", type="primary", use_container_width=True):
        st.cache_data.clear()
        # Invalidar também o df cacheado em sessão (Patch performance #3)
        _uid_clear = st.session_state.get("lm_user", {}).get("id", 0)
        for _k in [f"_df_cache_{_uid_clear}",
                   f"_df_bytes_id_{_uid_clear}",
                   f"_df_err_{_uid_clear}"]:
            st.session_state.pop(_k, None)
        if IS_CLOUD and "excel_bytes" in st.session_state:
            pass
        st.rerun()

    if not IS_CLOUD:
        mod_time = os.path.getmtime(excel_path)
        st.caption(f"📅 Última modificação:\n{datetime.fromtimestamp(mod_time).strftime('%d/%m/%Y %H:%M')}")

    st.divider()

    # Carregar dados — cache estável em session_state (Patch performance #2)
    _uid_df = st.session_state.get("lm_user", {}).get("id", 0)
    _df_key = f"_df_cache_{_uid_df}"
    _df_bytes_id_key = f"_df_bytes_id_{_uid_df}"
    _df_err_key = f"_df_err_{_uid_df}"
    _current_bytes_id = id(st.session_state.get("excel_bytes"))

    if (st.session_state.get(_df_bytes_id_key) != _current_bytes_id
            or _df_key not in st.session_state):
        try:
            df, _load_err = carregar_dados_safe(excel_path)
            st.session_state[_df_key] = df
            st.session_state[_df_err_key] = _load_err
            st.session_state[_df_bytes_id_key] = _current_bytes_id
        except Exception as e:
            st.error(f"Erro ao ler o Excel:\n{e}")
            st.stop()
    else:
        df = st.session_state[_df_key]
        _load_err = st.session_state.get(_df_err_key)

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

    jogadores  = sorted(df["Jogador"].dropna().unique().tolist())
    microciclos = sorted(df["Microciclo (Nr)"].dropna().unique().tolist(), reverse=True)
    posicoes   = sorted(df["Posição"].dropna().unique().tolist()) if "Posição" in df.columns else []

    if STRIPE_DISPONIVEL:
        st.markdown("""<div style="background:linear-gradient(160deg,#1c0608,#2d0d10);
border:2px solid #e63946;border-radius:12px;padding:16px 14px;text-align:center;margin:8px 0">
<div style="font-size:0.62rem;font-weight:700;color:#e63946;letter-spacing:3px;margin-bottom:6px">🚀 PLANO PRO</div>
<div style="font-size:0.95rem;font-weight:700;color:white;line-height:1.3;margin-bottom:6px">Em desenvolvimento</div>
<div style="font-size:0.7rem;color:rgba(255,255,255,0.6);margin:4px 0 10px;line-height:1.5">
Estamos em fase de demo.<br>
<span style="color:#e63946;font-weight:700">Acesso completo gratuito agora</span></div>
<div style="font-size:0.7rem;color:rgba(255,255,255,0.55);text-align:left;line-height:1.8">
✓ Atletas e equipas ilimitados<br>✓ Todos os alertas automáticos<br>✓ Análise GPS avançada<br>✓ Relatórios PDF personalizáveis
</div></div>""", unsafe_allow_html=True)
        st.link_button("📋 Receber novidades",
                        "https://loadmonitorsystem.com/#waitlist",
                        type="primary", use_container_width=True)
        st.divider()

    if st.button("🚪 Sair", key="btn_logout", use_container_width=True):
        if AUTH_DISPONIVEL:
            fazer_logout(st.session_state.get("lm_token",""))
        _uid_out = st.session_state.get("lm_user", {}).get("id", 0)
        for _k in [f"excel_bytes_{_uid_out}", "excel_bytes", "_excel_key", "excel_filename"]:
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


df_f = df.copy()
if mc_sel:
    df_f = df_f[df_f["Microciclo (Nr)"].isin(mc_sel)]
if pos_sel and "Posição" in df_f.columns:
    df_f = df_f[df_f["Posição"].isin(pos_sel)]

df_f_dia = df_f.copy()
if dia_md_sel and "Dia MD" in df_f_dia.columns:
    df_f_dia = df_f_dia[df_f_dia["Dia MD"].isin(dia_md_sel)]


def get_preferencia(user_id, chave, default=None):
    try:
        import auth
        uid = int(user_id) if user_id is not None else 0
        with auth.get_conn() as conn:
            with conn.cursor() as c:
                c.execute("SELECT valor FROM preferencias WHERE utilizador_id=%s AND chave=%s",
                          (uid, chave))
                row = c.fetchone()
                if not row or row[0] is None:
                    return default
                return json.loads(row[0])
    except Exception:
        return default

def set_preferencia(user_id, chave, valor) -> bool:
    try:
        import auth
        uid = int(user_id) if user_id is not None else 0
        with auth.get_conn() as conn:
            with conn.cursor() as c:
                c.execute("""
                    INSERT INTO preferencias (utilizador_id, chave, valor, atualizado_em)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (utilizador_id, chave) DO UPDATE SET
                        valor = EXCLUDED.valor,
                        atualizado_em = EXCLUDED.atualizado_em
                """, (uid, chave, json.dumps(valor)))
        return True
    except Exception:
        return False

def metricas_personalizaveis(df, recomendadas, key, label="Personalizar métricas"):
    from utils.dados import get_mets_gps as _get_mets
    todas = _get_mets(df)
    rec   = [m for m in recomendadas if m in df.columns]

    user_id = st.session_state.get("lm_user", {}).get("id", 0)
    saved   = get_preferencia(user_id, f"mets_{key}", None)

    if saved is not None:
        default_mets = [m for m in saved if m in todas]
        if not default_mets:
            default_mets = rec
    else:
        default_mets = rec

    with st.expander(f"➕ {label}", expanded=False):
        mets = st.multiselect(
            "Métricas",
            options=todas,
            default=default_mets,
            key=f"mets_pref_{key}",
            help="Adiciona ou remove métricas. As tuas escolhas ficam guardadas e persistem entre sessões.",
        )
        if mets != saved:
            set_preferencia(user_id, f"mets_{key}", mets)

    return mets if mets else (rec or todas[:6])


def scatter_jogadores(df_plot: pd.DataFrame, x_col: str, y_col: str,
                       title: str = "", color_col: str = "Posição",
                       size_col: str = None, height: int = 500):
    if df_plot.empty or x_col not in df_plot.columns or y_col not in df_plot.columns:
        return None

    df_plot = df_plot.dropna(subset=[x_col, y_col]).copy()
    if df_plot.empty:
        return None

    CORES_POS = {
        "Guarda-Redes": "#3498db", "GR": "#3498db",
        "Defesa": "#2ecc71",       "DC": "#2ecc71", "DD": "#2ecc71", "DE": "#2ecc71",
        "Médio": "#f39c12",        "MC": "#f39c12", "MD": "#f39c12", "ME": "#f39c12",
        "Avançado": "#e63946",     "AV": "#e63946", "EX": "#e63946", "PL": "#e63946",
    }
    DEFAULT_COR = "#9b59b6"

    fig = go.Figure()

    grupos = df_plot[color_col].unique() if color_col in df_plot.columns else ["Todos"]

    for grupo in grupos:
        if color_col in df_plot.columns:
            sub = df_plot[df_plot[color_col] == grupo]
        else:
            sub = df_plot
        cor = CORES_POS.get(str(grupo), DEFAULT_COR)

        if size_col and size_col in sub.columns:
            sizes = sub[size_col].fillna(sub[size_col].mean())
            sizes_norm = ((sizes - sizes.min()) / (sizes.max() - sizes.min() + 1e-9) * 30 + 18).tolist()
        else:
            sizes_norm = [28] * len(sub)

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

    x_mean = df_plot[x_col].mean()
    y_mean = df_plot[y_col].mean()
    fig.add_vline(x=x_mean, line_dash="dot", line_color="rgba(255,255,255,0.3)",
                  annotation_text=f"Média {x_col.split('(')[0].strip()}: {x_mean:,.0f}",
                  annotation_font_color="rgba(255,255,255,0.5)", annotation_font_size=10)
    fig.add_hline(y=y_mean, line_dash="dot", line_color="rgba(255,255,255,0.3)",
                  annotation_text=f"Média {y_col.split('(')[0].strip()}: {y_mean:,.0f}",
                  annotation_font_color="rgba(255,255,255,0.5)", annotation_font_size=10)

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


def calcular_delta(df_base, col, mc_atual, mc_anterior=None):
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


def validar_dados(df_base: pd.DataFrame):
    erros, avisos, ok = [], [], []

    if "Tipo" in df_base.columns:
        tipos_validos = {"treino", "jogo"}
        tipos_encontrados = df_base["Tipo"].dropna().str.lower().str.strip().unique()
        tipos_invalidos = [t for t in tipos_encontrados if t not in tipos_validos]
        if tipos_invalidos:
            erros.append(f"❌ Coluna 'Tipo' tem valores inválidos: {tipos_invalidos} — deve ser apenas 'Treino' ou 'Jogo'")
        else:
            ok.append("✅ Coluna 'Tipo' — valores corretos (Treino / Jogo)")

    if "Dia MD" in df_base.columns:
        dias_base = {"MD-5","MD-4","MD-3","MD-2","MD-1","MD","MD+1","MD+2","MD+3"}
        sufixos_validos = {"", "R", "C", "+", "-"}
        def _eh_dia_valido(d):
            d = str(d).strip()
            for base in dias_base:
                if d == base:
                    return True
                if d.startswith(base):
                    suf = d[len(base):].upper()
                    if suf in sufixos_validos:
                        return True
            return False
        dias_encontrados = set(df_base["Dia MD"].dropna().astype(str).str.strip().unique())
        dias_invalidos = {d for d in dias_encontrados if not _eh_dia_valido(d)}
        if dias_invalidos:
            avisos.append(f"⚠️ Coluna 'Dia MD' tem valores não standard: {dias_invalidos} — esperado: MD-5 a MD+3 (com sufixo opcional R/C, ex: MD+1R)")
        else:
            ok.append("✅ Coluna 'Dia MD' — valores corretos")

    if "Data" in df_base.columns:
        n_sem_data = df_base["Data"].isna().sum()
        if n_sem_data > 0:
            erros.append(f"❌ {n_sem_data} registos sem Data — verifica as linhas em branco no Excel")
        else:
            ok.append("✅ Coluna 'Data' — sem valores em falta")

    if "PSE Sessão" in df_base.columns:
        pse = pd.to_numeric(df_base["PSE Sessão"], errors="coerce")
        fora = df_base[(pse < 0) | (pse > 10)]["PSE Sessão"].count()
        if fora > 0:
            erros.append(f"❌ {fora} valores de PSE fora do intervalo 0–10")
        else:
            ok.append("✅ PSE Sessão — todos os valores entre 0 e 10")

    if "Hooper Index" in df_base.columns:
        hi = pd.to_numeric(df_base["Hooper Index"], errors="coerce")
        fora_hi = df_base[(hi < 4) | (hi > 20)]["Hooper Index"].count()
        if fora_hi > 0:
            avisos.append(f"⚠️ {fora_hi} valores de Hooper Index fora do intervalo esperado (0–16)")
        else:
            ok.append("✅ Hooper Index — valores dentro do intervalo (4–20)")

    if "Vel. Máx (km/h)" in df_base.columns:
        vmax = pd.to_numeric(df_base["Vel. Máx (km/h)"], errors="coerce")
        suspeitos = ((vmax > 40) | (vmax < 5)) & vmax.notna()
        n_sus = suspeitos.sum()
        if n_sus > 0:
            avisos.append(f"⚠️ {n_sus} valores de Vel. Máx suspeitos (<5 ou >40 km/h) — verifica se são erros de GPS")
        else:
            ok.append("✅ Vel. Máx — sem valores suspeitos")

    if "Posição" in df_base.columns and "Jogador" in df_base.columns:
        sem_pos = df_base[df_base["Posição"].isna()]["Jogador"].dropna().unique()
        if len(sem_pos) > 0:
            avisos.append(f"⚠️ Jogadores sem posição definida: {', '.join(sem_pos)}")
        else:
            ok.append("✅ Todos os jogadores têm posição definida")

    if "Data" in df_base.columns and "Jogador" in df_base.columns and "Tipo" in df_base.columns:
        dups = df_base.groupby(["Data","Jogador","Tipo"]).size()
        n_dups = (dups > 1).sum()
        if n_dups > 0:
            avisos.append(f"⚠️ {n_dups} combinações Data+Jogador+Tipo duplicadas — possíveis registos em duplicado")
        else:
            ok.append("✅ Sem registos duplicados")

    if "Microciclo (Nr)" in df_base.columns:
        mc_counts = df_base.groupby("Microciclo (Nr)")["Jogador"].nunique()
        mc_poucos = mc_counts[mc_counts < 5].index.tolist()
        if mc_poucos:
            avisos.append(f"⚠️ Microciclos com menos de 5 jogadores registados: {[int(m) for m in mc_poucos]}")

    return erros, avisos, ok


def enviar_email_alertas(destinatario: str, smtp_user: str, smtp_pass: str,
                          alertas: list, smtp_server: str = "smtp.gmail.com", smtp_port: int = 587):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    if not alertas:
        return False, "Sem alertas para enviar."

    _clube_email = (st.session_state.get("lm_user", {}).get("clube") or "").strip()
    _titulo_clube = _clube_email if _clube_email else "LoadMonitor"

    assunto = f"🚨 Alertas de Carga — {datetime.now().strftime('%d/%m/%Y')}"
    corpo_html = f"""
    <html><body style='font-family:Arial;background:#0e1117;color:#fff;padding:20px'>
    <h2 style='color:#e63946'>🚨 Alertas de Carga — {_titulo_clube}</h2>
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
    corpo_html += "</table><br><p style='color:#555;font-size:0.8rem'>LoadMonitorSystem · Análise de Carga Desportiva</p></body></html>"

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


def renderizar_bloco(bloco_key: str, df_base: pd.DataFrame,
                     contexto: str = "dia", met_principal: str = "Carga Interna",
                     nome_extra: str = "") -> dict:
    html_out = ""
    rendered = False

    METS_GPS = get_mets_gps(df_base if "df_base" in dir() else df)
    mets_disp = [m for m in METS_GPS if m in df_base.columns and df_base[m].notna().any()]

    if df_base.empty or not mets_disp:
        return {"rendered": False, "html": "", "fig": None}

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
                # Escala 1-5 de todos os itens: 1 = mau/alto, 5 = excelente/nenhum
                # (ver LoadMonitorSystem_Template.xlsx, folha Instrucoes) — valores
                # BAIXOS são o sinal de alerta em todos os itens, não só no Sono.
                if pd.notna(hi) and hi >= 14:       alertas.append(f"Hooper {hi:.0f}🔴")
                if pd.notna(sono) and sono <= 2:    alertas.append(f"Sono {sono:.0f}🔴")
                if pd.notna(stress) and stress <= 2: alertas.append(f"Stress {stress:.0f}🔴")
                if pd.notna(dor) and dor <= 2:      alertas.append(f"Dor {dor:.0f}🔴")
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

    elif bloco_key == "tabela":
        st.markdown('<p class="section-title">📋 Tabela Completa</p>', unsafe_allow_html=True)
        COLS_TAB = ["Posição"] + mets_disp
        cols_tab_num = [c for c in mets_disp if c in df_base.columns]
        cols_tab = ["Posição"] + cols_tab_num if "Posição" in df_base.columns else cols_tab_num
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


try:
    import app_pages.dashboard as _pg_dashboard
    import app_pages.equipa as _pg_equipa
    import app_pages.jogadores as _pg_jogadores
    import app_pages.planeamento as _pg_planeamento
    import app_pages.avancado as _pg_avancado
    import app_pages.sistema as _pg_sistema
except ModuleNotFoundError as _me:
    st.error(f"❌ Erro ao carregar módulos: {_me}")
    st.stop()

st.session_state["lm_user"] = _lm_user

st.session_state["lm_filters"] = {
    "df_f":         df_f,
    "df_f_dia":     df_f_dia,
    "mc_sel":       mc_sel,
    "dia_md_sel":   dia_md_sel,
    "pos_sel":      pos_sel,
    "jogador_sel":  jogador_sel,
    "posicoes":     posicoes,
    "microciclos":  microciclos,
    "jogadores":    jogadores,
}

st.session_state["lm_helpers"] = {
    "validar_dados":               validar_dados,
    "enviar_email_alertas":        enviar_email_alertas,
    "scatter_jogadores":           scatter_jogadores,
    "calcular_delta":              calcular_delta,
    "GLOSSARIO":                   GLOSSARIO,
    "EXCEL_PATH":                  EXCEL_PATH,
    "IS_CLOUD":                    IS_CLOUD,
    "AUTH_DISPONIVEL":             AUTH_DISPONIVEL,
    "tem_acesso":                  tem_acesso if AUTH_DISPONIVEL else (lambda u, f: False),
    "metricas_personalizaveis":    metricas_personalizaveis,
    "get_preferencia":             get_preferencia,
    "set_preferencia":             set_preferencia,
}

if seccao == "dashboard":
    _pg_dashboard.render(df=df, excel_path=excel_path)
elif seccao == "equipa":
    _pg_equipa.render(df=df, excel_path=excel_path)
elif seccao == "jogadores":
    _pg_jogadores.render(df=df, excel_path=excel_path)
elif seccao == "planeamento":
    _pg_planeamento.render(df=df, excel_path=excel_path)
elif seccao == "avancado":
    _pg_avancado.render(df=df, excel_path=excel_path)
elif seccao == "sistema":
    _pg_sistema.render(df=df, excel_path=excel_path)
