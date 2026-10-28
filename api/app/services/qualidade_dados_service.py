"""Qualidade dos dados por equipa — para o responsável da academia saber em
que números pode confiar antes de comparar equipas.

Por equipa e por mês, sobre os «jogador-dias» em que o jogador participou numa
sessão (tem GPS ou PSE nesse dia):
  • % com wellness (Hooper) registado;
  • % com PSE registada;
  • % com GPS (distância) importado.
Um mês com 40 % de wellness não suporta decisões de prontidão, por muito
bonitos que sejam os gráficos.
"""
from __future__ import annotations

import pandas as pd

from app.core.db import get_conn

MESES_POR_OMISSAO = 3
BOM_PCT = 80.0   # ≥ 80 % → dados fiáveis para decidir
FRACO_PCT = 60.0  # < 60 % → não decidir com base nisto


def nivel(pct: float | None) -> str | None:
    if pct is None:
        return None
    return "bom" if pct >= BOM_PCT else "fraco" if pct < FRACO_PCT else "medio"


def calcular(linhas: pd.DataFrame) -> list[dict]:
    """`linhas`: team_id, player_id, data, tem_gps, tem_pse, tem_wellness
    (uma por jogador e dia). Devolve, por equipa, os meses do mais recente
    para o mais antigo."""
    if linhas is None or linhas.empty:
        return []
    d = linhas.copy()
    d["data"] = pd.to_datetime(d["data"])
    d = d[d["tem_gps"] | d["tem_pse"]]  # o jogador participou nesse dia
    if d.empty:
        return []
    d["mes"] = d["data"].dt.strftime("%Y-%m")
    out = []
    for team_id, g in d.groupby("team_id"):
        meses = []
        for mes, m in sorted(g.groupby("mes"), key=lambda x: x[0], reverse=True):
            n = int(len(m))
            pct = {k: round(float(m[f"tem_{k}"].mean()) * 100, 0) for k in ("wellness", "pse", "gps")}
            meses.append({"mes": mes, "jogador_dias": n, "dias_sessao": int(m["data"].nunique()),
                          **{f"{k}_pct": v for k, v in pct.items()},
                          **{f"{k}_nivel": nivel(v) for k, v in pct.items()}})
        out.append({"team_id": str(team_id), "meses": meses})
    return out


def obter(academia_id: str, user_id: str, meses: int = MESES_POR_OMISSAO) -> dict:
    meses = max(1, min(12, int(meses or MESES_POR_OMISSAO)))
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select papel from academia_membros where academia_id = %s and user_id = %s", (academia_id, user_id))
            if not cur.fetchone():
                raise PermissionError("Não pertences a esta academia.")
            cur.execute(
                """
                select t.id, t.nome, t.escalao, t.epoca from teams t where t.academia_id = %s
                """,
                (academia_id,),
            )
            equipas = {str(i): {"nome": n, "escalao": e, "epoca": ep} for i, n, e, ep in cur.fetchall()}
            cur.execute(
                """
                select gs.team_id, gs.player_id, gs.data,
                       bool_or(gs.distancia_total_m is not null) as tem_gps,
                       bool_or(gs.pse_sessao is not null) as tem_pse,
                       bool_or(gs.hooper_index is not null) as tem_wellness
                from gps_sessions gs
                join teams t on t.id = gs.team_id
                join players p on p.id = gs.player_id and p.ativo
                where t.academia_id = %s and gs.data >= (date_trunc('month', current_date) - (%s || ' months')::interval)
                group by gs.team_id, gs.player_id, gs.data
                """,
                (academia_id, meses - 1),
            )
            linhas = pd.DataFrame(cur.fetchall(), columns=["team_id", "player_id", "data", "tem_gps", "tem_pse", "tem_wellness"])
    por_equipa = calcular(linhas)
    for e in por_equipa:
        e.update(equipas.get(e["team_id"], {}))
    ordem = {"Sub-13": 0, "Sub-14": 1, "Sub-15": 2, "Sub-16": 3, "Sub-17": 4, "Sub-19": 5}
    por_equipa.sort(key=lambda e: (-(int(e["epoca"][:4]) if e.get("epoca") else 0), ordem.get(e.get("escalao") or "", 99), e.get("nome") or ""))
    return {"meses": meses, "limites": {"bom": BOM_PCT, "fraco": FRACO_PCT}, "equipas": por_equipa}
