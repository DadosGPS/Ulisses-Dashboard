from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.jogador_service import obter_jogador

router = APIRouter()


@router.get("/api/teams/{team_id}/jogador")
def jogador(
    team_id: str,
    nome: str | None = None,
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")

    from app.services.jogador_service import listar_jogadores

    jogadores = listar_jogadores(team_id)
    if not jogadores:
        return {"jogadores_disponiveis": [], "jogador": None}

    nome_alvo = nome if nome and nome in [j["nome"] for j in jogadores] else jogadores[0]["nome"]
    resultado = obter_jogador(team_id, nome_alvo)
    if resultado is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jogador não encontrado.")

    return resultado
