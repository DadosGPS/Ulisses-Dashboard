from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual

router = APIRouter()


# ── Microciclos (linha temporal) e plano das sessões ─────────────────────────
from app.services import microciclos_service as mcs  # noqa: E402


def _guard_mc(utilizador: UtilizadorAtual, team_id: str):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    if not mcs.disponivel():
        raise HTTPException(status.HTTP_409_CONFLICT, mcs.MSG_MIGRACAO)


def _exec(fn, *args):
    try:
        return fn(*args)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.get("/api/teams/{team_id}/microciclos")
def microciclos(team_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    if not mcs.disponivel():
        return {"disponivel": False, "motivo": mcs.MSG_MIGRACAO, "microciclos": []}
    return mcs.listar(team_id)


class MicrocicloBody(BaseModel):
    numero: int
    nome: str | None = None
    tipo: str = "Normal"
    perfil: str | None = None
    fase: str | None = None
    data_inicio: str
    data_fim: str
    fatores: dict = {}
    notas: str | None = None


@router.post("/api/teams/{team_id}/microciclos")
def criar_microciclo(team_id: str, body: MicrocicloBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _guard_mc(utilizador, team_id)
    return _exec(mcs.criar, team_id, body.model_dump())


@router.put("/api/teams/{team_id}/microciclos/{mc_id}")
def editar_microciclo(team_id: str, mc_id: str, body: MicrocicloBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _guard_mc(utilizador, team_id)
    return _exec(mcs.atualizar, team_id, mc_id, body.model_dump())


@router.delete("/api/teams/{team_id}/microciclos/{mc_id}")
def apagar_microciclo(team_id: str, mc_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _guard_mc(utilizador, team_id)
    return mcs.apagar(team_id, mc_id)


@router.post("/api/teams/{team_id}/microciclos/{mc_id}/duplicar")
def duplicar_microciclo(team_id: str, mc_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _guard_mc(utilizador, team_id)
    return _exec(mcs.duplicar, team_id, mc_id)


class GerarBody(BaseModel):
    inicio: str
    semanas: int
    numero_inicial: int | None = None
    perfil: str | None = None


@router.post("/api/teams/{team_id}/microciclos/gerar")
def gerar_microciclos(team_id: str, body: GerarBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _guard_mc(utilizador, team_id)
    return _exec(mcs.gerar, team_id, body.inicio, body.semanas, body.numero_inicial, body.perfil)
