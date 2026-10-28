from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.limites_service import obter_limites_equipa
from app.services.prontidao_service import obter_prontidao

router = APIRouter()


@router.get("/api/teams/{team_id}/prontidao")
def prontidao(team_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    """Prontidão por jogador: CMJ e Hooper vs a média própria + ACWR diário."""
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    return obter_prontidao(team_id, obter_limites_equipa(team_id, utilizador.user_id))
