"""Macrociclo: a época inteira de uma equipa numa só vista.

Junta os microciclos (fase, perfil, fator semanal), os jogos (planeados no
calendário e realizados no GPS / na folha de jogos) e, semana a semana, a carga
de treino planeada vs realizada por jogador, com a carga interna e a variação
face à semana anterior.
"""
from __future__ import annotations

import json
from datetime import date

import pandas as pd

from app.core.db import get_conn
from app.services.dados_equipa import carregar_df_equipa
from app.services.microciclos_service import (
    FATORES, _COLS, _linha, alvos_semanais, referencia_equipa,
)

PICO_VARIACAO_PCT = 30.0  # subida semanal da carga interna a assinalar (regra dos ~10–30 %)


# ── Cálculos puros ───────────────────────────────────────────────────────────
def fases_continuas(mcs: list[dict]) -> list[dict]:
    """Microciclos seguidos com a mesma fase → um intervalo por fase."""
    out: list[dict] = []
    for m in sorted(mcs, key=lambda x: x["data_inicio"]):
        f = m.get("fase")
        if not f:
            continue
        if out and out[-1]["fase"] == f:
            out[-1]["fim"] = m["data_fim"]
            out[-1]["microciclos"] += 1
        else:
            out.append({"fase": f, "inicio": m["data_inicio"], "fim": m["data_fim"], "microciclos": 1})
    return out


def carga_semana(df: pd.DataFrame, inicio: date, fim: date) -> dict:
    """Carga da semana por jogador (média do plantel): treinos (sem jogos) por
    fator, carga interna total (treinos + jogos), n.º de sessões e de jogos."""
    from app.services.referencia_jogo import mascara_jogo

    out: dict = {"treino": {}, "carga_interna": None, "n_treinos": 0, "n_jogos": 0}
    if df is None or df.empty or "Data" not in df.columns:
        return out
    dias = df["Data"].dt.date
    sem = df[(dias >= inicio) & (dias <= fim)]
    if sem.empty:
        return out
    e_jogo = mascara_jogo(sem)
    treinos = sem[~e_jogo]
    out["n_treinos"] = int(treinos["Data"].dt.date.nunique())
    out["n_jogos"] = int(sem[e_jogo]["Data"].dt.date.nunique())
    for k, (col, _, _) in FATORES.items():
        if col in treinos.columns and treinos[col].notna().any():
            out["treino"][k] = round(float(treinos.dropna(subset=[col]).groupby("Jogador")[col].sum().mean()), 1)
    if "Carga Interna" in sem.columns and sem["Carga Interna"].notna().any():
        out["carga_interna"] = round(float(sem.dropna(subset=["Carga Interna"]).groupby("Jogador")["Carga Interna"].sum().mean()), 0)
    return out


def variacoes(semanas: list[dict]) -> None:
    """Acrescenta a cada semana a variação da carga interna face à anterior e
    assinala subidas acima de PICO_VARIACAO_PCT."""
    anterior = None
    for s in semanas:
        ci = s["real"].get("carga_interna")
        s["variacao_pct"] = None
        s["pico"] = False
        if ci is not None and anterior:
            s["variacao_pct"] = round((ci - anterior) / anterior * 100, 1)
            s["pico"] = s["variacao_pct"] > PICO_VARIACAO_PCT
        if ci is not None:
            anterior = ci


# ── Dados ────────────────────────────────────────────────────────────────────
def _jogos(cur, team_id: str, mcs: list[dict], df: pd.DataFrame) -> list[dict]:
    """Jogos da época: da folha de jogos (adversário, competição, resultado),
    os dias de jogo planeados no calendário e os jogos que só existem no GPS."""
    from app.services.referencia_jogo import mascara_jogo

    jogos: dict[str, dict] = {}
    try:
        cur.execute(
            """select data, adversario, competicao, golos_marcados, golos_sofridos from jogos
               where team_id = %s order by data""",
            (team_id,),
        )
        for d, adv, comp, gm, gs in cur.fetchall():
            jogos[d.isoformat()] = {"data": d.isoformat(), "adversario": adv, "competicao": comp,
                                    "resultado": f"{gm}–{gs}" if gm is not None and gs is not None else None, "origem": "jogos"}
    except Exception:
        cur.connection.rollback()  # tabela de jogos ainda não existe (migração 0015)
    for m in mcs:
        for k, v in (m.get("dias") or {}).items():
            if v.get("tipo") == "Jogo" and k not in jogos:
                jogos[k] = {"data": k, "adversario": (v.get("objetivo") or "").removeprefix("vs ").strip() or None,
                            "competicao": None, "resultado": None, "origem": "plano"}
    if df is not None and not df.empty and "Data" in df.columns:
        for d in sorted(set(df[mascara_jogo(df)]["Data"].dt.date)):
            jogos.setdefault(d.isoformat(), {"data": d.isoformat(), "adversario": None, "competicao": None,
                                             "resultado": None, "origem": "gps"})
    return [jogos[k] for k in sorted(jogos)]


def obter_epoca(team_id: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select epoca, coalesce(escalao || ' · ' || epoca, nome) from teams where id = %s", (team_id,))
            epoca, rotulo = cur.fetchone() or (None, None)
            cur.execute(f"select {_COLS} from microciclos where team_id = %s order by data_inicio", (team_id,))
            mcs = [_linha(r) for r in cur.fetchall()]
            df = carregar_df_equipa(team_id)
            jogos = _jogos(cur, team_id, mcs, df)
    ref = referencia_equipa(df)
    hoje = date.today()
    semanas = []
    for m in mcs:
        ini, fim = date.fromisoformat(m["data_inicio"]), date.fromisoformat(m["data_fim"])
        fatores = m.get("fatores") or {}
        if isinstance(fatores, str):
            fatores = json.loads(fatores)
        semanas.append({
            "id": m["id"], "numero": m["numero"], "nome": m.get("nome"), "perfil": m.get("perfil"),
            "fase": m.get("fase"), "tipo": m.get("tipo"), "inicio": m["data_inicio"], "fim": m["data_fim"],
            "estado": "futuro" if ini > hoje else ("atual" if fim >= hoje else "passado"),
            "fatores": fatores,
            "planeado": alvos_semanais(fatores, ref) if ref else {},
            "real": carga_semana(df, ini, fim),
            "jogos": [j for j in jogos if m["data_inicio"] <= j["data"] <= m["data_fim"]],
        })
    variacoes(semanas)
    datas = [s["inicio"] for s in semanas] + [s["fim"] for s in semanas] + [j["data"] for j in jogos]
    return {
        "team_id": team_id, "rotulo": rotulo, "epoca": epoca,
        "inicio": min(datas) if datas else None, "fim": max(datas) if datas else None, "hoje": hoje.isoformat(),
        "referencia": ref,
        "fatores": [{"chave": k, "label": l, "unidade": u} for k, (_, l, u) in FATORES.items()],
        "fases": fases_continuas(mcs),
        "semanas": semanas,
        "jogos": jogos,
        "pico_variacao_pct": PICO_VARIACAO_PCT,
    }
