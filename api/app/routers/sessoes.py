from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.sessoes_service import listar_sessoes

router = APIRouter()


@router.get("/api/teams/{team_id}/sessoes")
def sessoes(
    team_id: str,
    jogador: str | None = None,
    microciclo: int | None = None,
    dia_md: str | None = None,
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    return listar_sessoes(team_id, jogador=jogador, microciclo=microciclo, dia_md=dia_md)
