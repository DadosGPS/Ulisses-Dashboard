import asyncio
import json

from fastapi import HTTPException

from app.core.i18n import traduzir
from main import app


@app.get("/_teste_i18n")
def _erro():
    raise HTTPException(400, "Jogador não encontrado.")


def _get(caminho: str, cabecalhos: dict[str, str] | None = None) -> tuple[int, dict]:
    """Pedido GET direto à app ASGI (sem cliente HTTP de teste)."""
    enviado: list[dict] = []

    async def receber():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def enviar(msg):
        enviado.append(msg)

    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "GET", "scheme": "http",
        "path": caminho, "raw_path": caminho.encode(), "query_string": b"", "root_path": "",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (cabecalhos or {}).items()],
        "client": ("127.0.0.1", 1), "server": ("teste", 80),
    }
    asyncio.run(app(scope, receber, enviar))
    estado = next(m["status"] for m in enviado if m["type"] == "http.response.start")
    corpo = b"".join(m.get("body", b"") for m in enviado if m["type"] == "http.response.body")
    return estado, json.loads(corpo)


def test_traduzir_texto_e_padrao():
    assert traduzir("Jogador não encontrado.", "en") == "Player not found."
    assert traduzir("Jogador não encontrado.", "pt") == "Jogador não encontrado."
    assert traduzir("Já existe o MC 4.", "en") == "MC 4 already exists."
    assert traduzir("Mensagem sem tradução.", "en") == "Mensagem sem tradução."


def test_middleware_traduz_detail():
    assert _get("/_teste_i18n") == (400, {"detail": "Jogador não encontrado."})
    assert _get("/_teste_i18n", {"X-Lingua": "en"}) == (400, {"detail": "Player not found."})
