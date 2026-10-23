"""Variação habitual: decidir se um valor está «fora do normal» medindo-o
contra a variação do próprio histórico (o mesmo jogador, ou a equipa, nas
sessões equivalentes), em vez de uma percentagem fixa igual para todos.

Com pelo menos MIN_N referências usa o z-score (desvios-padrão); com menos,
cai para a percentagem fixa e diz que a referência é fraca.
"""
from __future__ import annotations

import statistics

MIN_N = 3


def classificar(atual: float | None, referencias: list[float], limiar_z: float = 1.5,
                limiar_pct: float = 15.0) -> dict:
    """Estado de `atual` face às `referencias`.

    Devolve {estado: alto|baixo|normal|insuficiente, delta_pct, z, tipico_pct,
    n, metodo: variacao|percentagem|None}. `tipico_pct` = coeficiente de
    variação das referências (quanto costuma variar, em %)."""
    refs = [float(r) for r in referencias if r is not None]
    n = len(refs)
    out = {"estado": "insuficiente", "delta_pct": None, "z": None, "tipico_pct": None, "n": n, "metodo": None}
    if atual is None or n == 0:
        return out
    media = statistics.fmean(refs)
    if media == 0:
        return out
    delta = (float(atual) - media) / media * 100.0
    out["delta_pct"] = round(delta, 1)
    dp = statistics.pstdev(refs) if n >= 2 else 0.0
    if n >= MIN_N and dp > 0:
        z = (float(atual) - media) / dp
        out.update(z=round(z, 2), tipico_pct=round(dp / media * 100.0, 1), metodo="variacao")
        out["estado"] = "alto" if z >= limiar_z else "baixo" if z <= -limiar_z else "normal"
        return out
    if n < 2:
        return out
    out["metodo"] = "percentagem"
    out["estado"] = "alto" if delta >= limiar_pct else "baixo" if delta <= -limiar_pct else "normal"
    return out
