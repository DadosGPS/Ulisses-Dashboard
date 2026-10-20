"""Mensagens aos jogadores (bem-estar e PSE por WhatsApp).

- /api/teams/{team_id}/mensagens…  → staff autenticado (configuração, envio)
- /api/r/{token}                   → PÚBLICO: o jogador abre o link e responde
- /api/cron/mensagens              → agendador, protegido por X-Cron-Secret
"""
from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services import mensagens_service as ms
from app.services import whatsapp_service

router = APIRouter()


def _guard(team_id: str, utilizador: UtilizadorAtual) -> None:
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    if not ms.tabelas_disponiveis():
        raise HTTPException(status.HTTP_409_CONFLICT, ms.MSG_MIGRACAO)


def _dia(valor: str | None) -> date:
    if not valor:
        return ms.agora().date()
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Data inválida (AAAA-MM-DD).")


@router.get("/api/teams/{team_id}/mensagens")
def estado(team_id: str, data: str | None = None, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    if not ms.tabelas_disponiveis():
        return {"disponivel": False, "motivo": ms.MSG_MIGRACAO}
    s = get_settings()
    dia = _dia(data)
    return {
        "disponivel": True,
        "motivo": None,
        "data": dia.isoformat(),
        "twilio": {
            "configurado": whatsapp_service.configurado(),
            "modelo_wellness": bool(s.twilio_template_wellness),
            "modelo_pse": bool(s.twilio_template_pse),
            "agendador": bool(s.cron_secret),
        },
        "config": ms.obter_config(team_id),
        "contactos": ms.listar_contactos(team_id),
        "dia": ms.estado_do_dia(team_id, dia),
    }


class ConfigBody(BaseModel):
    wellness_auto: bool
    wellness_hora: str
    wellness_dias: list[int]


@router.put("/api/teams/{team_id}/mensagens/config")
def editar_config(team_id: str, body: ConfigBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _guard(team_id, utilizador)
    try:
        return ms.guardar_config(team_id, body.wellness_auto, body.wellness_hora, body.wellness_dias)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


class ContactoBody(BaseModel):
    telefone: str | None = None
    consentimento: bool = False


@router.patch("/api/teams/{team_id}/mensagens/contactos/{player_id}")
def editar_contacto(team_id: str, player_id: str, body: ContactoBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _guard(team_id, utilizador)
    try:
        return ms.guardar_contacto(team_id, player_id, body.telefone, body.consentimento)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


class EnvioBody(BaseModel):
    data: str | None = None
    player_ids: list[str] | None = None
    duracao_min: float | None = None
    reenviar: bool = False


@router.post("/api/teams/{team_id}/mensagens/wellness")
def enviar_wellness(team_id: str, body: EnvioBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _guard(team_id, utilizador)
    return ms.enviar_pedidos(team_id, "wellness", _dia(body.data), body.player_ids, reenviar=body.reenviar)


@router.post("/api/teams/{team_id}/mensagens/pse")
def pedir_pse(team_id: str, body: EnvioBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _guard(team_id, utilizador)
    if body.duracao_min is not None and not 0 < body.duracao_min <= 240:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Duração inválida (1–240 minutos).")
    return ms.enviar_pedidos(team_id, "pse", _dia(body.data), body.player_ids, body.duracao_min, reenviar=body.reenviar)


class MarcarBody(BaseModel):
    token: str


@router.post("/api/teams/{team_id}/mensagens/marcar-enviado")
def marcar(team_id: str, body: MarcarBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _guard(team_id, utilizador)
    return ms.marcar_enviado(team_id, body.token)


# ── Público: resposta do jogador ─────────────────────────────────────────────
@router.get("/api/r/{token}")
def pedido_publico(token: str):
    p = ms.obter_pedido_publico(token)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Link inválido.")
    return p


@router.post("/api/r/{token}")
def resposta_publica(token: str, body: dict):
    try:
        return ms.responder(token, body)
    except LookupError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except PermissionError as e:
        raise HTTPException(status.HTTP_410_GONE, str(e))
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


# ── Agendador ────────────────────────────────────────────────────────────────
@router.post("/api/cron/mensagens")
def cron(x_cron_secret: str | None = Header(default=None)):
    segredo = get_settings().cron_secret
    if not segredo or x_cron_secret != segredo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Não autorizado.")
    if not ms.tabelas_disponiveis():
        return {"ok": False, "motivo": ms.MSG_MIGRACAO}
    return {"ok": True, **ms.envio_automatico()}
