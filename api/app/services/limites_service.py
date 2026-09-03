"""Limiares de alerta configuráveis (guardados em profiles.settings.limites).

Os alertas do dashboard usam estes limiares; se o utilizador não tiver
definido nada, aplicam-se os valores por omissão (os mesmos que estavam
fixos no código). Cada métrica tem um limiar de "atenção" e outro de
"atenção alta".
"""
from __future__ import annotations

import json

from app.core.db import get_conn

DEFAULTS: dict[str, float] = {
    "acwr_alto": 1.3,
    "acwr_muito_alto": 1.5,
    "carga_change_alto": 30.0,
    "carga_change_muito_alto": 50.0,
    "wellness_change_alto": 10.0,
    "wellness_change_muito_alto": 20.0,
    "hsr_change_alto": 25.0,
    "hsr_change_muito_alto": 40.0,
    "velocidade_queda_alto": 8.0,
    "velocidade_queda_muito_alto": 12.0,
    "dados_horas": 48.0,
}


def _settings(user_id: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select settings from profiles where id = %s", (user_id,))
            row = cur.fetchone()
    if not row or not row[0]:
        return {}
    val = row[0]
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return {}
    return val if isinstance(val, dict) else {}


def obter_limites(user_id: str) -> dict:
    guardados = _settings(user_id).get("limites") or {}
    lim = dict(DEFAULTS)
    for k, v in guardados.items():
        if k in DEFAULTS:
            try:
                lim[k] = float(v)
            except (TypeError, ValueError):
                pass
    return lim


def guardar_limites(user_id: str, novos: dict) -> dict:
    lim = dict(DEFAULTS)
    for k, v in (novos or {}).items():
        if k in DEFAULTS:
            try:
                lim[k] = float(v)
            except (TypeError, ValueError):
                pass
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "update profiles set settings = jsonb_set(coalesce(settings, '{}'::jsonb), '{limites}', %s::jsonb) where id = %s returning 1",
                (json.dumps(lim), user_id),
            )
            ok = cur.fetchone()
    return lim if ok else lim
