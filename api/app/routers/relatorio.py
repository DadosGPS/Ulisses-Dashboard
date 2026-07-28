from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel

from app.core.db import verificar_pertenca_equipa
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services.relatorio_service import gerar_pdf_relatorio, obter_texto_narrativo

router = APIRouter()


class TextoRelatorio(BaseModel):
    texto: str


@router.get("/api/teams/{team_id}/relatorio/texto")
def relatorio_texto(team_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")

    return obter_texto_narrativo(team_id)


@router.post("/api/teams/{team_id}/relatorio/pdf")
def relatorio_pdf(
    team_id: str,
    corpo: TextoRelatorio,
    utilizador: UtilizadorAtual = Depends(obter_utilizador_atual),
):
    if not verificar_pertenca_equipa(utilizador.user_id, team_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não pertences a esta equipa.")

    pdf_bytes = gerar_pdf_relatorio(team_id, corpo.texto)
    if pdf_bytes is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Geração de PDF indisponível no servidor no momento.",
        )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="relatorio_dia.pdf"'},
    )
