from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.jogador_service import listar_jogadores
from app.services.planeamento_service import obter_planeamento
from app.services.pse_planeado_service import guardar_pse_planeada, obter_pse_semana

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


@router.get("/api/teams/{team_id}/planeamento/pse-semana")
def pse_semana(
    team_id: str,
    microciclo: int | None = None,
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    return obter_pse_semana(team_id, microciclo)


class PseEsperadaBody(BaseModel):
    microciclo: int
    dia_md: str
    pse_esperada: float


@router.put("/api/teams/{team_id}/planeamento/pse-esperada")
def pse_esperada(
    team_id: str,
    body: PseEsperadaBody,
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    return guardar_pse_planeada(team_id, body.microciclo, body.dia_md, body.pse_esperada)
