from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services import decisoes_service as ds

router = APIRouter()


def _verificar(utilizador: UtilizadorAtual, team_id: str) -> None:
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")


@router.get("/api/teams/{team_id}/decisoes")
def listar(team_id: str, desde: str | None = None, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    """Decisões registadas (as mais recentes primeiro), opcionalmente desde uma data."""
    _verificar(utilizador, team_id)
    try:
        return ds.listar(team_id, desde)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.get("/api/teams/{team_id}/decisoes/resumo")
def resumo(team_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    """Por sinal: decisões de cada tipo e o que aconteceu nos 14 dias seguintes."""
    _verificar(utilizador, team_id)
    from app.services.limites_service import obter_limites_equipa
    return ds.obter_resumo(team_id, obter_limites_equipa(team_id, utilizador.user_id))


class DecisaoBody(BaseModel):
    jogador: str
    player_id: str | None = None
    data: str
    sinal: str
    decisao: str
    nota: str | None = None
    detalhe: dict | None = None


@router.post("/api/teams/{team_id}/decisoes")
def registar(team_id: str, body: DecisaoBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _verificar(utilizador, team_id)
    if not ds.disponivel():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, ds.MSG_MIGRACAO)
    try:
        return ds.registar(team_id, utilizador.user_id, body.jogador, body.player_id, body.data,
                           body.sinal, body.decisao, body.detalhe, body.nota)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.delete("/api/teams/{team_id}/decisoes/{decisao_id}")
def apagar(team_id: str, decisao_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _verificar(utilizador, team_id)
    return ds.apagar(team_id, decisao_id)
