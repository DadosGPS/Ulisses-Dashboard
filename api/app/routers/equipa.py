from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.equipa_service import obter_equipa
from app.services.mapa_calor_service import obter_mapa_calor

router = APIRouter()


@router.get("/api/teams/{team_id}/equipa")
def equipa(
    team_id: str,
    micro_inicio: int | None = None,
    micro_fim: int | None = None,
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")

    return obter_equipa(team_id, micro_inicio, micro_fim)


@router.get("/api/teams/{team_id}/mapa-calor")
def mapa_calor(
    team_id: str,
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")

    return obter_mapa_calor(team_id)
