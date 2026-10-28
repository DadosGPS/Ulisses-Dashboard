"""Força e ginásio — prescrição, registo e progressão.

Uma sessão de ginásio tem uma prescrição (exercício, séries, repetições,
carga) que é copiada para cada jogador escolhido; depois regista-se o que
cada um fez e a PSE da sessão. A PSE × duração entra em gps_sessions como uma
sessão de tipo «Ginásio» no mesmo dia (com o Dia MD e o microciclo da equipa
nesse dia), para a carga do ginásio contar na carga interna, no ACWR e na
monotonia — antes ficava fora de tudo.

Medidas:
  • tonelagem = séries × repetições × carga (kg) — volume-carga da sessão;
  • 1RM estimado (Epley: carga × (1 + reps/30)), só com ≤ 12 repetições,
    para seguir a progressão de força sem testar 1RM em jovens.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import pandas as pd

from app.core.db import get_conn
from app.services.dados_equipa import invalidar_cache_equipa

TIPO_GINASIO = "Ginásio"
MAX_REPS_E1RM = 12
MSG_MIGRACAO = (
    "O módulo de força precisa da migração supabase/migrations/0023_forca.sql "
    "(aplica-se sozinha no próximo deploy, ou no SQL Editor do Supabase)."
)


# ── Cálculos puros ───────────────────────────────────────────────────────────
def tonelagem(series, repeticoes, carga_kg) -> float:
    try:
        return float(series or 0) * float(repeticoes or 0) * float(carga_kg or 0)
    except (TypeError, ValueError):
        return 0.0


def e1rm(carga_kg, repeticoes) -> float | None:
    """1RM estimado (Epley). Sem carga ou com mais de 12 repetições → None."""
    try:
        c, r = float(carga_kg), int(repeticoes)
    except (TypeError, ValueError):
        return None
    if c <= 0 or r < 1 or r > MAX_REPS_E1RM:
        return None
    return round(c * (1 + r / 30), 1) if r > 1 else round(c, 1)


def limpar_linhas(linhas: list[dict] | None) -> list[dict]:
    """Valida a prescrição / o registo: exercício obrigatório, números nos
    intervalos da base de dados."""
    out = []
    for i, l in enumerate(linhas or []):
        ex = str(l.get("exercicio") or "").strip()[:80]
        if not ex:
            continue

        def num(k, lo, hi, inteiro=True):
            v = l.get(k)
            if v in (None, ""):
                return None
            try:
                n = float(v)
            except (TypeError, ValueError):
                raise ValueError(f"«{k}» inválido em {ex}.")
            if not lo <= n <= hi:
                raise ValueError(f"«{k}» de {ex} tem de estar entre {lo} e {hi}.")
            return int(round(n)) if inteiro else round(n, 1)

        out.append({"ordem": i, "exercicio": ex, "series": num("series", 1, 20), "repeticoes": num("repeticoes", 1, 100),
                    "carga_kg": num("carga_kg", 0, 500, inteiro=False), "feito": bool(l.get("feito", True))})
    return out


def progressao(registos: pd.DataFrame, hoje: date, semanas: int = 8) -> dict:
    """`registos`: data, exercicio, series, repeticoes, carga_kg, feito.
    Devolve a tonelagem por semana (segunda-feira) das últimas `semanas` e o
    melhor 1RM estimado por exercício em cada sessão."""
    vazio = {"semanas": [], "exercicios": []}
    if registos is None or registos.empty:
        return vazio
    r = registos[registos["feito"].astype(bool)].copy()
    if r.empty:
        return vazio
    r["data"] = pd.to_datetime(r["data"])
    r["ton"] = [tonelagem(s, rp, c) for s, rp, c in zip(r["series"], r["repeticoes"], r["carga_kg"])]
    r["e1rm"] = [e1rm(c, rp) for c, rp in zip(r["carga_kg"], r["repeticoes"])]
    inicio = pd.Timestamp(hoje) - pd.Timedelta(weeks=semanas)
    rec = r[r["data"] >= inicio]
    rec = rec.assign(semana=(rec["data"] - pd.to_timedelta(rec["data"].dt.weekday, unit="D")).dt.strftime("%Y-%m-%d"))
    por_semana = rec.groupby("semana").agg(tonelagem=("ton", "sum"), sessoes=("data", "nunique")).reset_index()
    sem = [{"semana": s, "tonelagem": round(float(t), 0), "sessoes": int(n)}
           for s, t, n in zip(por_semana["semana"], por_semana["tonelagem"], por_semana["sessoes"])]
    exercicios = []
    for ex, g in r.dropna(subset=["e1rm"]).groupby("exercicio"):
        pontos = g.groupby("data")["e1rm"].max().sort_index()
        serie = [{"data": d.strftime("%Y-%m-%d"), "e1rm": round(float(v), 1)} for d, v in pontos.items()]
        primeiro, ultimo = serie[0]["e1rm"], serie[-1]["e1rm"]
        exercicios.append({"exercicio": ex, "serie": serie, "atual": ultimo,
                           "variacao_pct": round((ultimo - primeiro) / primeiro * 100, 1) if primeiro and len(serie) > 1 else None})
    exercicios.sort(key=lambda e: -len(e["serie"]))
    return {"semanas": sem, "exercicios": exercicios}


# ── Base de dados ────────────────────────────────────────────────────────────
def disponivel() -> bool:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.forca_sessoes') is not null")
                return bool(cur.fetchone()[0])
    except Exception:
        return False


def _contexto_dia(cur, team_id: str, dia: date) -> tuple[str | None, int | None]:
    """Dia MD e microciclo da equipa nesse dia: das sessões de campo, senão do
    plano de microciclos."""
    cur.execute(
        """
        select dia_md, microciclo_nr from gps_sessions
        where team_id = %s and data = %s and tipo <> %s and (dia_md is not null or microciclo_nr is not null)
        group by dia_md, microciclo_nr order by count(*) desc limit 1
        """,
        (team_id, dia, TIPO_GINASIO),
    )
    row = cur.fetchone()
    if row:
        return row[0], row[1]
    try:
        cur.execute("select numero, dias from microciclos where team_id = %s and %s between data_inicio and data_fim limit 1", (team_id, dia))
        mc = cur.fetchone()
    except Exception:
        cur.connection.rollback()
        mc = None
    if not mc:
        return None, None
    dias = mc[1] if isinstance(mc[1], dict) else json.loads(mc[1] or "{}")
    plano = dias.get(dia.isoformat()) if isinstance(dias, dict) else None
    return (plano or {}).get("dia_md"), mc[0]


def _jogadores_da_equipa(cur, team_id: str, ids: list[str]) -> list[str]:
    if not ids:
        return []
    cur.execute("select id::text from players where team_id = %s and id::text = any(%s)", (team_id, list(ids)))
    return [r[0] for r in cur.fetchall()]


def listar_sessoes(team_id: str, desde: str | None = None) -> dict:
    if not disponivel():
        return {"disponivel": False, "motivo": MSG_MIGRACAO, "sessoes": []}
    inicio = date.fromisoformat(desde) if desde else date.today() - timedelta(days=60)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select s.id::text, s.data, s.nome, s.duracao_min,
                       count(distinct r.player_id),
                       coalesce(sum(case when r.feito then coalesce(r.series, 0) * coalesce(r.repeticoes, 0) * coalesce(r.carga_kg, 0) end), 0)
                from forca_sessoes s left join forca_registos r on r.sessao_id = s.id
                where s.team_id = %s and s.data >= %s
                group by s.id order by s.data desc, s.criado_em desc
                """,
                (team_id, inicio),
            )
            linhas = cur.fetchall()
    return {"disponivel": True, "motivo": None, "sessoes": [
        {"id": i, "data": d.isoformat(), "nome": n, "duracao_min": dur, "n_jogadores": int(nj), "tonelagem": round(float(t), 0)}
        for i, d, n, dur, nj, t in linhas]}


def criar_sessao(team_id: str, user_id: str | None, dia: str, nome: str, duracao_min: int | None,
                 prescricao: list[dict], jogadores: list[str], notas: str | None = None) -> dict:
    nome = (nome or "").strip()[:80]
    if not nome:
        raise ValueError("Dá um nome à sessão (ex.: Força — membros inferiores).")
    presc = limpar_linhas(prescricao)
    if not presc:
        raise ValueError("A sessão precisa de pelo menos um exercício.")
    d = date.fromisoformat(dia)
    with get_conn() as conn:
        with conn.cursor() as cur:
            validos = _jogadores_da_equipa(cur, team_id, jogadores)
            if not validos:
                raise ValueError("Escolhe pelo menos um jogador desta equipa.")
            cur.execute(
                """
                insert into forca_sessoes (team_id, data, nome, duracao_min, prescricao, notas, criado_por)
                values (%s, %s, %s, %s, %s::jsonb, %s, %s) returning id::text
                """,
                (team_id, d, nome, duracao_min, json.dumps(presc), (notas or "").strip()[:500] or None, user_id),
            )
            sid = cur.fetchone()[0]
            for pid in validos:
                for l in presc:
                    cur.execute(
                        """
                        insert into forca_registos (sessao_id, team_id, player_id, ordem, exercicio, series, repeticoes, carga_kg, feito)
                        values (%s, %s, %s, %s, %s, %s, %s, %s, true)
                        """,
                        (sid, team_id, pid, l["ordem"], l["exercicio"], l["series"], l["repeticoes"], l["carga_kg"]),
                    )
    return {"id": sid, "n_jogadores": len(validos)}


def obter_sessao(team_id: str, sessao_id: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select id::text, data, nome, duracao_min, prescricao, notas from forca_sessoes where id = %s and team_id = %s",
                        (sessao_id, team_id))
            s = cur.fetchone()
            if not s:
                raise LookupError("Sessão não encontrada.")
            cur.execute(
                """
                select r.player_id::text, p.nome, r.ordem, r.exercicio, r.series, r.repeticoes, r.carga_kg::float, r.feito
                from forca_registos r join players p on p.id = r.player_id
                where r.sessao_id = %s order by p.nome, r.ordem
                """,
                (sessao_id,),
            )
            regs = cur.fetchall()
            cur.execute(
                "select player_id::text, pse_sessao::float, duracao_min::float from gps_sessions where team_id = %s and data = %s and tipo = %s",
                (team_id, s[1], TIPO_GINASIO),
            )
            pse = {pid: {"pse": p, "duracao_min": dur} for pid, p, dur in cur.fetchall()}
    jogadores: dict[str, dict] = {}
    for pid, nome, ordem, ex, se, rp, c, feito in regs:
        j = jogadores.setdefault(pid, {"player_id": pid, "nome": nome, "linhas": [], "tonelagem": 0.0, **pse.get(pid, {"pse": None, "duracao_min": None})})
        j["linhas"].append({"ordem": ordem, "exercicio": ex, "series": se, "repeticoes": rp, "carga_kg": c, "feito": feito,
                            "e1rm": e1rm(c, rp)})
        if feito:
            j["tonelagem"] += tonelagem(se, rp, c)
    for j in jogadores.values():
        j["tonelagem"] = round(j["tonelagem"], 0)
    presc = s[4] if isinstance(s[4], list) else json.loads(s[4] or "[]")
    return {"id": s[0], "data": s[1].isoformat(), "nome": s[2], "duracao_min": s[3], "prescricao": presc, "notas": s[5],
            "jogadores": sorted(jogadores.values(), key=lambda j: j["nome"])}


def guardar_jogador(team_id: str, sessao_id: str, player_id: str, linhas: list[dict],
                    pse: float | None, duracao_min: float | None) -> dict:
    """Substitui o registo de um jogador numa sessão e grava a PSE como sessão
    «Ginásio» em gps_sessions (carga interna = PSE × duração)."""
    regs = limpar_linhas(linhas)
    if pse is not None and not 0 <= float(pse) <= 10:
        raise ValueError("A PSE vai de 0 a 10.")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select data, duracao_min from forca_sessoes where id = %s and team_id = %s", (sessao_id, team_id))
            s = cur.fetchone()
            if not s:
                raise LookupError("Sessão não encontrada.")
            if not _jogadores_da_equipa(cur, team_id, [player_id]):
                raise LookupError("Jogador não encontrado nesta equipa.")
            dia, dur_sessao = s
            cur.execute("delete from forca_registos where sessao_id = %s and player_id = %s", (sessao_id, player_id))
            for l in regs:
                cur.execute(
                    """
                    insert into forca_registos (sessao_id, team_id, player_id, ordem, exercicio, series, repeticoes, carga_kg, feito)
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (sessao_id, team_id, player_id, l["ordem"], l["exercicio"], l["series"], l["repeticoes"], l["carga_kg"], l["feito"]),
                )
            dur = float(duracao_min) if duracao_min else (float(dur_sessao) if dur_sessao else None)
            if pse is not None and dur:
                dia_md, mc = _contexto_dia(cur, team_id, dia)
                cur.execute(
                    """
                    insert into gps_sessions (team_id, player_id, data, tipo, dia_md, microciclo_nr, pse_sessao, duracao_min, carga_interna)
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (team_id, player_id, data, tipo) do update set
                        pse_sessao = excluded.pse_sessao, duracao_min = excluded.duracao_min,
                        carga_interna = excluded.carga_interna,
                        dia_md = coalesce(gps_sessions.dia_md, excluded.dia_md),
                        microciclo_nr = coalesce(gps_sessions.microciclo_nr, excluded.microciclo_nr)
                    """,
                    (team_id, player_id, dia, TIPO_GINASIO, dia_md, mc, float(pse), dur, float(pse) * dur),
                )
    invalidar_cache_equipa(team_id)
    return {"ok": True, "tonelagem": round(sum(tonelagem(l["series"], l["repeticoes"], l["carga_kg"]) for l in regs if l["feito"]), 0)}


def apagar_sessao(team_id: str, sessao_id: str) -> dict:
    """Apaga a sessão e, se for a única de ginásio nesse dia, a carga
    «Ginásio» que ela tinha posto em gps_sessions."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("delete from forca_sessoes where id = %s and team_id = %s returning data", (sessao_id, team_id))
            row = cur.fetchone()
            if not row:
                return {"removidas": 0}
            cur.execute("select exists (select 1 from forca_sessoes where team_id = %s and data = %s)", (team_id, row[0]))
            if not cur.fetchone()[0]:
                cur.execute("delete from gps_sessions where team_id = %s and data = %s and tipo = %s and distancia_total_m is null",
                            (team_id, row[0], TIPO_GINASIO))
    invalidar_cache_equipa(team_id)
    return {"removidas": 1}


def perfil_jogador(team_id: str, player_id: str) -> dict:
    if not disponivel():
        return {"disponivel": False, "motivo": MSG_MIGRACAO, "semanas": [], "exercicios": []}
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select s.data, r.exercicio, r.series, r.repeticoes, r.carga_kg::float, r.feito
                from forca_registos r join forca_sessoes s on s.id = r.sessao_id
                where r.team_id = %s and r.player_id = %s
                """,
                (team_id, player_id),
            )
            df = pd.DataFrame(cur.fetchall(), columns=["data", "exercicio", "series", "repeticoes", "carga_kg", "feito"])
    return {"disponivel": True, "motivo": None, **progressao(df, date.today())}
