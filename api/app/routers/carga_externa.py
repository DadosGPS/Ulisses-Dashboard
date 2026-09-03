from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.carga_externa_service import obter_carga_externa

router = APIRouter()


@router.get("/api/teams/{team_id}/carga-externa")
def carga_externa(
    team_id: str,
    tipo: str | None = None,
    posicao: str | None = None,
    dia_md: str | None = None,
    microciclo: int | None = None,
    baseline_dias: int = 28,
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")

    return obter_carga_externa(team_id, tipo, posicao, dia_md, microciclo, baseline_dias)
