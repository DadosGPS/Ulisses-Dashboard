"""Captura de wellness (questionário diário) → gps_sessions.

O questionário guarda os quatro sub-scores que o esquema já tem (sono, dor
muscular, stress, humor), cada um de 1 (mau) a 5 (ótimo), e o Hooper Index
derivado — a MESMA fórmula de utils/dados.py: soma de (5 − sub-score), por isso
um valor alto = pior bem-estar (é o que os alertas de wellness já leem).

Grava por upsert na sessão do dia (team_id, player_id, data, tipo='Treino'):
se já existe a sessão de treino desse dia, junta-lhe o wellness; caso
contrário, cria uma linha só com o wellness. Assim o dado entra logo no mesmo
DataFrame que alimenta a Análise e o dashboard.
"""
from __future__ import annotations

import json

from app.core.db import get_conn
from app.services.dados_equipa import invalidar_cache_equipa

_SUBSCORES = ("sono", "dor_musc", "stress", "humor")


def _clamp(v) -> int:
    """Garante um inteiro em [1, 5]."""
    try:
        n = int(round(float(v)))
    except (TypeError, ValueError):
        n = 3
    return max(1, min(5, n))


def calcular_hooper(sono, dor_musc, stress, humor) -> int:
    """Hooper Index = Σ (5 − sub-score), cada sub-score em [1, 5]. Intervalo
    0 (ótimo) … 16 (péssimo), igual à derivação de utils/dados.py."""
    return sum(5 - _clamp(v) for v in (sono, dor_musc, stress, humor))


def registar_wellness(
    team_id: str,
    player_id: str,
    data: str,
    sono,
    dor_musc,
    stress,
    humor,
    notas: str | None = None,
) -> dict:
    valores = {k: _clamp(v) for k, v in zip(_SUBSCORES, (sono, dor_musc, stress, humor))}
    hooper = calcular_hooper(**valores)
    extra = {"wellness_notas": notas.strip()} if (notas and notas.strip()) else {}

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into gps_sessions
                    (team_id, player_id, data, tipo, sono, dor_musc, stress, humor, hooper_index, extra_metrics)
                values (%s, %s, %s, 'Treino', %s, %s, %s, %s, %s, %s::jsonb)
                on conflict (team_id, player_id, data, tipo) do update set
                    sono = excluded.sono,
                    dor_musc = excluded.dor_musc,
                    stress = excluded.stress,
                    humor = excluded.humor,
                    hooper_index = excluded.hooper_index,
                    extra_metrics = gps_sessions.extra_metrics || excluded.extra_metrics
                returning id
                """,
                (
                    team_id, player_id, data,
                    valores["sono"], valores["dor_musc"], valores["stress"], valores["humor"],
                    hooper, json.dumps(extra),
                ),
            )
            linha = cur.fetchone()

    invalidar_cache_equipa(team_id)
    return {"status": "done", "id": str(linha[0]) if linha else None, "hooper_index": hooper}
