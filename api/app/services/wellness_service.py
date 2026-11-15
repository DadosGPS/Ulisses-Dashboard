"""Captura de wellness (questionário diário) → gps_sessions.

O questionário guarda cinco itens (sono, dor muscular, stress, humor e
fadiga), cada um de 1 (mau) a 5 (ótimo), e o Hooper Index derivado dos quatro
originais (a fadiga fica fora da soma para não mudar a escala nem o histórico;
entra na regra por item — ver itens_abaixo_do_normal) — a MESMA fórmula de utils/dados.py: soma de (5 − sub-score), por isso
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


def _validar(nome: str, v) -> int:
    """Sub-score obrigatório, inteiro de 1 a 5. Antes, uma resposta em falta ou
    inválida passava silenciosamente a 3 — um questionário incompleto parecia
    um dia médio. Agora é recusado e o jogador/staff vê o erro."""
    try:
        n = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"«{nome}» em falta ou inválido (1 a 5).")
    if n != int(n) or not 1 <= n <= 5:
        raise ValueError(f"«{nome}» tem de ser um inteiro de 1 a 5.")
    return int(n)


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
    fadiga=None,
) -> dict:
    valores = {k: _validar(k, v) for k, v in zip(_SUBSCORES, (sono, dor_musc, stress, humor))}
    hooper = calcular_hooper(**valores)
    # Fadiga: opcional na API (formulários antigos não a enviam), 1–5 quando vem.
    valores["fadiga"] = _validar("fadiga", fadiga) if fadiga is not None and fadiga != "" else None
    extra = {"wellness_notas": notas.strip()} if (notas and notas.strip()) else {}

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into gps_sessions
                    (team_id, player_id, data, tipo, sono, dor_musc, stress, humor, fadiga, hooper_index, extra_metrics)
                values (%s, %s, %s, 'Treino', %s, %s, %s, %s, %s, %s, %s::jsonb)
                on conflict (team_id, player_id, data, tipo) do update set
                    sono = excluded.sono,
                    dor_musc = excluded.dor_musc,
                    stress = excluded.stress,
                    humor = excluded.humor,
                    fadiga = coalesce(excluded.fadiga, gps_sessions.fadiga),
                    hooper_index = excluded.hooper_index,
                    extra_metrics = gps_sessions.extra_metrics || excluded.extra_metrics
                returning id
                """,
                (
                    team_id, player_id, data,
                    valores["sono"], valores["dor_musc"], valores["stress"], valores["humor"], valores["fadiga"],
                    hooper, json.dumps(extra),
                ),
            )
            linha = cur.fetchone()

    invalidar_cache_equipa(team_id)
    return {"status": "done", "id": str(linha[0]) if linha else None, "hooper_index": hooper}
