from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.estado_service import atualizar_ativo, atualizar_estado, listar_estados
from app.services.jogador_service import obter_jogador

router = APIRouter()


@router.get("/api/teams/{team_id}/jogador")
def jogador(
    team_id: str,
    nome: str | None = None,
    microciclo: int | None = None,
    dia_md: str | None = None,
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")

    from app.services.jogador_service import listar_jogadores

    jogadores = listar_jogadores(team_id)
    if not jogadores:
        return {"jogadores_disponiveis": [], "jogador": None}

    nome_alvo = nome if nome and nome in [j["nome"] for j in jogadores] else jogadores[0]["nome"]
    resultado = obter_jogador(team_id, nome_alvo, microciclo, dia_md)
    if resultado is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jogador não encontrado.")

    return resultado


class EstadoUpdate(BaseModel):
    estado: str
    motivo: str | None = None


@router.get("/api/teams/{team_id}/jogadores/estado")
def estados(team_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    return {"jogadores": listar_estados(team_id)}


@router.patch("/api/teams/{team_id}/jogadores/{player_id}/estado")
def estado_jogador(
    team_id: str,
    player_id: str,
    body: EstadoUpdate,
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    try:
        resultado = atualizar_estado(team_id, player_id, body.estado, body.motivo)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    if resultado is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jogador não encontrado.")
    return resultado


class AtivoUpdate(BaseModel):
    ativo: bool


@router.patch("/api/teams/{team_id}/jogadores/{player_id}/ativo")
def ativo_jogador(
    team_id: str,
    player_id: str,
    body: AtivoUpdate,
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    resultado = atualizar_ativo(team_id, player_id, body.ativo)
    if resultado is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jogador não encontrado.")
    return resultado
