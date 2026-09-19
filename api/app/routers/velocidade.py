from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.velocidade_service import (
    PCT_MECANICO,
    PCT_METABOLICO,
    PCT_SPRINT,
    obter_perfil_velocidade,
)

router = APIRouter()


@router.get("/api/teams/{team_id}/velocidade")
def velocidade(
    team_id: str,
    pct_metabolico: int = PCT_METABOLICO,
    pct_mecanico: int = PCT_MECANICO,
    pct_sprint: int = PCT_SPRINT,
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    return obter_perfil_velocidade(team_id, pct_metabolico, pct_mecanico, pct_sprint)
