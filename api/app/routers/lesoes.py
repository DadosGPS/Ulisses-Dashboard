from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.lesoes_service import apagar_lesao, atualizar_lesao, guardar_lesao, obter_lesoes

router = APIRouter()


@router.get("/api/teams/{team_id}/lesoes")
def lesoes(team_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    return obter_lesoes(team_id)


class LesaoBody(BaseModel):
    player_id: str
    zona: str
    lado: str | None = None
    tipo: str | None = None
    gravidade: str | None = None
    data_inicio: str
    data_fim: str | None = None
    notas: str | None = None


@router.post("/api/teams/{team_id}/lesoes")
def criar_lesao(team_id: str, body: LesaoBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    return guardar_lesao(team_id, body.player_id, body.zona, body.lado, body.tipo,
                         body.gravidade, body.data_inicio, body.data_fim, body.notas)


class LesaoUpdateBody(BaseModel):
    data_fim: str | None = None
    notas: str | None = None


@router.put("/api/teams/{team_id}/lesoes/{lesao_id}")
def editar_lesao(team_id: str, lesao_id: str, body: LesaoUpdateBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    return atualizar_lesao(team_id, lesao_id, body.data_fim, body.notas)


@router.delete("/api/teams/{team_id}/lesoes/{lesao_id}")
def remover_lesao(team_id: str, lesao_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    return apagar_lesao(team_id, lesao_id)
