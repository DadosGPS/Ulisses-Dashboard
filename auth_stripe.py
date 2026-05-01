"""
LoadMonitorSystem — Integração Stripe
"""

import stripe
import os
import sqlite3
import streamlit as st
from datetime import datetime

# Chave Stripe dividida em duas partes para compatibilidade com Streamlit Secrets
_sk_p1 = os.environ.get("STRIPE_KEY_P1", "")
_sk_p2 = os.environ.get("STRIPE_KEY_P2", "")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", _sk_p1 + _sk_p2)
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID       = os.environ.get("STRIPE_PRICE_ID", "")
APP_URL               = os.environ.get("APP_URL", "https://loadmonitorsystem.streamlit.app")
DB_PATH               = os.environ.get("LM_DB_PATH", "loadmonitor.db")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


def criar_checkout_stripe(user_id: int, email: str, nome: str) -> dict:
    if not STRIPE_SECRET_KEY or not STRIPE_PRICE_ID:
        return {"erro": "Stripe não configurado. Contacta o suporte."}
    try:
        # Validar email antes de enviar ao Stripe
        import re
        email_valido = email and re.match(r"[^@]+@[^@]+\.[^@]+", email.strip())
        
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            customer_email=email.strip() if email_valido else None,
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            metadata={"user_id": str(user_id), "nome": nome},
            success_url=f"{APP_URL}?payment=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{APP_URL}?payment=cancelled",
            allow_promotion_codes=True,
            billing_address_collection="required",
            locale="pt",
        )
        return {"url": session.url, "session_id": session.id}
    except Exception as e:
        return {"erro": str(e)}


def ativar_plano_pro(user_id: int, stripe_customer_id: str = None,
                      stripe_subscription_id: str = None) -> bool:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            try: c.execute("ALTER TABLE utilizadores ADD COLUMN stripe_customer_id TEXT")
            except: pass
            try: c.execute("ALTER TABLE utilizadores ADD COLUMN stripe_subscription_id TEXT")
            except: pass
            c.execute("""UPDATE utilizadores SET plano='pro', trial_fim=NULL,
                stripe_customer_id=?, stripe_subscription_id=? WHERE id=?""",
                (stripe_customer_id, stripe_subscription_id, user_id))
            conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao ativar Pro: {e}")
        return False


def cancelar_subscricao(user_id: int) -> dict:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT stripe_subscription_id FROM utilizadores WHERE id=?", (user_id,))
            row = c.fetchone()
            if not row or not row[0]:
                return {"erro": "Sem subscrição ativa encontrada."}
            sub_id = row[0]
        stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
        return {"sucesso": True, "msg": "Subscrição cancelada. Acesso Pro mantido até ao fim do período pago."}
    except Exception as e:
        return {"erro": str(e)}


def processar_webhook_stripe(payload: bytes, sig_header: str) -> dict:
    if not STRIPE_WEBHOOK_SECRET:
        return {"erro": "Webhook secret não configurado"}
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        return {"erro": str(e)}

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        user_id = int(data["metadata"].get("user_id", 0))
        if user_id:
            ativar_plano_pro(user_id, data.get("customer"), data.get("subscription"))
            return {"ok": True, "acao": f"Pro ativado para user {user_id}"}

    elif event_type in ["customer.subscription.deleted"]:
        customer_id = data.get("customer")
        try:
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute("UPDATE utilizadores SET plano='free' WHERE stripe_customer_id=?", (customer_id,))
                conn.commit()
        except Exception as e:
            return {"erro": str(e)}

    return {"ok": True, "acao": f"Evento: {event_type}"}


def mostrar_botao_upgrade(user_id: int, email: str, nome: str,
                           plano_atual: str, dias_trial: int = None):
    """Banner de upgrade premium com destaque visual máximo na sidebar."""

    # Plano Pro pago — mostrar badge verde
    if plano_atual == "pro" and dias_trial is None:
        st.markdown("""
<div style="background:linear-gradient(135deg,#0d2a0d,#1a3a1a);
border:1px solid #2ecc71;border-radius:10px;padding:12px 14px;
text-align:center;margin:4px 0">
<div style="font-size:0.72rem;font-weight:700;color:#2ecc71;
letter-spacing:2px">✅ PLANO PRO ATIVO</div>
<div style="font-size:0.68rem;color:rgba(255,255,255,0.4);margin-top:2px">
Acesso completo desbloqueado</div></div>""", unsafe_allow_html=True)
        return

    # Trial ativo — mostrar countdown
    if plano_atual == "pro" and dias_trial is not None:
        cor = "#e74c3c" if dias_trial <= 3 else "#f39c12" if dias_trial <= 7 else "#3498db"
        urgencia = "⚠️ A expirar em breve!" if dias_trial <= 3 else f"⏳ {dias_trial} dias de trial"
        st.markdown(f"""
<div style="background:{cor}18;border:1px solid {cor}60;
border-radius:10px;padding:10px 14px;text-align:center;margin:4px 0">
<div style="font-size:0.7rem;font-weight:700;color:{cor}">{urgencia}</div>
<div style="font-size:0.65rem;color:rgba(255,255,255,0.4);margin-top:2px">
Faz upgrade para manter o acesso Pro</div></div>""", unsafe_allow_html=True)

    # Banner principal de upgrade
    st.markdown("""
<div style="background:linear-gradient(160deg,#1c0608,#2d0d10);
border:2px solid #e63946;border-radius:12px;padding:18px 14px;
text-align:center;margin:10px 0 6px">
<div style="font-size:0.62rem;font-weight:700;color:#e63946;
letter-spacing:3px;margin-bottom:8px">🚀 PLANO PRO</div>
<div style="font-size:1.8rem;font-weight:700;color:white;line-height:1">
29€<span style="font-size:0.85rem;color:rgba(255,255,255,0.45);
font-weight:400">/mês</span></div>
<div style="font-size:0.65rem;color:rgba(255,255,255,0.35);margin:4px 0 12px">
Sem contrato · Cancela quando quiseres</div>
<div style="font-size:0.72rem;color:rgba(255,255,255,0.65);
text-align:left;line-height:1.8">
✓ Atletas e equipas ilimitados<br>
✓ Todos os alertas automáticos<br>
✓ Análise GPS avançada (Vmáx)<br>
✓ Relatórios PDF personalizáveis<br>
✓ Notificações email e WhatsApp
</div></div>""", unsafe_allow_html=True)

    # Mostrar URL do Stripe se já foi gerado anteriormente
    stripe_url_key = f"stripe_url_{user_id}"
    if stripe_url_key in st.session_state:
        url = st.session_state[stripe_url_key]
        st.markdown(f"""
<div style="background:#1a0608;border:1px solid #e63946;border-radius:10px;
padding:16px;text-align:center;margin:8px 0">
<div style="font-size:0.8rem;color:rgba(255,255,255,0.7);margin-bottom:10px">
✅ Página de pagamento pronta</div>
<a href="{url}" target="_blank"
style="display:block;background:#e63946;color:white;
padding:12px;border-radius:6px;font-weight:700;font-size:0.9rem;
text-decoration:none;margin-bottom:8px">
💳 Abrir página de pagamento →</a>
<div style="font-size:0.65rem;color:rgba(255,255,255,0.35)">
Abre numa nova aba · Seguro · Processado pelo Stripe</div>
</div>""", unsafe_allow_html=True)
        if st.button("🔄 Gerar novo link", key="btn_novo_link", use_container_width=True):
            del st.session_state[stripe_url_key]
            st.rerun()
        return

    if st.button("⬆️ Activar Plano Pro — 29€/mês",
                  key="btn_upgrade_pro",
                  type="primary",
                  use_container_width=True):
        with st.spinner("A preparar pagamento seguro..."):
            resultado = criar_checkout_stripe(user_id, email, nome)
        if "url" in resultado:
            st.session_state[stripe_url_key] = resultado["url"]
            st.rerun()
        else:
            st.error(resultado.get("erro", "Erro ao criar sessão. Tenta novamente."))


def verificar_retorno_stripe():
    """Processa o retorno do Stripe após pagamento."""
    params = st.query_params
    payment_status = params.get("payment", "")

    if payment_status == "success":
        session_id = params.get("session_id", "")
        user_id = st.session_state.get("lm_user", {}).get("id", 0)
        if session_id and user_id and STRIPE_SECRET_KEY:
            try:
                session = stripe.checkout.Session.retrieve(session_id)
                if session.payment_status == "paid":
                    ativar_plano_pro(user_id, session.customer, session.subscription)
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
