from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.filtros_service import obter_filtros

router = APIRouter()


@router.get("/api/teams/{team_id}/filtros")
def filtros(team_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    return obter_filtros(team_id)
