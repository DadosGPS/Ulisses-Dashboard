from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.wellness_service import registar_wellness

router = APIRouter()


class WellnessBody(BaseModel):
    player_id: str
    data: str  # ISO date (YYYY-MM-DD)
    sono: int
    dor_musc: int
    stress: int
    humor: int
    notas: str | None = None


@router.post("/api/teams/{team_id}/wellness")
def registar(team_id: str, body: WellnessBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    """Regista o wellness diário de um jogador (alimenta os alertas de wellness)."""
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    try:
        return registar_wellness(
            team_id, body.player_id, body.data,
            body.sono, body.dor_musc, body.stress, body.humor, body.notas,
        )
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Não foi possível registar o bem-estar: {e}")
