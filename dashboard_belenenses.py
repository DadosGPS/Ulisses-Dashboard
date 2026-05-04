"""
LoadMonitorSystem — Ficheiro Principal
Arquitectura modular: utils/ + pages/
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os, io, base64, json
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


# ── Módulos da app ───────────────────────────────────────────────────────────
from utils.dados import carregar_dados, carregar_dados_safe, carregar_exercicios, get_mets_gps, normalizar_coluna, COL_ALIASES
from utils.calculos import calcular_acwr, calcular_acwr_global, zscore_serie, cor_acwr, calcular_monotonia_strain
from utils.ui import lm_header, premium_layout, botao_download_html, gerar_pdf_html, metric_card, sem_dados_suficientes

st.set_page_config(
    page_title="Carga de Treino | Belenenses",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sentry — observabilidade de erros em produção ────────────────────────────
# Inicializa apenas se SENTRY_DSN estiver configurado em Secrets/env.
# Não rebenta se Sentry não estiver disponível.
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
            # Não enviar erros relacionados com auth — são esperados
            exc_info = hint.get("exc_info") if hint else None
            if exc_info:
                exc_type, exc_value, _ = exc_info
                if exc_type:
                    msg = str(exc_value).lower()
                    # Ignorar: passwords erradas, sessões expiradas, rate limits
                    if any(t in msg for t in ["password incorret", "sessão expir",
                                               "tentativas falhadas", "bloqueada"]):
                        return None
            # Remover query string (pode conter reset_token)
            if event.get("request") and event["request"].get("query_string"):
                event["request"]["query_string"] = "[Filtered]"
            return event

        sentry_sdk.init(
            dsn=_sentry_dsn,
            traces_sample_rate=0.1,         # 10% das transações
            profiles_sample_rate=0.0,       # Sem profiling (poupa quota)
            send_default_pii=False,         # NÃO recolher IP/headers — RGPD
            environment=os.environ.get("ENVIRONMENT", "production"),
            release="loadmonitor@1.0.0",
            before_send=_sentry_filtro,
        )
except ImportError:
    pass  # sentry_sdk não instalado — segue sem


# ── CSS personalizado ─────────────────────────────────────────────────────────
# Tipografia Inter + variáveis de marca alinhadas com loadmonitorsystem.com
st.markdown(
    "<style>"
    "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');"
    ":root{"
    "--lm-accent:#e63946;"
    "--lm-accent-2:#ff6b75;"
    "--lm-ink:#0a0a0a;"
    "--lm-mono:'JetBrains Mono',ui-monospace,monospace;"
    "--lm-sans:'Inter',-apple-system,BlinkMacSystemFont,system-ui,sans-serif;"
    "}"
    "html,body,[class*=\"css\"],.stMarkdown,.stApp,"
    ".stButton button,.stTextInput input,.stNumberInput input,"
    ".stSelectbox div,.stMultiSelect div,.stRadio label,"
    ".stCheckbox label,.stMetric,.stDataFrame{"
    "font-family:var(--lm-sans) !important;"
    "font-feature-settings:'cv02','cv03','cv04','cv11';"
    "-webkit-font-smoothing:antialiased;"
    "-moz-osx-font-smoothing:grayscale;"
    "}"
    "h1,h2,h3,h4,h5,h6{"
    "font-family:var(--lm-sans) !important;"
    "letter-spacing:-0.02em;"
    "}"
    "code,pre,kbd,samp,.stCodeBlock{"
    "font-family:var(--lm-mono) !important;"
    "}"
    "</style>",
    unsafe_allow_html=True
)

# ── Caminho do ficheiro Excel ─────────────────────────────────────────────────
EXCEL_PATH = "Excel_carga_de_treino_profissional_final_2.xlsx"

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
    .login-logo-wrap {
        display: flex; align-items: center; justify-content: center;
        gap: 12px; margin-bottom: 4px;
    }
    .login-mark {
        width: 32px; height: 32px;
        background: #ffffff;
        border-radius: 7px;
        position: relative;
    }
    .login-mark::before {
        content: ''; position: absolute; inset: 7px;
        background: #e63946; border-radius: 3px;
    }
    .login-logo {
        font-family: 'Inter', -apple-system, sans-serif;
        font-size: 1.9rem; font-weight: 600;
        letter-spacing: -0.025em; text-align: center;
    }
    .login-logo span { color: #e63946; }
    .login-tagline {
        text-align: center; color: #888; font-size: 0.78rem;
        letter-spacing: 2px; text-transform: uppercase;
        margin-bottom: 32px; font-weight: 500;
    }
    .trial-badge {
        background: linear-gradient(135deg, #e63946, #c0392b);
        color: white; text-align: center; padding: 10px;
        border-radius: 8px; font-size: 0.8rem; font-weight: 600;
        margin-bottom: 20px; letter-spacing: 0.5px;
    }
    </style>
    <div class="login-container">
        <div class="login-logo-wrap">
            <div class="login-mark"></div>
            <div class="login-logo">Load<span>Monitor</span></div>
        </div>
        <div class="login-tagline">Monitorização de Carga Desportiva</div>
        <div class="trial-badge">🎉 14 dias grátis no plano Pro — sem cartão de crédito</div>
    </div>
    """, unsafe_allow_html=True)

    col_center = st.columns([1, 2, 1])[1]
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

            # Consentimento RGPD — obrigatório para criar conta
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
                    # Mensagem genérica (não revela se email existe ou não)
                    st.success("Se o email estiver registado, vais receber um link em alguns segundos. Verifica a tua caixa de entrada (e spam).")
    st.stop()

# ── Verificar autenticação ────────────────────────────────────────────────────
# Modo de desenvolvimento — bypass do login para testes
_DEV_MODE = False
try:
    _DEV_MODE = str(st.secrets.get("DEV_MODE", "")).lower() in ["true", "1", "yes"]
except:
    _DEV_MODE = False

# ── Página de reset password (acionada por ?reset_token=XXX no URL) ──────────
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
    # Bypass total — entra automaticamente como Pro
    st.session_state["lm_user"] = {
        "id": 1, "nome": "Dev User", "email": "dev@loadmonitor.io",
        "clube": "Dev Mode", "plano": "pro",
        "trial_fim": None, "dias_trial": None,
    }
    st.session_state["lm_token"] = "dev_token_bypass"

elif not AUTH_DISPONIVEL:
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

# ── DEBUG: botão para testar Sentry (só aparece se SENTRY_TEST=true em Secrets) ──
try:
    if str(st.secrets.get("SENTRY_TEST", "")).lower() in ["true", "1"]:
        if st.button("🐛 Disparar erro de teste para Sentry"):
            try:
                # Erro propositado e identificável
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
    # ── Sidebar — design refinado e largura fixa ─────────────────────────
    st.markdown("""
    <style>
    /* ─── Sidebar: largura fixa estreita + fundo gradiente ─────────────── */
    section[data-testid="stSidebar"] {
        width: 260px !important;
        min-width: 260px !important;
        max-width: 260px !important;
        background: linear-gradient(180deg, #0a0e14 0%, #0d1421 50%, #0b1018 100%) !important;
        border-right: 1px solid rgba(255,255,255,0.04) !important;
    }
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 0 !important;
        width: 260px !important;
    }
    /* Esconder o handle de redimensionar */
    section[data-testid="stSidebar"] [data-testid="stSidebarResizeHandle"] { display: none !important; }

    /* Compactar conteúdo do main area */
    .main .block-container {
        padding-left: 2.6rem !important;
        padding-right: 2.6rem !important;
        padding-top: 1.6rem !important;
        max-width: 1400px;
    }

    /* ─── Logo / cabeçalho da sidebar ────────────────────────────────── */
    .lm-side-head {
        padding: 22px 18px 16px;
        border-bottom: 1px solid rgba(255,255,255,0.04);
        margin-bottom: 4px;
        position: relative;
    }
    .lm-side-head::before {
        content: ""; position: absolute; left: 18px; bottom: 0; width: 32px; height: 2px;
        background: linear-gradient(90deg, #e63946, transparent);
    }
    .lm-side-logo-wrap {
        display: flex; align-items: center; gap: 9px;
    }
    .lm-side-mark {
        width: 22px; height: 22px;
        background: white;
        border-radius: 5px;
        position: relative;
        flex-shrink: 0;
    }
    .lm-side-mark::before {
        content: ''; position: absolute; inset: 5px;
        background: #e63946; border-radius: 2px;
    }
    .lm-side-logo {
        font-family: 'Inter', system-ui, sans-serif;
        font-size: 1.18rem; font-weight: 600;
        letter-spacing: -0.02em; color: white;
        line-height: 1;
    }
    .lm-side-logo span { color: #e63946; }
    .lm-side-tag {
        font-size: 0.55rem; color: rgba(255,255,255,0.3);
        letter-spacing: 2.5px; text-transform: uppercase;
        margin-top: 6px; font-weight: 600;
    }

    /* ─── Cartão do utilizador ──────────────────────────────────────── */
    .lm-side-user {
        background: linear-gradient(135deg, rgba(255,255,255,0.045), rgba(255,255,255,0.015));
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 10px;
        padding: 11px 13px;
        margin: 12px 12px 8px;
        transition: all 0.2s ease;
    }
    .lm-side-user:hover {
        border-color: rgba(230,57,70,0.18);
        background: linear-gradient(135deg, rgba(230,57,70,0.05), rgba(255,255,255,0.02));
    }
    .lm-side-user-name {
        font-weight: 700; font-size: 0.83rem;
        color: rgba(255,255,255,0.92);
        letter-spacing: 0.1px;
    }
    .lm-side-user-clube {
        font-size: 0.68rem; color: rgba(255,255,255,0.4);
        margin-top: 2px;
    }
    .lm-side-badge {
        display: inline-block; margin-top: 8px;
        padding: 2px 9px; border-radius: 4px;
        font-size: 0.58rem; font-weight: 700;
        letter-spacing: 1.5px;
    }

    /* ─── Botões de navegação refinados ─────────────────────────────── */
    section[data-testid="stSidebar"] .stButton > button {
        border-radius: 8px !important;
        font-size: 0.83rem !important;
        font-weight: 500 !important;
        padding: 8px 12px !important;
        text-align: left !important;
        justify-content: flex-start !important;
        transition: all 0.15s ease !important;
        height: auto !important;
        min-height: unset !important;
    }
    section[data-testid="stSidebar"] .stButton > button[kind="secondary"] {
        background: transparent !important;
        color: rgba(255,255,255,0.7) !important;
        border: 1px solid transparent !important;
    }
    section[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
        background: rgba(255,255,255,0.04) !important;
        color: white !important;
        border-color: rgba(255,255,255,0.06) !important;
        transform: translateX(2px);
    }
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, rgba(230,57,70,0.14), rgba(230,57,70,0.06)) !important;
        color: #ff6b75 !important;
        border: 1px solid rgba(230,57,70,0.28) !important;
        font-weight: 600 !important;
        box-shadow: 0 0 0 1px rgba(230,57,70,0.05) inset !important;
    }
    section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, rgba(230,57,70,0.22), rgba(230,57,70,0.1)) !important;
        color: #ffffff !important;
    }

    /* ─── Divisores subtis ──────────────────────────────────────────── */
    section[data-testid="stSidebar"] hr {
        margin: 14px 14px !important;
        border: none !important;
        border-top: 1px solid rgba(255,255,255,0.04) !important;
    }

    /* ─── Cabeçalhos de secção ──────────────────────────────────────── */
    section[data-testid="stSidebar"] h3 {
        font-size: 0.7rem !important;
        font-weight: 700 !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
        color: rgba(255,255,255,0.38) !important;
        margin: 14px 16px 8px !important;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        font-size: 0.78rem !important;
        color: rgba(255,255,255,0.7) !important;
    }

    /* ─── File uploader compacto ────────────────────────────────────── */
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] {
        padding: 0 12px;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
        border: 1px dashed rgba(255,255,255,0.1) !important;
        background: rgba(255,255,255,0.018) !important;
        border-radius: 8px !important;
        padding: 10px !important;
        min-height: unset !important;
        transition: all 0.15s ease;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]:hover {
        border-color: rgba(230,57,70,0.3) !important;
        background: rgba(230,57,70,0.025) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] small,
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] span {
        font-size: 0.72rem !important;
    }

    /* ─── Inputs (selectbox, multiselect, text) refinados ──────────── */
    section[data-testid="stSidebar"] [data-testid="stMultiSelect"] label,
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] label,
    section[data-testid="stSidebar"] [data-testid="stTextInput"] label {
        font-size: 0.7rem !important;
        color: rgba(255,255,255,0.55) !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px !important;
        text-transform: uppercase !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="select"] > div,
    section[data-testid="stSidebar"] [data-baseweb="input"] > div {
        background: rgba(255,255,255,0.025) !important;
        border-color: rgba(255,255,255,0.06) !important;
        font-size: 0.8rem !important;
    }

    /* ─── Caption mais subtil ──────────────────────────────────────── */
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        font-size: 0.68rem !important;
        color: rgba(255,255,255,0.35) !important;
        padding: 0 12px;
    }

    /* ─── Scrollbar fininha ────────────────────────────────────────── */
    section[data-testid="stSidebar"] ::-webkit-scrollbar { width: 4px; }
    section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb {
        background: rgba(255,255,255,0.06); border-radius: 2px;
    }
    section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb:hover {
        background: rgba(230,57,70,0.4);
    }
    </style>
    """, unsafe_allow_html=True)

    # ── LoadMonitor Logo ─────────────────────────────────────────────────
    st.markdown("""
    <div class="lm-side-head">
        <div class="lm-side-logo-wrap">
            <div class="lm-side-mark"></div>
            <div class="lm-side-logo">Load<span>Monitor</span></div>
        </div>
        <div class="lm-side-tag">Sports Performance</div>
    </div>
    """, unsafe_allow_html=True)

    # Info do utilizador
    plano_cor = "#e63946" if _lm_plano == "pro" else "#888"
    plano_label = f"PRO{'  ⏳ ' + str(_lm_trial) + 'd trial' if _lm_trial else ''}" if _lm_plano == "pro" else "FREE"
    st.markdown(f"""
    <div class="lm-side-user">
        <div class="lm-side-user-name">{_lm_nome}</div>
        <div class="lm-side-user-clube">{_lm_clube}</div>
        <span class="lm-side-badge" style="background:{plano_cor};color:white">
        {plano_label}</span>
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
            # ═══ ECRÃ DE BOAS-VINDAS PREMIUM ═══════════════════════════════════════════
            
            # ── HERO ───────────────────────────────────────────────────────────────
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
para preparadores físicos de futebol profissional.
</div></div></div>""", unsafe_allow_html=True)

            # ── 3 PASSOS ───────────────────────────────────────────────────────────
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

            # ── DOWNLOAD TEMPLATE (alternativa para quem não tem Excel ainda) ──────
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

            # ── COMPATIBILIDADE ─────────────────────────────────────────────────────
            st.markdown("""
<div style="
    background:rgba(230,57,70,0.05);
    border:1px solid rgba(230,57,70,0.15);
    border-radius:12px;padding:18px 22px;margin:24px 0 8px;
    display:flex;align-items:center;gap:16px;flex-wrap:wrap">
<div style="
    background:rgba(230,57,70,0.18);
    border-radius:8px;padding:8px 12px;
    font-size:1.1rem">⚡</div>
<div style="flex:1;min-width:200px">
<div style="font-size:0.92rem;font-weight:600;color:white;margin-bottom:2px">
Já tens Excel próprio? Funciona logo.</div>
<div style="font-size:0.78rem;color:rgba(255,255,255,0.5);line-height:1.5">
Catapult · STATSports · Polar · FieldWiz · WIMU · Excel manual — a app deteta automaticamente as colunas do teu ficheiro.
</div></div></div>""", unsafe_allow_html=True)

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


# ── Log de alertas (ficheiro JSON local) ─────────────────────────────────────
LOG_PATH = Path("alertas_log.json")

# ── Persistência de preferências do utilizador (Postgres via auth.py) ────────
def _init_prefs_table():
    """Tabela já é criada pelo schema SQL do Supabase. Mantemos no-op para compat."""
    pass

_init_prefs_table()

def get_preferencia(user_id, chave, default=None):
    """Lê preferência guardada para o utilizador. Devolve default se não existir."""
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
    """Guarda preferência (serializa em JSON). Retorna True em sucesso."""
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
    """
    Multiselect persistente de métricas, com expander.
    - recomendadas: lista default (intersecção com df.columns)
    - key: chave única para guardar a preferência (ex: 'mets_jogo')
    - label: texto do expander
    Persiste entre sessões via tabela `preferencias` em Postgres (Supabase).
    """
    from utils.dados import get_mets_gps as _get_mets
    todas = _get_mets(df)
    rec   = [m for m in recomendadas if m in df.columns]

    user_id = st.session_state.get("lm_user", {}).get("id", 0)
    saved   = get_preferencia(user_id, f"mets_{key}", None)

    if saved is not None:
        # Filtra entradas que já não existem no df atual (ex.: mudou de Excel)
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

    # Dia MD — aceita base (MD-5..MD+2) e sufixos R/C/etc (MD+1R, MD+1C, MD-1R...)
    if "Dia MD" in df_base.columns:
        dias_base = {"MD-5","MD-4","MD-3","MD-2","MD-1","MD","MD+1","MD+2","MD+3"}
        # Sufixos opcionais para variantes (R = Recuperação, C = Compensatório, etc.)
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
            avisos.append(f"⚠️ {fora_hi} valores de Hooper Index fora do intervalo esperado (0–16)")
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

# ═══════════════════════════════════════════════════════════════════════════════
# ROUTING
# ═══════════════════════════════════════════════════════════════════════════════
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

# ─── Expor estado partilhado a todas as páginas via session_state ────────────
# As páginas em app_pages/ leem daqui em vez de receberem dezenas de kwargs.
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

# Helpers e constantes globais — pages acedem como st.session_state["lm_helpers"]["X"]
st.session_state["lm_helpers"] = {
    "carregar_log":                carregar_log,
    "guardar_alerta":              guardar_alerta,
    "registar_alertas_automaticos": registar_alertas_automaticos,
    "validar_dados":               validar_dados,
    "enviar_email_alertas":        enviar_email_alertas,
    "scatter_jogadores":           scatter_jogadores,
    "calcular_delta":              calcular_delta,
    "GLOSSARIO":                   GLOSSARIO,
    "EXCEL_PATH":                  EXCEL_PATH,
    "LOG_PATH":                    LOG_PATH,
    "IS_CLOUD":                    IS_CLOUD,
    "AUTH_DISPONIVEL":             AUTH_DISPONIVEL,
    "tem_acesso":                  tem_acesso if AUTH_DISPONIVEL else (lambda u, f: True),
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
