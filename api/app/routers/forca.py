from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services import forca_service as fs

router = APIRouter()


def _verificar(utilizador: UtilizadorAtual, team_id: str) -> None:
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")


def _erros(f):
    try:
        return f()
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except LookupError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.get("/api/teams/{team_id}/forca/sessoes")
def listar(team_id: str, desde: str | None = None, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _verificar(utilizador, team_id)
    return _erros(lambda: fs.listar_sessoes(team_id, desde))


class Linha(BaseModel):
    exercicio: str
    series: float | None = None
    repeticoes: float | None = None
    carga_kg: float | None = None
    feito: bool = True


class NovaSessao(BaseModel):
    data: str
    nome: str
    duracao_min: int | None = None
    prescricao: list[Linha]
    jogadores: list[str]
    notas: str | None = None


@router.post("/api/teams/{team_id}/forca/sessoes")
def criar(team_id: str, body: NovaSessao, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _verificar(utilizador, team_id)
    if not fs.disponivel():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, fs.MSG_MIGRACAO)
    return _erros(lambda: fs.criar_sessao(team_id, utilizador.user_id, body.data, body.nome, body.duracao_min,
                                          [l.model_dump() for l in body.prescricao], body.jogadores, body.notas))


@router.get("/api/teams/{team_id}/forca/sessoes/{sessao_id}")
def ver(team_id: str, sessao_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _verificar(utilizador, team_id)
    return _erros(lambda: fs.obter_sessao(team_id, sessao_id))


class RegistoJogador(BaseModel):
    linhas: list[Linha]
    pse: float | None = None
    duracao_min: float | None = None


@router.put("/api/teams/{team_id}/forca/sessoes/{sessao_id}/jogadores/{player_id}")
def guardar(team_id: str, sessao_id: str, player_id: str, body: RegistoJogador,
            utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _verificar(utilizador, team_id)
    return _erros(lambda: fs.guardar_jogador(team_id, sessao_id, player_id, [l.model_dump() for l in body.linhas],
                                             body.pse, body.duracao_min))


@router.delete("/api/teams/{team_id}/forca/sessoes/{sessao_id}")
def apagar(team_id: str, sessao_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _verificar(utilizador, team_id)
    return fs.apagar_sessao(team_id, sessao_id)


@router.get("/api/teams/{team_id}/forca/jogador/{player_id}")
def jogador(team_id: str, player_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _verificar(utilizador, team_id)
    return fs.perfil_jogador(team_id, player_id)
