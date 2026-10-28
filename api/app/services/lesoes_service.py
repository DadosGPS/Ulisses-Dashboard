"""Histórico de lesões — CRUD + agregados para o body map e o calendário de
disponibilidade (estado atual, nº de lesões, dias perdidos, episódios por
jogador).
"""
from datetime import date

import pandas as pd

from app.core.db import get_conn
from app.services.estado_service import listar_estados


def _dias(inicio, fim) -> int:
    fim_efetivo = fim or date.today()
    return max(0, (fim_efetivo - inicio).days)


CONTEXTOS = ("treino", "jogo", "outro")


def _tem_contexto(cur) -> bool:
    cur.execute("select exists (select 1 from information_schema.columns where table_name = 'lesoes' and column_name = 'contexto')")
    return bool(cur.fetchone()[0])


def guardar_lesao(team_id: str, player_id: str, zona: str, lado: str | None, tipo: str | None,
                  gravidade: str | None, data_inicio: str, data_fim: str | None, notas: str | None,
                  contexto: str | None = None) -> dict:
    contexto = contexto if contexto in CONTEXTOS else None
    with get_conn() as conn:
        with conn.cursor() as cur:
            if _tem_contexto(cur):
                cur.execute(
                    """
                    insert into lesoes (team_id, player_id, zona, lado, tipo, gravidade, data_inicio, data_fim, notas, contexto)
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    returning id
                    """,
                    (team_id, player_id, zona, lado, tipo, gravidade, data_inicio, data_fim or None, notas, contexto),
                )
            else:
                cur.execute(
                    """
                    insert into lesoes (team_id, player_id, zona, lado, tipo, gravidade, data_inicio, data_fim, notas)
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    returning id
                    """,
                    (team_id, player_id, zona, lado, tipo, gravidade, data_inicio, data_fim or None, notas),
                )
            return {"id": str(cur.fetchone()[0])}


# ── Epidemiologia (parte pura) ───────────────────────────────────────────────
# Indicadores de um departamento médico/performance (consenso de Fuller et al., 2006, para
# estudos de lesões no futebol): incidência e carga de lesão por 1000 h de
# exposição, em treino e em jogo, e disponibilidade do plantel. Com poucas
# horas (< HORAS_MINIMAS) os números variam muito com uma única lesão.
HORAS_MINIMAS = 1000.0


def epidemiologia(lesoes: pd.DataFrame, sessoes: pd.DataFrame, inicio: date, fim: date, n_jogadores: int) -> dict:
    """`lesoes`: jogador, data_inicio, data_fim, contexto, zona.
    `sessoes`: Jogador, Data, Tipo, Dia MD, Duração (min) (uma linha por sessão)."""
    from app.services.referencia_jogo import mascara_jogo

    out = {"inicio": inicio.isoformat(), "fim": fim.isoformat(), "horas": 0.0, "horas_treino": 0.0, "horas_jogo": 0.0,
           "n_lesoes": 0, "incidencia": None, "incidencia_treino": None, "incidencia_jogo": None,
           "carga": None, "dias_perdidos": 0, "disponibilidade_pct": None, "sem_contexto": 0,
           "zonas": [], "estimativa_instavel": True}
    if sessoes is not None and not sessoes.empty and "Duração (min)" in sessoes.columns:
        s = sessoes.copy()
        s["Data"] = pd.to_datetime(s["Data"])
        s = s[(s["Data"].dt.date >= inicio) & (s["Data"].dt.date <= fim)]
        dur = pd.to_numeric(s["Duração (min)"], errors="coerce").fillna(0) / 60.0
        jogo = mascara_jogo(s)
        out["horas_jogo"] = round(float(dur[jogo].sum()), 1)
        out["horas_treino"] = round(float(dur[~jogo].sum()), 1)
        out["horas"] = round(out["horas_jogo"] + out["horas_treino"], 1)

    def por_1000(n: float, h: float) -> float | None:
        return round(n / h * 1000, 1) if h > 0 else None

    if lesoes is not None and not lesoes.empty:
        l = lesoes.copy()
        l["data_inicio"] = pd.to_datetime(l["data_inicio"]).dt.date
        l["data_fim"] = [pd.Timestamp(x).date() if x is not None and pd.notna(x) else None for x in l["data_fim"]]
        novas = l[(l["data_inicio"] >= inicio) & (l["data_inicio"] <= fim)]
        out["n_lesoes"] = int(len(novas))
        ctx = novas["contexto"] if "contexto" in novas.columns else pd.Series([None] * len(novas), index=novas.index)
        out["sem_contexto"] = int(ctx.isna().sum())
        out["incidencia"] = por_1000(len(novas), out["horas"])
        out["incidencia_treino"] = por_1000(int((ctx == "treino").sum()), out["horas_treino"])
        out["incidencia_jogo"] = por_1000(int((ctx == "jogo").sum()), out["horas_jogo"])
        # Dias perdidos DENTRO do período (uma lesão de antes que continua conta a parte que cai aqui).
        dias = 0
        for r in l.itertuples(index=False):
            a = max(r.data_inicio, inicio)
            b = min(r.data_fim or fim, fim)
            if b >= a:
                dias += (b - a).days
        out["dias_perdidos"] = int(dias)
        out["carga"] = por_1000(dias, out["horas"])
        total_dias = max(1, (fim - inicio).days + 1) * max(1, int(n_jogadores))
        out["disponibilidade_pct"] = round(max(0.0, 1 - dias / total_dias) * 100, 1)
        if "zona" in novas.columns and not novas.empty:
            z = novas["zona"].value_counts().head(3)
            out["zonas"] = [{"zona": k, "n": int(v)} for k, v in z.items()]
    elif n_jogadores:
        out["disponibilidade_pct"] = 100.0
    out["estimativa_instavel"] = out["horas"] < HORAS_MINIMAS
    return out


def atualizar_lesao(team_id: str, lesao_id: str, data_fim: str | None, notas: str | None) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update lesoes set data_fim = %s, notas = coalesce(%s, notas), atualizado_em = now()
                where id = %s and team_id = %s
                returning id
                """,
                (data_fim or None, notas, lesao_id, team_id),
            )
            row = cur.fetchone()
            return {"id": str(row[0])} if row else {"id": None}


def apagar_lesao(team_id: str, lesao_id: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("delete from lesoes where id = %s and team_id = %s", (lesao_id, team_id))
            return {"removidas": cur.rowcount}


def obter_lesoes(team_id: str) -> dict:
    # Usa listar_estados (tabela players) e não carregar_df_equipa: precisamos do
    # player_id real de cada jogador para o formulário de registo de lesões poder
    # associar a lesão ao jogador certo. [{player_id, nome, posicao, ativo, ...}]
    jogadores_bd = [j for j in listar_estados(team_id) if j.get("ativo")]
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                ctx_col = "l.contexto" if _tem_contexto(cur) else "null::text"
                cur.execute(
                    f"""
                    select l.id, p.id, p.nome, coalesce(p.posicao,'—'), l.zona, l.lado, l.tipo,
                           l.gravidade, l.data_inicio, l.data_fim, l.notas, {ctx_col}
                    from lesoes l join players p on p.id = l.player_id
                    where l.team_id = %s
                    order by l.data_inicio desc
                    """,
                    (team_id,),
                )
                rows = cur.fetchall()
    except Exception:
        rows = []

    # Agrupa lesões por jogador.
    por_jogador: dict[str, dict] = {}
    for r in rows:
        lid, pid, nome, pos, zona, lado, tipo, grav, ini, fim, notas, contexto = r
        entry = por_jogador.setdefault(nome, {"player_id": str(pid), "jogador": nome, "posicao": pos, "lesoes": []})
        entry["lesoes"].append({
            "id": str(lid), "zona": zona, "lado": lado, "tipo": tipo, "gravidade": grav,
            "data_inicio": ini.isoformat() if ini else None,
            "data_fim": fim.isoformat() if fim else None,
            "dias": _dias(ini, fim) if ini else None,
            "em_curso": fim is None,
            "notas": notas,
            "contexto": contexto,
        })

    jogadores = []
    # Inclui todos os jogadores do plantel (mesmo sem lesões).
    nomes_vistos = set()
    for jb in jogadores_bd:
        nome = jb.get("nome")
        nomes_vistos.add(nome)
        e = por_jogador.get(nome, {"player_id": jb.get("player_id"), "jogador": nome, "posicao": jb.get("posicao", "—"), "lesoes": []})
        _preencher_agregados(e)
        jogadores.append(e)
    # Jogadores com lesões mas que já não estão no plantel atual (raro).
    for nome, e in por_jogador.items():
        if nome not in nomes_vistos:
            _preencher_agregados(e)
            jogadores.append(e)

    jogadores.sort(key=lambda j: (j["estado"] != "lesionado", -j["n_lesoes"], str(j["jogador"]).lower()))

    # Epidemiologia da época (julho → junho), até hoje.
    epi = None
    try:
        from app.services.dados_equipa import carregar_df_equipa
        from app.services.ficha_atleta_service import limites_epoca
        ini, fim_epoca = limites_epoca(None)
        fim = min(fim_epoca, date.today())
        df = carregar_df_equipa(team_id)
        les = pd.DataFrame([(r[2], r[8], r[9], r[11], r[4]) for r in rows], columns=["jogador", "data_inicio", "data_fim", "contexto", "zona"])
        epi = epidemiologia(les, df, ini, fim, len(jogadores_bd))
    except Exception:
        epi = None
    return {"tem_dados": True, "jogadores": jogadores, "epidemiologia": epi}


def _preencher_agregados(e: dict) -> None:
    lesoes = e["lesoes"]
    e["n_lesoes"] = len(lesoes)
    e["dias_perdidos"] = sum(l["dias"] or 0 for l in lesoes)
    e["estado"] = "lesionado" if any(l["em_curso"] for l in lesoes) else "disponível"
    # Frequência por zona (para o body map).
    freq: dict[str, int] = {}
    for l in lesoes:
        freq[l["zona"]] = freq.get(l["zona"], 0) + 1
    e["zonas_freq"] = freq
