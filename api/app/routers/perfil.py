from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.testes_service import obter_perfis, obter_perfis_academia

router = APIRouter()


@router.get("/api/teams/{team_id}/perfil")
def perfil(
    team_id: str,
    momento: int | None = None,
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    """Perfil dos jogadores por testes. Usa os testes da academia (velocidade,
    1 km, saltos — T1–T4 da época); sem eles, os testes importados com o GPS."""
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    if momento is not None and momento not in (1, 2, 3, 4):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "O momento de avaliação vai de T1 a T4.")
    academia = obter_perfis_academia(utilizador.user_id, team_id, momento)
    if academia:
        return academia
    return {**obter_perfis(team_id), "fonte": "gps"}
