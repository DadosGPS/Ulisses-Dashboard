"""
LoadMonitorSystem — Integração Stripe
Adicionar ao auth.py existente

Requer:
  pip install stripe
  Variáveis de ambiente:
    STRIPE_SECRET_KEY      = sk_live_...  (ou sk_test_... para testes)
    STRIPE_WEBHOOK_SECRET  = whsec_...
    STRIPE_PRICE_ID        = price_...    (ID do produto 29€/mês no Stripe)
"""

import stripe
import os
import sqlite3
import streamlit as st
from datetime import datetime

# ── Configuração ──────────────────────────────────────────────────────────────
STRIPE_SECRET_KEY     = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID       = os.environ.get("STRIPE_PRICE_ID", "")  # price_xxx do Stripe
APP_URL               = os.environ.get("APP_URL", "https://loadmonitorsystem.streamlit.app")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

DB_PATH = os.environ.get("LM_DB_PATH", "loadmonitor.db")


# ══════════════════════════════════════════════════════════════════════════════
# CRIAR SESSÃO DE CHECKOUT STRIPE
# Redireciona o utilizador para a página de pagamento do Stripe
# ══════════════════════════════════════════════════════════════════════════════
def criar_checkout_stripe(user_id: int, email: str, nome: str) -> dict:
    """
    Cria uma sessão de checkout Stripe para subscrição Pro (29€/mês).
    Retorna {"url": "https://checkout.stripe.com/..."} ou {"erro": "..."}
    """
    if not STRIPE_SECRET_KEY or not STRIPE_PRICE_ID:
        return {"erro": "Stripe não configurado. Contacta o suporte."}

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            customer_email=email,
            line_items=[{
                "price": STRIPE_PRICE_ID,
                "quantity": 1,
            }],
            metadata={
                "user_id": str(user_id),
                "nome": nome,
            },
            success_url=f"{APP_URL}?payment=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{APP_URL}?payment=cancelled",
            allow_promotion_codes=True,
            billing_address_collection="required",
            locale="pt",
        )
        return {"url": session.url, "session_id": session.id}

    except stripe.error.StripeError as e:
        return {"erro": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# ATIVAR PLANO PRO APÓS PAGAMENTO
# Chamado pelo webhook do Stripe quando o pagamento é confirmado
# ══════════════════════════════════════════════════════════════════════════════
def ativar_plano_pro(user_id: int, stripe_customer_id: str = None,
                      stripe_subscription_id: str = None) -> bool:
    """Ativa o plano Pro para o utilizador após pagamento confirmado."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            # Atualizar plano
            c.execute("""
                UPDATE utilizadores
                SET plano = 'pro',
                    trial_fim = NULL,
                    stripe_customer_id = ?,
                    stripe_subscription_id = ?
                WHERE id = ?
            """, (stripe_customer_id, stripe_subscription_id, user_id))

            # Garantir que as colunas Stripe existem
            try:
                c.execute("ALTER TABLE utilizadores ADD COLUMN stripe_customer_id TEXT")
            except:
                pass
            try:
                c.execute("ALTER TABLE utilizadores ADD COLUMN stripe_subscription_id TEXT")
            except:
                pass

            conn.commit()
            return True
    except Exception as e:
        print(f"Erro ao ativar Pro: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# CANCELAR SUBSCRIÇÃO
# ══════════════════════════════════════════════════════════════════════════════
def cancelar_subscricao(user_id: int) -> dict:
    """Cancela a subscrição Stripe do utilizador no fim do período atual."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT stripe_subscription_id FROM utilizadores WHERE id=?", (user_id,))
            row = c.fetchone()
            if not row or not row[0]:
                return {"erro": "Sem subscrição ativa encontrada."}

            sub_id = row[0]

        # Cancelar no fim do período (não imediatamente)
        stripe.Subscription.modify(sub_id, cancel_at_period_end=True)

        return {"sucesso": True, "msg": "Subscrição cancelada. Acesso Pro mantido até ao fim do período pago."}

    except stripe.error.StripeError as e:
        return {"erro": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# PROCESSAR WEBHOOK STRIPE
# Para usar num endpoint separado (ex: Flask, FastAPI, ou Streamlit page)
# ══════════════════════════════════════════════════════════════════════════════
def processar_webhook_stripe(payload: bytes, sig_header: str) -> dict:
    """
    Processa eventos do webhook Stripe.
    Chamar com o body raw do request e o header 'Stripe-Signature'.

    Eventos tratados:
    - checkout.session.completed → ativa plano Pro
    - customer.subscription.deleted → faz downgrade para Free
    - invoice.payment_failed → notificar utilizador (opcional)
    """
    if not STRIPE_WEBHOOK_SECRET:
        return {"erro": "Webhook secret não configurado"}

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        return {"erro": f"Webhook inválido: {e}"}

    event_type = event["type"]
    data = event["data"]["object"]

    # ── Pagamento concluído (checkout) ────────────────────────────────────────
    if event_type == "checkout.session.completed":
        user_id = int(data["metadata"].get("user_id", 0))
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        if user_id:
            ativar_plano_pro(user_id, customer_id, subscription_id)
            return {"ok": True, "acao": f"Pro ativado para user {user_id}"}

    # ── Subscrição cancelada/expirada ─────────────────────────────────────────
    elif event_type in ["customer.subscription.deleted", "customer.subscription.updated"]:
        if event_type == "customer.subscription.deleted" or data.get("status") == "canceled":
            customer_id = data.get("customer")
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    c = conn.cursor()
                    c.execute("""
                        UPDATE utilizadores SET plano='free'
                        WHERE stripe_customer_id=?
                    """, (customer_id,))
                    conn.commit()
                return {"ok": True, "acao": f"Downgrade para Free (customer {customer_id})"}
            except Exception as e:
                return {"erro": str(e)}

    # ── Pagamento falhado ─────────────────────────────────────────────────────
    elif event_type == "invoice.payment_failed":
        # Opcional: enviar email ao utilizador
        return {"ok": True, "acao": "payment_failed — notificação não implementada"}

    return {"ok": True, "acao": f"Evento ignorado: {event_type}"}


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENTE STREAMLIT — BOTÃO DE UPGRADE
# Usar na sidebar ou na página de preços
# ══════════════════════════════════════════════════════════════════════════════
def mostrar_botao_upgrade(user_id: int, email: str, nome: str,
                           plano_atual: str, dias_trial: int = None):
    """
    Mostra o botão de upgrade para Pro na app Streamlit.
    Inclui banner de trial, preço e link para checkout Stripe.
    """
    if plano_atual == "pro" and dias_trial is None:
        # Utilizador Pro pago — mostrar estado e opção de cancelar
        st.success("✅ **Plano Pro ativo**")
        if st.button("Gerir subscrição", key="btn_gerir_sub"):
            resultado = cancelar_subscricao(user_id)
            if "sucesso" in resultado:
                st.info(resultado["msg"])
            else:
                st.error(resultado.get("erro", "Erro"))
        return

    if plano_atual == "pro" and dias_trial is not None:
        # Trial ativo
        cor = "#e74c3c" if dias_trial <= 3 else "#f39c12" if dias_trial <= 7 else "#2ecc71"
        st.markdown(
            f'<div style="background:{cor}15;border:1px solid {cor}30;border-radius:8px;'
            f'padding:10px 14px;margin-bottom:8px;font-size:0.82rem">'
            f'<b>Trial Pro</b> — {dias_trial} dia(s) restante(s)</div>',
            unsafe_allow_html=True
        )

    # Botão de upgrade
    st.markdown("---")
    st.markdown("**🚀 Plano Pro — 29€/mês**")
    st.caption("Acesso completo · Cancela quando quiseres · Sem contrato")

    if st.button("⬆️ Fazer upgrade para Pro", key="btn_upgrade_pro",
                  type="primary", use_container_width=True):
        with st.spinner("A criar sessão de pagamento..."):
            resultado = criar_checkout_stripe(user_id, email, nome)

        if "url" in resultado:
            st.markdown(
                f'<meta http-equiv="refresh" content="0;url={resultado["url"]}">',
                unsafe_allow_html=True
            )
            st.markdown(
                f'**[Clica aqui se não fores redirecionado automaticamente]({resultado["url"]})**'
            )
        else:
            st.error(resultado.get("erro", "Erro ao criar sessão de pagamento."))


# ══════════════════════════════════════════════════════════════════════════════
# VERIFICAR PAGAMENTO APÓS REDIRECT DO STRIPE
# Chamar no início da app para processar o retorno do checkout
# ══════════════════════════════════════════════════════════════════════════════
def verificar_retorno_stripe():
    """
    Verifica se o utilizador voltou do Stripe após pagamento.
    Chamar no início do dashboard, antes de qualquer rendering.
    """
    params = st.query_params
    payment_status = params.get("payment", "")

    if payment_status == "success":
        session_id = params.get("session_id", "")
        user_id = st.session_state.get("lm_user", {}).get("id", 0)

        if session_id and user_id and STRIPE_SECRET_KEY:
            try:
                session = stripe.checkout.Session.retrieve(session_id)
                if session.payment_status == "paid":
                    ativar_plano_pro(
                        user_id,
                        session.customer,
                        session.subscription
                    )
                    # Atualizar session_state
                    if "lm_user" in st.session_state:
                        st.session_state["lm_user"]["plano"] = "pro"
                        st.session_state["lm_user"]["dias_trial"] = None
                    st.query_params.clear()
                    st.success("🎉 **Plano Pro ativado!** Bem-vindo ao LoadMonitorSystem Pro.")
                    st.rerun()
            except Exception as e:
                st.warning(f"Não foi possível verificar o pagamento: {e}")

    elif payment_status == "cancelled":
        st.query_params.clear()
        st.info("Pagamento cancelado. Podes fazer upgrade quando quiseres.")
