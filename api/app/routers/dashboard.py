"""
Dashboard API Routes

Alimenta o dashboard:
- estado do plantel (normal / atenção / atenção alta);
- avisos por jogador com explicação (ACWR, Vmax, exposição HSR/Sprint);
- exposição HSR/Sprint da semana vs jogo.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import UtilizadorAtual, verify_team_membership
from app.services.alertas_service import construir_avisos_dashboard, obter_exposicao_semana
from app.services.dados_equipa import carregar_df_equipa
from app.services.limites_service import obter_limites

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/teams", tags=["dashboard"])


def _build_alerts(team_id: str, limites: dict | None = None) -> list[dict]:
    df = carregar_df_equipa(team_id)
    if df.empty:
        return []
    return construir_avisos_dashboard(df, limites)


@router.get("/{team_id}/dashboard/squad-status")
async def get_squad_status(
    team_id: str,
    utilizador: UtilizadorAtual = Depends(verify_team_membership),
):
    """Get squad status summary: count of players by alert status."""
    try:
        alerts = _build_alerts(team_id, obter_limites(utilizador.user_id))
        summary = {
            "normal": 0,
            "attention": 0,
            "highAttention": 0,
            "total": len(alerts),
        }
        for alert in alerts:
            if alert["status"] == "normal":
                summary["normal"] += 1
            elif alert["status"] == "attention":
                summary["attention"] += 1
            else:
                summary["highAttention"] += 1
        return summary
    except Exception as e:
        logger.error(f"Error getting squad status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_id}/dashboard/exposicao-semana")
async def get_exposicao_semana(
    team_id: str,
    utilizador: UtilizadorAtual = Depends(verify_team_membership),
):
    """Exposição HSR/Sprint da semana (carga acumulada ÷ jogo mais exigente),
    sempre visível no dashboard — mesmo dentro da zona de referência."""
    try:
        df = carregar_df_equipa(team_id)
        return obter_exposicao_semana(df, obter_limites(utilizador.user_id))
    except Exception as e:
        logger.error(f"Error getting weekly exposure: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_id}/dashboard/attention-required")
async def get_attention_required(
    team_id: str,
    utilizador: UtilizadorAtual = Depends(verify_team_membership),
):
    """Get list of players requiring attention, sorted by severity."""
    try:
        return [alert for alert in _build_alerts(team_id, obter_limites(utilizador.user_id)) if alert["status"] != "normal"]
    except Exception as e:
        logger.error(f"Error getting attention required: {e}")
        raise HTTPException(status_code=500, detail=str(e))
