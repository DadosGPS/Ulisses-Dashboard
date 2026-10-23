"""«Hoje» — tarefas do dia do preparador físico (ver hoje_service)."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.core.security import UtilizadorAtual, verify_team_membership
from app.services import hoje_service, mensagens_service as ms

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
