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
import json

from app.services.dados_equipa import calculo_em_cache, carregar_df_equipa
from app.services.limites_service import obter_limites_equipa
from app.services.planeado_realizado_service import obter_planeado_vs_realizado

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/teams", tags=["dashboard"])


def _build_alerts(team_id: str, limites: dict | None = None) -> list[dict]:
    # squad-status e attention-required pedem o mesmo cálculo na mesma página:
    # faz-se uma vez e reutiliza-se (por equipa e limites do utilizador).
    def calcular():
        df = carregar_df_equipa(team_id)
        if df.empty:
            return []
        from datetime import date

        import pandas as pd

        from app.services.estado_service import listar_estados
        from app.services.prontidao_service import _carregar_testes
        try:
            estados = {e["nome"]: e["estado"] for e in listar_estados(team_id)}
        except Exception:
            estados = {}
        from app.services.ficha_atleta_service import crescimento_da_equipa
        return construir_avisos_dashboard(df, limites, estados=estados, testes=_carregar_testes(team_id),
                                          hoje=pd.Timestamp(date.today()), crescimento=crescimento_da_equipa(team_id))
    return calculo_em_cache(team_id, "avisos:" + json.dumps(limites or {}, sort_keys=True, default=str), calcular)


@router.get("/{team_id}/dashboard/squad-status")
def get_squad_status(
    team_id: str,
    utilizador: UtilizadorAtual = Depends(verify_team_membership),
):
    """Get squad status summary: count of players by alert status."""
    try:
        alerts = _build_alerts(team_id, obter_limites_equipa(team_id, utilizador.user_id))
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
def get_exposicao_semana(
    team_id: str,
    microciclo: int | None = None,
    utilizador: UtilizadorAtual = Depends(verify_team_membership),
):
    """Exposição HSR/Sprint da semana (carga acumulada ÷ jogo mais exigente),
    sempre visível no dashboard — mesmo dentro da zona de referência."""
    try:
        df = carregar_df_equipa(team_id)
        return obter_exposicao_semana(df, obter_limites_equipa(team_id, utilizador.user_id), microciclo)
    except Exception as e:
        logger.error(f"Error getting weekly exposure: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_id}/dashboard/planeado-vs-realizado")
def get_planeado_vs_realizado(
    team_id: str,
    utilizador: UtilizadorAtual = Depends(verify_team_membership),
):
    """Sessão de treino mais recente: PSE e carga externa planeadas vs a média
    real da equipa, com o desvio em % e um estado (ok / atenção / fora)."""
    try:
        return obter_planeado_vs_realizado(team_id)
    except Exception as e:
        logger.error(f"Error getting planned vs actual: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_id}/dashboard/attention-required")
def get_attention_required(
    team_id: str,
    utilizador: UtilizadorAtual = Depends(verify_team_membership),
):
    """Get list of players requiring attention, sorted by severity."""
    try:
        return [alert for alert in _build_alerts(team_id, obter_limites_equipa(team_id, utilizador.user_id)) if alert["status"] != "normal"]
    except Exception as e:
        logger.error(f"Error getting attention required: {e}")
        raise HTTPException(status_code=500, detail=str(e))
