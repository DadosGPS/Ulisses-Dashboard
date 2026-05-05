"""
LoadMonitorSystem — Integração Stripe

NOTA: Durante a fase BETA/DEMO, o pagamento Pro está desactivado.
A função `mostrar_botao_upgrade` redireciona para a lista de espera
em loadmonitorsystem.com/#waitlist em vez de tentar gerar checkout.

As outras funções (criar_checkout_stripe, ativar_plano_pro,
cancelar_subscricao, processar_webhook_stripe, verificar_retorno_stripe)
estão preservadas e ligadas ao Postgres. Quando o Pro abrir oficialmente,
basta voltar a chamar `mostrar_botao_upgrade` em modo "vendas".

CORREÇÃO IMPORTANTE (vs versão anterior):
  Toda a persistência foi migrada de SQLite para Postgres via auth.get_conn().
  A versão anterior escrevia em loadmonitor.db (SQLite) — isto perdia-se a
  cada restart do Streamlit Cloud e era inconsistente com o resto da app.
"""

import os
import streamlit as st

import stripe

# Ligação à BD partilhada com o auth.py
from auth import get_conn

# ── Configuração de chaves ────────────────────────────────────────────────────
# Suporta tanto STRIPE_SECRET_KEY direto como o esquema antigo P1+P2
# (caso a chave tenha sido partida em duas variáveis de ambiente).
def _get_secret(key: str, default: str = "") -> str:
    """Lê primeiro de st.secrets, depois de env var."""
    try:
        v = st.secrets.get(key, None)
        if v:
            return str(v).strip()
    except Exception:
        pass
    return os.environ.get(key, default).strip()

_sk_p1 = _get_secret("STRIPE_KEY_P1", "")
_sk_p2 = _get_secret("STRIPE_KEY_P2", "")
STRIPE_SECRET_KEY     = _get_secret("STRIPE_SECRET_KEY", _sk_p1 + _sk_p2)
STRIPE_WEBHOOK_SECRET = _get_secret("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID       = _get_secret("STRIPE_PRICE_ID", "")
APP_URL               = _get_secret("APP_URL", "https://loadmonitorsystem.streamlit.app")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


def criar_checkout_stripe(user_id: int, email: str, nome: str) -> dict:
    """Cria sessão de checkout Stripe. Devolve {"url": ..., "session_id": ...} ou {"erro": ...}."""
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


def ativar_plano_pro(user_id: int,
                     stripe_customer_id: str = None,
                     stripe_subscription_id: str = None) -> bool:
    """
    Ativa o plano Pro para um utilizador.
    Persiste em Postgres (não SQLite). As colunas stripe_customer_id e
    stripe_subscription_id já estão no schema (auth.init_db).
    """
    try:
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute("""
                    UPDATE utilizadores
                    SET plano = 'pro',
                        trial_fim = NULL,
                        stripe_customer_id = %s,
                        stripe_subscription_id = %s
                    WHERE id = %s
                """, (stripe_customer_id, stripe_subscription_id, user_id))
        return True
    except Exception as e:
        print(f"[auth_stripe.ativar_plano_pro] Erro: {e}")
        return False


def cancelar_subscricao(user_id: int) -> dict:
    """Cancela a subscrição Stripe no fim do período pago."""
    try:
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute("""
                    SELECT stripe_subscription_id FROM utilizadores WHERE id=%s
                """, (user_id,))
                row = c.fetchone()
                if not row or not row[0]:
                    return {"erro": "Sem subscrição ativa encontrada."}
                sub_id = row[0]

        stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
        return {
            "sucesso": True,
            "msg": "Subscrição cancelada. Acesso Pro mantido até ao fim do período pago."
        }
    except Exception as e:
        return {"erro": str(e)}


def processar_webhook_stripe(payload: bytes, sig_header: str) -> dict:
    """Processa eventos Stripe (checkout completo, cancelamentos, etc)."""
    if not STRIPE_WEBHOOK_SECRET:
        return {"erro": "Webhook secret não configurado"}
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        return {"erro": str(e)}

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        try:
            user_id = int(data["metadata"].get("user_id", 0))
        except (ValueError, TypeError, KeyError):
            user_id = 0
        if user_id:
            ok = ativar_plano_pro(user_id, data.get("customer"), data.get("subscription"))
            if ok:
                return {"ok": True, "acao": f"Pro ativado para user {user_id}"}
            return {"erro": f"Falhou ativar Pro para user {user_id}"}

    elif event_type in ["customer.subscription.deleted"]:
        customer_id = data.get("customer")
        if not customer_id:
            return {"erro": "Sem customer_id no evento"}
        try:
            with get_conn() as conn:
                with conn.cursor() as c:
                    c.execute("""
                        UPDATE utilizadores
                        SET plano = 'free'
                        WHERE stripe_customer_id = %s
                    """, (customer_id,))
        except Exception as e:
            return {"erro": str(e)}
        return {"ok": True, "acao": f"Plano free atribuído (customer {customer_id})"}

    return {"ok": True, "acao": f"Evento ignorado: {event_type}"}


def mostrar_botao_upgrade(user_id: int, email: str, nome: str,
                          plano_atual: str, dias_trial: int = None):
    """
    Banner de upgrade.

    DURANTE A FASE BETA/DEMO: redireciona para waitlist (não cobra ninguém).
    Quando o Pro pago abrir, comentar este modo e descomentar o bloco
    de checkout abaixo.
    """

    # Plano Pro pago real (futuro — não acontece durante a beta)
    if plano_atual == "pro" and dias_trial is None:
        st.markdown("""
<div style="background:linear-gradient(135deg,#0d2a0d,#1a3a1a);
border:1px solid #2ecc71;border-radius:10px;padding:12px 14px;
text-align:center;margin:4px 0">
<div style="font-size:0.72rem;font-weight:700;color:#2ecc71;
letter-spacing:2px">✅ ACESSO COMPLETO</div>
<div style="font-size:0.68rem;color:rgba(255,255,255,0.4);margin-top:2px">
Versão demo gratuita</div></div>""", unsafe_allow_html=True)
        return

    # Banner principal — Plano Pro em desenvolvimento
    st.markdown("""
<div style="background:linear-gradient(160deg,#1c0608,#2d0d10);
border:2px solid #e63946;border-radius:12px;padding:18px 14px;
text-align:center;margin:10px 0 6px">
<div style="font-size:0.62rem;font-weight:700;color:#e63946;
letter-spacing:3px;margin-bottom:8px">🚀 PLANO PRO</div>
<div style="font-size:1rem;font-weight:700;color:white;line-height:1.3;margin-bottom:6px">
Em desenvolvimento</div>
<div style="font-size:0.72rem;color:rgba(255,255,255,0.65);margin-bottom:14px;line-height:1.5">
O Plano Pro entra em beta privada brevemente.<br>
Junta-te à lista de espera para seres avisado<br>
quando estiver disponível.</div>
<div style="font-size:0.7rem;color:rgba(255,255,255,0.55);
text-align:left;line-height:1.8;margin-bottom:8px;padding:0 4px">
✓ Atletas e equipas ilimitados<br>
✓ Todos os alertas automáticos<br>
✓ Análise GPS avançada (Vmáx)<br>
✓ Relatórios PDF personalizáveis<br>
✓ Notificações email
</div></div>""", unsafe_allow_html=True)

    # Botão para a lista de espera
    st.link_button(
        "📋 Entrar na lista de espera",
        "https://loadmonitorsystem.com/#waitlist",
        type="primary",
        use_container_width=True
    )


def verificar_retorno_stripe():
    """Processa o retorno do Stripe após pagamento (callback do success_url)."""
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
