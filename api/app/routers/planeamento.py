from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.jogador_service import listar_jogadores
from app.services.planeamento_service import obter_planeamento

router = APIRouter()


@router.get("/api/teams/{team_id}/planeamento")
def planeamento(
    team_id: str,
    jogador: str | None = None,
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")

    resultado = obter_planeamento(team_id, jogador)
    resultado["jogadores_disponiveis"] = [j["nome"] for j in listar_jogadores(team_id)]
    resultado["jogador_selecionado"] = jogador
    return resultado
