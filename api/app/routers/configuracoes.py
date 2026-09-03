from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.configuracoes_service import (
    atualizar_equipa,
    atualizar_jogador,
    criar_jogador,
    obter_configuracoes,
)
from app.services.limites_service import guardar_limites, obter_limites

router = APIRouter()


def _guard(utilizador: UtilizadorAtual, team_id: str) -> None:
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")


@router.get("/api/teams/{team_id}/configuracoes")
def configuracoes(team_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _guard(utilizador, team_id)
    return obter_configuracoes(team_id)


class EquipaUpdate(BaseModel):
    nome: str
    desporto: str | None = None


@router.patch("/api/teams/{team_id}/configuracoes/equipa")
def editar_equipa(team_id: str, body: EquipaUpdate, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _guard(utilizador, team_id)
    try:
        return atualizar_equipa(team_id, body.nome, body.desporto)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


class JogadorCreate(BaseModel):
    nome: str
    posicao: str | None = None


@router.post("/api/teams/{team_id}/configuracoes/jogadores")
def novo_jogador(team_id: str, body: JogadorCreate, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _guard(utilizador, team_id)
    try:
        return criar_jogador(team_id, body.nome, body.posicao)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


class JogadorUpdate(BaseModel):
    nome: str
    posicao: str | None = None


@router.patch("/api/teams/{team_id}/configuracoes/jogadores/{player_id}")
def editar_jogador(team_id: str, player_id: str, body: JogadorUpdate, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _guard(utilizador, team_id)
    try:
        resultado = atualizar_jogador(team_id, player_id, body.nome, body.posicao)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    if resultado is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jogador não encontrado.")
    return resultado


@router.get("/api/teams/{team_id}/configuracoes/limites")
def limites(team_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _guard(utilizador, team_id)
    return obter_limites(utilizador.user_id)


@router.patch("/api/teams/{team_id}/configuracoes/limites")
def editar_limites(team_id: str, body: dict, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _guard(utilizador, team_id)
    return guardar_limites(utilizador.user_id, body)
