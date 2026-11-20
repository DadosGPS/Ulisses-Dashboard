"""Ligação a folhas do Google Sheets: PSE dos jogadores e wellness diário.

Todas as rotas da equipa aceitam ?tipo=pse (por omissão) ou ?tipo=wellness.

- GET    /api/teams/{team_id}/google-sheets              → configuração e estado
- PUT    /api/teams/{team_id}/google-sheets              → liga / altera a folha
- DELETE /api/teams/{team_id}/google-sheets              → desliga
- POST   /api/teams/{team_id}/google-sheets/sincronizar  → importa agora
- POST   /api/cron/google-sheets                         → agendador (X-Cron-Secret)
"""
from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services import google_sheets_service as gs

router = APIRouter()


class ConfigGoogleSheets(BaseModel):
    url: str
    folha: str = "RPE"
    data_inicio: date
    filtro_equipa: str | None = None
    ativo: bool = True


TipoFonte = Query("pse", pattern="^(pse|wellness)$")


def _verificar(utilizador: UtilizadorAtual, team_id: str) -> None:
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")


@router.get("/api/teams/{team_id}/google-sheets")
def obter(team_id: str, tipo: str = TipoFonte, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _verificar(utilizador, team_id)
    return gs.obter_config(team_id, tipo)


@router.put("/api/teams/{team_id}/google-sheets")
def guardar(team_id: str, corpo: ConfigGoogleSheets, tipo: str = TipoFonte,
            utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _verificar(utilizador, team_id)
    try:
        fonte = gs.guardar_config(team_id, utilizador.user_id, corpo.url, corpo.folha, corpo.data_inicio,
                                  corpo.filtro_equipa, corpo.ativo, tipo)
    except gs.ErroGoogleSheets as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "A ligação ao Google Sheets precisa das migrações 0028 e 0029 (supabase/migrations) "
                            "(aplica-se sozinha no próximo deploy, ou no SQL Editor do Supabase).")
    return {"email_conta_servico": gs.email_conta_servico(), "fonte": fonte}


@router.delete("/api/teams/{team_id}/google-sheets")
def remover(team_id: str, tipo: str = TipoFonte, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _verificar(utilizador, team_id)
    gs.remover_config(team_id, tipo)
    return {"ok": True}


@router.post("/api/teams/{team_id}/google-sheets/sincronizar")
async def sincronizar(team_id: str, tipo: str = TipoFonte, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    await run_in_threadpool(_verificar, utilizador, team_id)
    try:
        return await run_in_threadpool(gs.sincronizar, team_id, utilizador.user_id, tipo)
    except gs.ErroGoogleSheets as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.post("/api/teams/{team_id}/google-sheets/sincronizar-se-preciso")
async def sincronizar_se_preciso(team_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    """Chamado pela app ao abrir e ao voltar a ela: relê as folhas com mais de 2 min."""
    await run_in_threadpool(_verificar, utilizador, team_id)
    return await run_in_threadpool(gs.sincronizar_se_preciso, team_id, utilizador.user_id)


@router.post("/api/cron/google-sheets")
def cron(x_cron_secret: str | None = Header(default=None)):
    segredo = get_settings().cron_secret
    if not segredo or x_cron_secret != segredo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Não autorizado.")
    return gs.sincronizar_todas()
