"""Equipa técnica: membros, papéis e convites."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services import equipa_tecnica_service as et

router = APIRouter()


def _exec(fn, *args):
    if not et.disponivel():
        raise HTTPException(status.HTTP_409_CONFLICT, et.MSG_MIGRACAO)
    try:
        return fn(*args)
    except PermissionError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e))
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.get("/api/academia/equipa-tecnica")
def equipa_tecnica(utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    if not et.disponivel():
        return {"disponivel": False, "motivo": et.MSG_MIGRACAO}
    return _exec(et.listar, utilizador.user_id)


class ConviteBody(BaseModel):
    papel: str
    team_ids: list[str] = []
    email: str | None = None
    nome: str | None = None


@router.post("/api/academia/convites")
def novo_convite(body: ConviteBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    return _exec(et.criar_convite, utilizador.user_id, body.papel, body.team_ids, body.email, body.nome)


@router.delete("/api/academia/convites/{convite_id}")
def cancelar_convite(convite_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    return _exec(et.revogar_convite, utilizador.user_id, convite_id)


class MembroBody(BaseModel):
    papel: str
    team_ids: list[str] = []


@router.patch("/api/academia/membros/{alvo_id}")
def alterar_membro(alvo_id: str, body: MembroBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    return _exec(et.alterar_membro, utilizador.user_id, alvo_id, body.papel, body.team_ids)


@router.delete("/api/academia/membros/{alvo_id}")
def remover_membro(alvo_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    return _exec(et.remover_membro, utilizador.user_id, alvo_id)


@router.get("/api/convites/{token}")
def ver_convite(token: str):
    """PÚBLICO: quem abre o link vê de que academia/equipas é o convite."""
    return _exec(et.obter_convite_publico, token)


@router.post("/api/convites/{token}/aceitar")
def aceitar(token: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    from app.services.dados_equipa import invalidar_cache_equipa
    r = _exec(et.aceitar_convite, utilizador.user_id, utilizador.email, token)
    invalidar_cache_equipa(None)
    return r
