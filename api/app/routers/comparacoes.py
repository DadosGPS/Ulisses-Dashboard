from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.comparacoes_service import (
    obter_comparacao_jogadores,
    obter_comparacao_posicoes,
)

router = APIRouter()


@router.get("/api/teams/{team_id}/comparacao/jogadores")
def comparacao_jogadores(
    team_id: str,
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    return obter_comparacao_jogadores(team_id)


@router.get("/api/teams/{team_id}/comparacao/posicoes")
def comparacao_posicoes(
    team_id: str,
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    return obter_comparacao_posicoes(team_id)
