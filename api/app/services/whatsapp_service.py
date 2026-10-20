"""Envio de mensagens WhatsApp pela API REST da Twilio (sem dependências novas).

O WhatsApp só deixa uma empresa iniciar conversa com um MODELO de mensagem
aprovado pela Meta. Por isso, com `twilio_template_*` definido envia-se o
modelo (ContentSid + variáveis {{1}} nome, {{2}} link); sem ele envia-se texto
livre, que só funciona na sandbox da Twilio ou dentro de 24 h de uma resposta
do jogador.

Sem credenciais, `configurado()` é falso e quem chama trata o envio como
«simulado» (o link é gerado e mostrado na app para partilhar à mão).
"""
from __future__ import annotations

import base64
import json
import re
import urllib.error
import urllib.parse
import urllib.request

from app.core.config import get_settings

TIMEOUT_S = 15


def configurado() -> bool:
    s = get_settings()
    return bool(s.twilio_account_sid and s.twilio_auth_token and s.twilio_whatsapp_from)


def normalizar_telefone(telefone: str | None) -> str | None:
    """Devolve o número em E.164 (+351912345678) ou None se não for válido.
    Um número português de 9 dígitos sem indicativo recebe +351."""
    if not telefone:
        return None
    t = re.sub(r"[\s\-().]", "", str(telefone))
    if t.startswith("00"):
        t = "+" + t[2:]
    if re.fullmatch(r"9\d{8}", t):
        t = "+351" + t
    return t if re.fullmatch(r"\+\d{8,15}", t) else None


def enviar(telefone: str, texto: str, template_sid: str | None = None, variaveis: dict | None = None) -> tuple[bool, str | None]:
    """Envia uma mensagem. Devolve (sucesso, erro)."""
    s = get_settings()
    numero = normalizar_telefone(telefone)
    if not numero:
        return False, "Número de telefone inválido."
    origem = s.twilio_whatsapp_from if s.twilio_whatsapp_from.startswith("whatsapp:") else f"whatsapp:{s.twilio_whatsapp_from}"
    campos = {"From": origem, "To": f"whatsapp:{numero}"}
    if template_sid:
        campos["ContentSid"] = template_sid
        campos["ContentVariables"] = json.dumps(variaveis or {})
    else:
        campos["Body"] = texto

    url = f"https://api.twilio.com/2010-04-01/Accounts/{s.twilio_account_sid}/Messages.json"
    pedido = urllib.request.Request(url, data=urllib.parse.urlencode(campos).encode(), method="POST")
    credenciais = base64.b64encode(f"{s.twilio_account_sid}:{s.twilio_auth_token}".encode()).decode()
    pedido.add_header("Authorization", f"Basic {credenciais}")
    try:
        with urllib.request.urlopen(pedido, timeout=TIMEOUT_S) as resp:
            return 200 <= resp.status < 300, None
    except urllib.error.HTTPError as e:
        try:
            detalhe = json.loads(e.read().decode()).get("message")
        except Exception:
            detalhe = None
        return False, f"Twilio {e.code}: {detalhe or e.reason}"
    except Exception as e:  # rede, timeout
        return False, f"Falha de ligação à Twilio: {e}"
