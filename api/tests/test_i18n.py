from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.i18n import traduzir
from main import app


@app.get("/_teste_i18n")
def _erro():
    raise HTTPException(400, "Jogador não encontrado.")


def test_traduzir_texto_e_padrao():
    assert traduzir("Jogador não encontrado.", "en") == "Player not found."
    assert traduzir("Jogador não encontrado.", "pt") == "Jogador não encontrado."
    assert traduzir("Já existe o MC 4.", "en") == "MC 4 already exists."
    assert traduzir("Mensagem sem tradução.", "en") == "Mensagem sem tradução."


def test_middleware_traduz_detail():
    c = TestClient(app)
    assert c.get("/_teste_i18n").json()["detail"] == "Jogador não encontrado."
    assert c.get("/_teste_i18n", headers={"X-Lingua": "en"}).json()["detail"] == "Player not found."
