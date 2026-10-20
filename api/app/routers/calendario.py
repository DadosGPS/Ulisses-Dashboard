from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services import calendario_service as cal

router = APIRouter()


def _guard(utilizador: UtilizadorAtual, team_id: str):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")


@router.get("/api/teams/{team_id}/calendario")
def calendario(team_id: str, inicio: str, fim: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _guard(utilizador, team_id)
    try:
        return cal.obter(team_id, inicio, fim)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


class EventoBody(BaseModel):
    data: str
    titulo: str
    categoria: str = "Outro"


@router.post("/api/teams/{team_id}/calendario/eventos")
def novo_evento(team_id: str, body: EventoBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _guard(utilizador, team_id)
    try:
        return cal.criar_evento(team_id, utilizador.user_id, body.data, body.titulo, body.categoria)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.delete("/api/teams/{team_id}/calendario/eventos/{evento_id}")
def apagar_evento(team_id: str, evento_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _guard(utilizador, team_id)
    return cal.apagar_evento(team_id, evento_id)
