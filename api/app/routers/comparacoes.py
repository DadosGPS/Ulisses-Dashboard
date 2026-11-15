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
    microciclo: int | None = None,
    dia_md: str | None = None,
    contexto: str = "todos",
    por_minuto: bool = False,
    ultimos: int | None = None,
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    if contexto not in ("todos", "jogos", "treinos"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Contexto inválido.")
    return obter_comparacao_jogadores(team_id, microciclo, dia_md, contexto, por_minuto, ultimos)


@router.get("/api/teams/{team_id}/comparacao/posicoes")
def comparacao_posicoes(
    team_id: str,
    microciclo: int | None = None,
    dia_md: str | None = None,
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    return obter_comparacao_posicoes(team_id, microciclo, dia_md)
