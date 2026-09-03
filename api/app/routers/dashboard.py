"""
Dashboard API Routes — Redesigned Product Architecture

Provides aggregate data for the new 5-section product:
- Squad status summary (normal, attention, high attention)
- Player alerts with explanations
- What changed comparisons (week-over-week)
- Today's session summary if exists
- Quick statistics for dashboard cards
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from app.core.security import UtilizadorAtual, verify_team_membership
from app.services.alertas_service import build_alerts_for_team
from app.services.dados_equipa import carregar_df_equipa
from app.services.estado_service import listar_estados
from app.services.limites_service import obter_limites

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/teams", tags=["dashboard"])


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _state_lookup(team_id: str) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for estado in listar_estados(team_id):
        lookup[str(estado["player_id"])] = estado
    return lookup


def _build_alerts(team_id: str, limites: dict | None = None) -> list[dict]:
    df = carregar_df_equipa(team_id).copy()
    if df.empty:
        return []

    if "player_id" not in df.columns or "Data" not in df.columns:
        return []

    df = df.copy()
    df["player_id"] = df["player_id"].astype(str)
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df = df.dropna(subset=["Data"]).sort_values(["player_id", "Data"]).reset_index(drop=True)

    return build_alerts_for_team(df.to_dict(orient="records"), _state_lookup(team_id), limites)


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


@router.get("/{team_id}/dashboard/what-changed")
async def get_what_changed(
    team_id: str,
    _=Depends(verify_team_membership),
):
    """Get team-wide changes comparing the last 7 days with the previous 7 days."""
    try:
        df = carregar_df_equipa(team_id).copy()
        if df.empty:
            return []

        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
        df = df.dropna(subset=["Data"]).sort_values("Data")

        metrics = [
            ("Distância Total", "Distância Total (m)"),
            ("HSR", "HSR (m)"),
            ("Sprint", "Sprint (m)"),
        ]

        changes: list[dict] = []
        for label, column in metrics:
            if column not in df.columns:
                continue
            grouped = df.groupby("Data")[column].sum().sort_index()
            if len(grouped) < 2:
                continue
            current = float(grouped.tail(7).sum()) if len(grouped) >= 7 else float(grouped.iloc[-1])
            previous = float(grouped.iloc[-14:-7].sum()) if len(grouped) >= 14 else float(grouped.iloc[0])
            delta = ((current - previous) / previous * 100.0) if previous else 0.0
            changes.append({
                "metric": label,
                "previous": int(previous),
                "current": int(current),
                "change_percent": round(delta, 1),
                "direction": "up" if delta >= 0 else "down",
            })

        return changes[:3]
    except Exception as e:
        logger.error(f"Error getting what changed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_id}/dashboard/today-session")
async def get_today_session(
    team_id: str,
    _=Depends(verify_team_membership),
):
    """Get today's session summary if it exists."""
    try:
        df = carregar_df_equipa(team_id).copy()
        if df.empty:
            return {"exists": False}

        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
        today = pd.Timestamp.now(tz=None).normalize()
        session_df = df[df["Data"] == today]

        if session_df.empty:
            return {"exists": False}

        team_load = {
            "total_distance": int(float(session_df["Distância Total (m)"].sum())) if "Distância Total (m)" in session_df.columns else 0,
            "hsr": int(float(session_df["HSR (m)"].sum())) if "HSR (m)" in session_df.columns else 0,
            "sprint": int(float(session_df["Sprint (m)"].sum())) if "Sprint (m)" in session_df.columns else 0,
            "accelerations": int(float(session_df["Acc (n)"].sum())) if "Acc (n)" in session_df.columns else 0,
            "decelerations": int(float(session_df["Dcc (n)"].sum())) if "Dcc (n)" in session_df.columns else 0,
            "sRPE": int(float(session_df["PSE Sessão"].sum())) if "PSE Sessão" in session_df.columns else 0,
        }

        return {
            "exists": True,
            "session_id": str(session_df.iloc[0].get("id", "")),
            "date": today.strftime("%Y-%m-%d"),
            "type": str(session_df.iloc[0].get("Tipo", "Treino")),
            "match_day": str(session_df.iloc[0].get("Dia MD", "MD")),
            "duration_minutes": int(float(session_df["Duração (min)"].sum())) if "Duração (min)" in session_df.columns else 0,
            "participants": int(session_df["Jogador"].nunique()),
            "team_load": team_load,
        }
    except Exception as e:
        logger.error(f"Error getting today's session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_id}/dashboard/quick-stats")
async def get_quick_stats(
    team_id: str,
    _=Depends(verify_team_membership),
):
    """Get quick statistics for dashboard cards."""
    try:
        df = carregar_df_equipa(team_id).copy()
        if df.empty:
            return {
                "squad_size": 0,
                "sessions_this_week": 0,
                "average_weekly_load": 0,
                "data_freshness": "Sem dados",
            }

        team_players = df["player_id"].nunique() if "player_id" in df.columns else 0
        sessions_this_week = int(df[df["Data"] >= pd.Timestamp.now().normalize() - pd.Timedelta(days=7)]["Data"].nunique())
        load_total = float(df.get("Carga Interna", pd.Series([0.0] * len(df))).sum()) if "Carga Interna" in df.columns else 0.0

        return {
            "squad_size": int(team_players),
            "sessions_this_week": sessions_this_week,
            "average_weekly_load": int(load_total / 7) if sessions_this_week else 0,
            "data_freshness": "Atualizado",
        }
    except Exception as e:
        logger.error(f"Error getting quick stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
