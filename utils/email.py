"""
LoadMonitor — Wrapper para envio de email transacional via Resend.

Templates incluídos:
- enviar_email_boas_vindas
- enviar_email_reset_password
- enviar_email_trial_expira
- enviar_email_subscricao_confirmada

Configuração: precisa de RESEND_API_KEY, FROM_EMAIL e APP_BASE_URL em
              Streamlit Secrets ou variáveis de ambiente.
"""

import os
from datetime import datetime

# Resend (importação tolerante para não rebentar a app se ainda não estiver instalado)
try:
    import resend
    RESEND_DISPONIVEL = True
except ImportError:
    RESEND_DISPONIVEL = False


# ── Configuração ──────────────────────────────────────────────────────────────
def _get_secret(key: str, default: str = "") -> str:
    """Lê secret/env var. Streamlit Secrets primeiro, depois env."""
    try:
        import streamlit as st
        val = st.secrets.get(key, None)
        if val:
            return str(val)
    except Exception:
        pass
    return os.environ.get(key, default)


def _config():
    """Carrega configuração de envio. Retorna dict ou None se não configurada."""
    api_key = _get_secret("RESEND_API_KEY")
    if not api_key or not RESEND_DISPONIVEL:
        return None
    return {
        "api_key":  api_key,
        "from":     _get_secret("FROM_EMAIL", "noreply@loadmonitorsystem.com"),
        "base_url": _get_secret("APP_BASE_URL", "https://loadmonitorsystem.com"),
    }


def _enviar(to: str, subject: str, html: str) -> dict:
    """
    Envia email via Resend. Retorna {"sucesso": bool, "id": str|None, "erro": str|None}.
    Se Resend não estiver configurado, retorna sucesso=False mas não rebenta.
    """
    cfg = _config()
    if not cfg:
        return {"sucesso": False, "id": None, "erro": "Resend não configurado (RESEND_API_KEY ausente)."}
    try:
        resend.api_key = cfg["api_key"]
        params = {
            "from":    f"LoadMonitor <{cfg['from']}>",
            "to":      [to],
            "subject": subject,
            "html":    html,
        }
        result = resend.Emails.send(params)
        return {"sucesso": True, "id": result.get("id"), "erro": None}
    except Exception as e:
        return {"sucesso": False, "id": None, "erro": str(e)}


# ── Estilos partilhados (inline para compatibilidade com clientes de email) ──
def _wrap_html(content: str, preview: str = "") -> str:
    """Encapsula conteúdo num template base com header/footer consistentes."""
    return f"""<!DOCTYPE html>
<html lang="pt"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#f5f5f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;color:#1a1a2e;line-height:1.55">
<span style="display:none;color:transparent;height:0;width:0;overflow:hidden">{preview}</span>
<div style="max-width:560px;margin:0 auto;padding:32px 16px">

  <!-- Header -->
  <div style="text-align:center;padding:8px 0 24px">
    <div style="font-family:'Arial Black',Helvetica,sans-serif;font-size:1.6rem;font-weight:900;letter-spacing:1px;color:#1a1a2e">
      Load<span style="color:#e63946">Monitor</span>
    </div>
    <div style="font-size:0.7rem;color:#888;letter-spacing:2px;text-transform:uppercase;margin-top:4px">
      Sports Performance
    </div>
  </div>

  <!-- Card -->
  <div style="background:white;border-radius:12px;padding:32px 28px;box-shadow:0 1px 3px rgba(0,0,0,0.06);border:1px solid #e8e8ee">
    {content}
  </div>

  <!-- Footer -->
  <div style="text-align:center;color:#888;font-size:0.75rem;padding:24px 8px 8px;line-height:1.6">
    LoadMonitor — Monitorização de Carga e Tomada de Decisão<br>
    <a href="https://loadmonitorsystem.com" style="color:#888;text-decoration:none">loadmonitorsystem.com</a>
  </div>

</div></body></html>"""


# ── 1. Email de boas-vindas ────────────────────────────────────────────────────
def enviar_email_boas_vindas(email: str, nome: str) -> dict:
    """Envia email de boas-vindas após registo bem-sucedido."""
    cfg = _config()
    base_url = cfg["base_url"] if cfg else "https://loadmonitorsystem.com"
    primeiro_nome = (nome or "").split()[0] if nome else ""

    content = f"""
    <h1 style="margin:0 0 16px;font-size:1.5rem;font-weight:700;color:#1a1a2e">
      Bem-vindo ao LoadMonitor{', ' + primeiro_nome if primeiro_nome else ''}!
    </h1>

    <p style="margin:0 0 16px;color:#555">
      Obrigado por criares conta. A tua <strong>trial Pro de 14 dias</strong> começa agora —
      tens acesso completo a todas as funcionalidades sem precisares de introduzir cartão.
    </p>

    <h2 style="margin:24px 0 12px;font-size:1.05rem;font-weight:700;color:#1a1a2e">
      Como começar
    </h2>

    <p style="margin:0 0 16px;color:#555">
      O LoadMonitor aceita o Excel que já usas — Catapult, STATSports, Polar, FieldWiz, WIMU,
      ou registos manuais. A app deteta automaticamente as colunas do teu ficheiro.
    </p>

    <ol style="margin:0 0 20px;padding-left:20px;color:#555">
      <li style="margin-bottom:8px">Acede à app no botão abaixo</li>
      <li style="margin-bottom:8px">Carrega o teu Excel na sidebar</li>
      <li style="margin-bottom:8px">Vê o primeiro relatório em segundos</li>
    </ol>

    <div style="text-align:center;margin:28px 0 20px">
      <a href="{base_url}" style="display:inline-block;background:#e63946;color:white;text-decoration:none;padding:14px 32px;border-radius:8px;font-weight:700;font-size:0.95rem">
        Abrir LoadMonitor
      </a>
    </div>

    <p style="margin:20px 0 16px;color:#777;font-size:0.9rem">
      Não tens Excel ainda? Dentro da app encontras um template pronto a preencher.
    </p>

    <p style="margin:24px 0 0;color:#555">
      Se tiveres dúvidas, responde a este email.<br>
      <strong>Equipa LoadMonitor</strong>
    </p>
    """

    html = _wrap_html(content, preview="A tua trial Pro de 14 dias começa agora.")
    return _enviar(email, f"Bem-vindo ao LoadMonitor{', ' + primeiro_nome if primeiro_nome else ''}", html)


# ── 2. Email de reset de password ──────────────────────────────────────────────
def enviar_email_reset_password(email: str, nome: str, token: str) -> dict:
    """Envia email com link de reset de password."""
    cfg = _config()
    base_url = cfg["base_url"] if cfg else "https://loadmonitorsystem.com"
    primeiro_nome = (nome or "").split()[0] if nome else ""
    reset_url = f"{base_url}/?reset_token={token}"

    content = f"""
    <h1 style="margin:0 0 16px;font-size:1.4rem;font-weight:700;color:#1a1a2e">
      Olá{' ' + primeiro_nome if primeiro_nome else ''},
    </h1>

    <p style="margin:0 0 20px;color:#555">
      Recebemos um pedido para repor a tua password no LoadMonitor.
    </p>

    <div style="text-align:center;margin:28px 0">
      <a href="{reset_url}" style="display:inline-block;background:#e63946;color:white;text-decoration:none;padding:14px 32px;border-radius:8px;font-weight:700;font-size:0.95rem">
        Repor password
      </a>
    </div>

    <p style="margin:20px 0 16px;color:#555">
      Este link é válido durante <strong>1 hora</strong> e só pode ser usado uma vez.
    </p>

    <p style="margin:0 0 20px;color:#777;font-size:0.9rem">
      Se não foste tu a fazer este pedido, ignora este email — a tua conta continua segura.
    </p>

    <p style="margin:24px 0 0;color:#555">
      <strong>Equipa LoadMonitor</strong>
    </p>

    <hr style="border:none;border-top:1px solid #eee;margin:28px 0 16px">

    <p style="margin:0;color:#999;font-size:0.78rem;line-height:1.55;word-break:break-all">
      Se o botão não funcionar, copia e cola este link no browser:<br>
      <span style="color:#666">{reset_url}</span>
    </p>
    """

    html = _wrap_html(content, preview="Link para repor a tua password — válido durante 1 hora.")
    return _enviar(email, "Repor a tua password — LoadMonitor", html)


# ── 3. Email — Trial a expirar ─────────────────────────────────────────────────
def enviar_email_trial_expira(email: str, nome: str, dias_restantes: int = 3) -> dict:
    """Envia aviso de trial Pro prestes a expirar."""
    cfg = _config()
    base_url = cfg["base_url"] if cfg else "https://loadmonitorsystem.com"
    primeiro_nome = (nome or "").split()[0] if nome else ""

    content = f"""
    <h1 style="margin:0 0 16px;font-size:1.4rem;font-weight:700;color:#1a1a2e">
      Olá{' ' + primeiro_nome if primeiro_nome else ''},
    </h1>

    <p style="margin:0 0 16px;color:#555">
      A tua trial Pro do LoadMonitor termina em <strong>{dias_restantes} dias</strong>.
      Não tens nada para fazer — não te vamos cobrar nada.
    </p>

    <h2 style="margin:24px 0 12px;font-size:1.05rem;font-weight:700;color:#1a1a2e">
      O que vai mudar
    </h2>

    <ul style="margin:0 0 20px;padding-left:20px;color:#555">
      <li style="margin-bottom:6px">A tua conta passa para o <strong>plano Free</strong></li>
      <li style="margin-bottom:6px">Manténs acesso ao dashboard básico, ACWR e wellness</li>
      <li style="margin-bottom:6px">Perdes análise GPS avançada, alertas e relatórios PDF</li>
    </ul>

    <h2 style="margin:24px 0 12px;font-size:1.05rem;font-weight:700;color:#1a1a2e">
      Queres continuar com o Pro?
    </h2>

    <div style="text-align:center;margin:24px 0">
      <a href="{base_url}" style="display:inline-block;background:#e63946;color:white;text-decoration:none;padding:14px 32px;border-radius:8px;font-weight:700;font-size:0.95rem">
        Activar Plano Pro — 29€/mês
      </a>
    </div>

    <p style="margin:16px 0 0;color:#888;font-size:0.85rem;text-align:center">
      Sem contrato. Cancela quando quiseres.
    </p>

    <p style="margin:24px 0 0;color:#555">
      <strong>Equipa LoadMonitor</strong>
    </p>
    """

    html = _wrap_html(content, preview=f"A tua trial Pro acaba em {dias_restantes} dias.")
    return _enviar(email, f"A tua trial Pro acaba em {dias_restantes} dias", html)


# ── 4. Email — Subscrição confirmada ───────────────────────────────────────────
def enviar_email_subscricao_confirmada(email: str, nome: str, proxima_cobranca: str = "") -> dict:
    """Envia confirmação de subscrição Pro após pagamento."""
    primeiro_nome = (nome or "").split()[0] if nome else ""
    proxima_str = proxima_cobranca or "30 dias"

    content = f"""
    <h1 style="margin:0 0 16px;font-size:1.5rem;font-weight:700;color:#1a1a2e">
      Obrigado{', ' + primeiro_nome if primeiro_nome else ''}!
    </h1>

    <p style="margin:0 0 20px;color:#555">
      A tua subscrição do <strong>Plano Pro</strong> está activa. Tens acesso a tudo o que
      o LoadMonitor oferece:
    </p>

    <ul style="margin:0 0 24px;padding-left:20px;color:#555">
      <li style="margin-bottom:6px">Atletas e equipas ilimitados</li>
      <li style="margin-bottom:6px">Análise GPS avançada (Vmáx, Sprint, ACWR)</li>
      <li style="margin-bottom:6px">Calculadora científica de exercícios</li>
      <li style="margin-bottom:6px">Relatórios PDF personalizáveis</li>
      <li style="margin-bottom:6px">Alertas automáticos por email</li>
    </ul>

    <h2 style="margin:24px 0 12px;font-size:1.05rem;font-weight:700;color:#1a1a2e">
      Detalhes da subscrição
    </h2>

    <table style="width:100%;border-collapse:collapse;margin-bottom:20px">
      <tr><td style="padding:8px 0;color:#888;font-size:0.9rem;width:40%">Plano</td>
          <td style="padding:8px 0;color:#1a1a2e;font-weight:600">Pro · 29€/mês</td></tr>
      <tr><td style="padding:8px 0;color:#888;font-size:0.9rem;border-top:1px solid #eee">Próxima cobrança</td>
          <td style="padding:8px 0;color:#1a1a2e;font-weight:600;border-top:1px solid #eee">{proxima_str}</td></tr>
      <tr><td style="padding:8px 0;color:#888;font-size:0.9rem;border-top:1px solid #eee">Cancelar</td>
          <td style="padding:8px 0;color:#1a1a2e;border-top:1px solid #eee">A qualquer momento, em Sistema → Plano</td></tr>
    </table>

    <p style="margin:0 0 16px;color:#777;font-size:0.9rem">
      A factura segue separadamente, gerada pelo Stripe.
    </p>

    <p style="margin:24px 0 0;color:#555">
      Se tiveres dúvidas, responde a este email.<br>
      <strong>Equipa LoadMonitor</strong>
    </p>
    """

    html = _wrap_html(content, preview="A tua subscrição Pro está activa.")
    return _enviar(email, "Subscrição Pro confirmada — bem-vindo ao plano!", html)
