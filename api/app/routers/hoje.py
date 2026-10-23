"""«Hoje» — tarefas do dia do preparador físico (ver hoje_service)."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.core.security import UtilizadorAtual, verify_team_membership
from app.services import hoje_service, mensagens_service as ms, semana_jogadores_service

router = APIRouter()


@router.get("/api/teams/{team_id}/hoje")
async def hoje(team_id: str, data: str | None = None, utilizador: UtilizadorAtual = Depends(verify_team_membership)):
    fuso = None
    if await run_in_threadpool(ms.tabelas_disponiveis):
        fuso = (await run_in_threadpool(ms.obter_config, team_id)).get("fuso")
    hoje_local = ms.agora(fuso).date()
    try:
        dia = date.fromisoformat(data) if data else hoje_local
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Data inválida (AAAA-MM-DD).")
    return await run_in_threadpool(hoje_service.obter, team_id, utilizador.user_id, dia, hoje_local)


@router.get("/api/teams/{team_id}/semana-jogadores")
async def semana_jogadores(team_id: str, microciclo: int | None = None, data: str | None = None,
                           utilizador: UtilizadorAtual = Depends(verify_team_membership)):
    """Objetivo semanal por jogador e compensação pós-jogo."""
    fuso = None
    if await run_in_threadpool(ms.tabelas_disponiveis):
        fuso = (await run_in_threadpool(ms.obter_config, team_id)).get("fuso")
    try:
        dia = date.fromisoformat(data) if data else ms.agora(fuso).date()
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Data inválida (AAAA-MM-DD).")
    return await run_in_threadpool(semana_jogadores_service.obter, team_id, dia, microciclo)
