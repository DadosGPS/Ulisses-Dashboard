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


@router.get("/api/teams/{team_id}/perfil-individual")
def perfil_individual(
    team_id: str,
    dias: int = 28,
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    """Velocidade e acelerações face às capacidades de cada jogador (export Sonra)."""
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    from app.services.perfil_individual_service import obter_perfil_individual

    return obter_perfil_individual(team_id, dias)
