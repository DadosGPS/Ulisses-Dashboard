from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.rtp_service import atualizar_plano, criar_plano, listar_planos

router = APIRouter()


def _verificar(team_id: str, utilizador: UtilizadorAtual) -> None:
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")


@router.get("/api/teams/{team_id}/rtp")
def planos(team_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    """Planos de regresso ao jogo com o progresso avaliado a partir do GPS."""
    _verificar(team_id, utilizador)
    return listar_planos(team_id)


class PlanoBody(BaseModel):
    player_id: str
    data_inicio: str
    etapas: list[dict] | None = None
    sessoes_por_etapa: int | None = None
    lesao_id: str | None = None
    notas: str | None = None


@router.post("/api/teams/{team_id}/rtp")
def novo_plano(team_id: str, body: PlanoBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _verificar(team_id, utilizador)
    out = criar_plano(team_id, body.player_id, body.data_inicio, body.etapas, body.sessoes_por_etapa, body.lesao_id, body.notas)
    if not out.get("ok"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, out.get("erro") or "Jogador não encontrado.")
    return out


class PlanoUpdateBody(BaseModel):
    etapas: list[dict] | None = None
    sessoes_por_etapa: int | None = None
    estado: str | None = None
    notas: str | None = None
    data_inicio: str | None = None


@router.put("/api/teams/{team_id}/rtp/{plano_id}")
def editar_plano(team_id: str, plano_id: str, body: PlanoUpdateBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _verificar(team_id, utilizador)
    out = atualizar_plano(team_id, plano_id, body.etapas, body.sessoes_por_etapa, body.estado, body.notas, body.data_inicio)
    if not out.get("ok"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, out.get("erro") or "Plano não encontrado.")
    return out
