from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.analise_service import obter_analise
from app.services.limites_service import obter_limites

router = APIRouter()


@router.get("/api/teams/{team_id}/analise")
def analise(
    team_id: str,
    microciclo: int | None = None,
    dia_md: str | None = None,
    jogador: str | None = None,
    comparar: int | None = None,
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")

    # Mesmos limiares configuráveis que o dashboard usa — a Análise deixa de ter
    # números fixos no código e passa a respeitar o que o utilizador definiu.
    return obter_analise(team_id, microciclo, dia_md, jogador, comparar, limites=obter_limites(utilizador.user_id))
