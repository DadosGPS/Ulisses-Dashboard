from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.ia_service import perguntar, resumo_staff
from app.services.limites_service import obter_limites

router = APIRouter()


def _guard(utilizador: UtilizadorAtual, team_id: str) -> None:
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")


class Mensagem(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class PerguntaBody(BaseModel):
    pergunta: str
    historico: list[Mensagem] | None = None


@router.post("/api/teams/{team_id}/ia/resumo")
def ia_resumo(team_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    """Resumo para o treinador gerado pela assistente de IA."""
    _guard(utilizador, team_id)
    r = resumo_staff(team_id, obter_limites(utilizador.user_id))
    if not r.get("ok"):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, r.get("erro", "Assistente indisponível."))
    return r


@router.post("/api/teams/{team_id}/ia/perguntar")
def ia_perguntar(team_id: str, body: PerguntaBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    """Pergunta livre à assistente, respondida a partir dos dados da equipa."""
    _guard(utilizador, team_id)
    pergunta = (body.pergunta or "").strip()
    if not pergunta:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Escreve uma pergunta.")
    historico = [m.model_dump() for m in (body.historico or [])][-10:]  # limita o contexto
    r = perguntar(team_id, pergunta, historico, obter_limites(utilizador.user_id))
    if not r.get("ok"):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, r.get("erro", "Assistente indisponível."))
    return r
