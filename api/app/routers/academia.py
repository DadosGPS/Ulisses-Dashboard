"""Academia: estrutura escalões × épocas e equipas do utilizador."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.db import get_conn
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services import academia_service as acad

router = APIRouter()


def _equipas_simples(user_id: str) -> list[dict]:
    """Antes da migração 0009: só as equipas, para o seletor funcionar."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select t.id, t.nome from teams t join team_members tm on tm.team_id = t.id where tm.user_id = %s order by t.nome",
                (user_id,),
            )
            return [{"team_id": str(i), "nome": n, "rotulo": n, "escalao": None, "epoca": None,
                     "academia_id": None, "n_jogadores": None, "ultima_sessao": None} for i, n in cur.fetchall()]


@router.get("/api/academia")
def estrutura(utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    if not acad.disponivel():
        return {"disponivel": False, "motivo": acad.MSG_MIGRACAO, "academias": [],
                "equipas": _equipas_simples(utilizador.user_id), "escaloes": acad.ESCALOES, "epoca_atual": acad.epoca_atual()}
    return acad.obter_estrutura(utilizador.user_id)


class NovaEquipa(BaseModel):
    escalao: str
    epoca: str
    copiar_de: str | None = None


@router.post("/api/academia/{academia_id}/equipas")
def nova_equipa(academia_id: str, body: NovaEquipa, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    if not acad.disponivel():
        raise HTTPException(status.HTTP_409_CONFLICT, acad.MSG_MIGRACAO)
    try:
        return acad.criar_equipa(utilizador.user_id, academia_id, body.escalao, body.epoca, body.copiar_de)
    except PermissionError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e))
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


class EditarEquipa(BaseModel):
    escalao: str | None = None
    epoca: str | None = None


@router.patch("/api/academia/equipas/{team_id}")
def editar_equipa(team_id: str, body: EditarEquipa, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    if not acad.disponivel():
        raise HTTPException(status.HTTP_409_CONFLICT, acad.MSG_MIGRACAO)
    try:
        return acad.atualizar_equipa(utilizador.user_id, team_id, body.escalao, body.epoca)
    except PermissionError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e))
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
