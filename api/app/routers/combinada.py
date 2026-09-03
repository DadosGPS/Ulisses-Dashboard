from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.combinada_service import obter_combinada

router = APIRouter()


@router.get("/api/teams/{team_id}/combinada")
def combinada(
    team_id: str,
    microciclo: int | None = None,
    dia_md: str | None = None,
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    return obter_combinada(team_id, microciclo, dia_md)
