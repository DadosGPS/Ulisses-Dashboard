from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.ingest_service import processar_upload

router = APIRouter()

TIPOS_ACEITES = {".csv", ".xlsx", ".xls"}


@router.post("/api/ingest")
async def ingest(
    team_id: str = Form(...),
    file: UploadFile = File(...),
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    if not file.filename or not any(file.filename.lower().endswith(ext) for ext in TIPOS_ACEITES):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Usa um ficheiro CSV ou Excel (.xlsx/.csv).")

    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")

    conteudo = await file.read()
    resultado = processar_upload(
        team_id=team_id,
        uploaded_by=utilizador.user_id,
        filename=file.filename,
        conteudo=conteudo,
    )

    if resultado["status"] == "error":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, resultado["error"])

    return resultado
