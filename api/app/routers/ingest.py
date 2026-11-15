import json

from starlette.concurrency import run_in_threadpool
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.importacao_service import analisar_ficheiro
from app.services.ingest_service import (
    guardar_mapa_lembrado, nomes_jogadores, obter_mapa_lembrado, processar_upload, processar_upload_com_mapa,
)
from app.services import verificacao_service

router = APIRouter()

TIPOS_ACEITES = {".csv", ".xlsx", ".xls"}


def _validar(file: UploadFile, utilizador: UtilizadorAtual, team_id: str) -> None:
    if not file.filename or not any(file.filename.lower().endswith(ext) for ext in TIPOS_ACEITES):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Usa um ficheiro CSV ou Excel (.xlsx/.csv).")
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")


@router.post("/api/ingest")
async def ingest(
    team_id: str = Form(...),
    file: UploadFile = File(...),
    substituir: bool = Form(True),
    excluir_erros: bool = Form(False),
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    await run_in_threadpool(_validar, file, utilizador, team_id)

    conteudo = await file.read()
    # Processamento pesado (pandas + BD) fora do event loop: não bloqueia os outros utilizadores.
    resultado = await run_in_threadpool(
        processar_upload,
        team_id=team_id,
        uploaded_by=utilizador.user_id,
        filename=file.filename,
        conteudo=conteudo,
        substituir=substituir,
        excluir_erros=excluir_erros,
    )

    if resultado["status"] in ("error", "bloqueado"):
        return _erro(resultado)

    return resultado


def _erro(resultado: dict) -> JSONResponse:
    """400 (erro de leitura/gravação) ou 422 (bloqueado pela verificação de
    dados) — com `detail` (mensagem) e, quando existe, a verificação completa."""
    codigo = 422 if resultado["status"] == "bloqueado" else 400
    corpo = {"detail": resultado["error"]}
    if resultado.get("verificacao"):
        corpo["verificacao"] = resultado["verificacao"]
    return JSONResponse(corpo, status_code=codigo)


@router.post("/api/ingest/analisar")
async def ingest_analisar(
    team_id: str = Form(...),
    file: UploadFile = File(...),
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    """Passo 1 da importação robusta: lê o ficheiro e devolve o diagnóstico
    (colunas detetadas, mapeamento sugerido, avisos, pré-visualização) SEM
    gravar nada. O frontend mostra isto, deixa ajustar, e só depois confirma."""
    await run_in_threadpool(_validar, file, utilizador, team_id)
    conteudo = await file.read()
    lembrado = await run_in_threadpool(obter_mapa_lembrado, team_id)
    existentes = await run_in_threadpool(nomes_jogadores, team_id)
    resultado = await run_in_threadpool(analisar_ficheiro, file.filename, conteudo, lembrado, existentes)
    if not resultado.get("ok"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, resultado.get("erro", "Ficheiro inválido."))
    return resultado


@router.post("/api/ingest/confirmar")
async def ingest_confirmar(
    team_id: str = Form(...),
    file: UploadFile = File(...),
    mapa: str = Form(...),
    substituir: bool = Form(False),
    excluir_erros: bool = Form(False),
    ignoradas: str = Form("[]"),
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    """Passo 2 da importação robusta: grava usando o mapeamento confirmado
    pelo utilizador (JSON {coluna_crua: nome_canónico}). O ficheiro é
    reenviado — a API não guarda estado entre pedidos.

    Por defeito JUNTA aos dados da equipa (as sessões do ficheiro substituem
    só as mesmas sessões); `substituir` apaga primeiro tudo o que a equipa tem.
    O mapeamento fica guardado para a próxima importação."""
    await run_in_threadpool(_validar, file, utilizador, team_id)
    try:
        mapa_dict = json.loads(mapa) if mapa else {}
        if not isinstance(mapa_dict, dict):
            raise ValueError
    except (ValueError, json.JSONDecodeError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mapeamento de colunas inválido.")

    conteudo = await file.read()
    resultado = await run_in_threadpool(
        processar_upload_com_mapa,
        team_id=team_id,
        uploaded_by=utilizador.user_id,
        filename=file.filename,
        conteudo=conteudo,
        mapa=mapa_dict,
        substituir=substituir,
        excluir_erros=excluir_erros,
    )

    if resultado["status"] in ("error", "bloqueado"):
        return _erro(resultado)

    try:
        lista_ign = [str(x) for x in json.loads(ignoradas or "[]")][:200]
    except (ValueError, TypeError):
        lista_ign = []
    await run_in_threadpool(guardar_mapa_lembrado, team_id, mapa_dict, lista_ign)
    return resultado


@router.get("/api/teams/{team_id}/verificacao-dados")
def verificacao_dados(team_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    """Histórico das verificações das importações + verificação dos dados já
    guardados da equipa (as mesmas regras, sobre o que está na base de dados)."""
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")
    return verificacao_service.obter(team_id)
