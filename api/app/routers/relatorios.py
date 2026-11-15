from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.relatorios_service import obter_jogo, obter_treino

router = APIRouter()


def _acesso(utilizador: UtilizadorAtual, team_id: str) -> None:
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")


def _data_valida(data: str | None) -> None:
    from datetime import date
    if data:
        try:
            date.fromisoformat(data)
        except ValueError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Data inválida (usa AAAA-MM-DD).")


@router.get("/api/teams/{team_id}/relatorios/treino")
def relatorio_treino(team_id: str, data: str | None = None, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    """Relatório de um treino: alvo do dia por jogador, habitual por dia MD e exercícios."""
    _acesso(utilizador, team_id)
    _data_valida(data)
    return obter_treino(team_id, data)


@router.get("/api/teams/{team_id}/relatorios/jogo")
def relatorio_jogo(team_id: str, data: str | None = None, jogador: str | None = None,
                   utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    """Relatório de um jogo: equipa vs época, jogadores vs a própria época, 1.ª vs 2.ª parte."""
    _acesso(utilizador, team_id)
    _data_valida(data)
    return obter_jogo(team_id, data, jogador)
