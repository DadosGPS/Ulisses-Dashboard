from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.carga_planeada_service import guardar_carga_planeada, obter_carga_planeada_semana
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


@router.get("/api/teams/{team_id}/planeamento/carga-semana")
def carga_semana(
    team_id: str,
    microciclo: int | None = None,
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    return obter_carga_planeada_semana(team_id, microciclo)


class CargaPlaneadaBody(BaseModel):
    microciclo: int
    dia_md: str
    distancia_m: float | None = None
    hsr_m: float | None = None
    sprint_m: float | None = None


@router.put("/api/teams/{team_id}/planeamento/carga-planeada")
def carga_planeada(
    team_id: str,
    body: CargaPlaneadaBody,
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    return guardar_carga_planeada(team_id, body.microciclo, body.dia_md, body.distancia_m, body.hsr_m, body.sprint_m)
