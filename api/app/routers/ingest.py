import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.importacao_service import analisar_ficheiro
from app.services.ingest_service import processar_upload, processar_upload_com_mapa

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
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    _validar(file, utilizador, team_id)

    conteudo = await file.read()
    resultado = processar_upload(
        team_id=team_id,
        uploaded_by=utilizador.user_id,
        filename=file.filename,
        conteudo=conteudo,
        substituir=substituir,
    )

    if resultado["status"] == "error":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, resultado["error"])

    return resultado


@router.post("/api/ingest/analisar")
async def ingest_analisar(
    team_id: str = Form(...),
    file: UploadFile = File(...),
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    """Passo 1 da importação robusta: lê o ficheiro e devolve o diagnóstico
    (colunas detetadas, mapeamento sugerido, avisos, pré-visualização) SEM
    gravar nada. O frontend mostra isto, deixa ajustar, e só depois confirma."""
    _validar(file, utilizador, team_id)
    conteudo = await file.read()
    resultado = analisar_ficheiro(file.filename, conteudo)
    if not resultado.get("ok"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, resultado.get("erro", "Ficheiro inválido."))
    return resultado


@router.post("/api/ingest/confirmar")
async def ingest_confirmar(
    team_id: str = Form(...),
    file: UploadFile = File(...),
    mapa: str = Form(...),
    substituir: bool = Form(True),
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    """Passo 2 da importação robusta: grava usando o mapeamento confirmado
    pelo utilizador (JSON {coluna_crua: nome_canónico}). O ficheiro é
    reenviado — a API não guarda estado entre pedidos."""
    _validar(file, utilizador, team_id)
    try:
        mapa_dict = json.loads(mapa) if mapa else {}
        if not isinstance(mapa_dict, dict):
            raise ValueError
    except (ValueError, json.JSONDecodeError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mapeamento de colunas inválido.")

    conteudo = await file.read()
    resultado = processar_upload_com_mapa(
        team_id=team_id,
        uploaded_by=utilizador.user_id,
        filename=file.filename,
        conteudo=conteudo,
        mapa=mapa_dict,
        substituir=substituir,
    )

    if resultado["status"] == "error":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, resultado["error"])

    return resultado
