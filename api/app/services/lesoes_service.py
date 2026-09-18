"""Histórico de lesões — CRUD + agregados para o body map e o calendário de
disponibilidade (estado atual, nº de lesões, dias perdidos, episódios por
jogador).
"""
from datetime import date

from app.core.db import get_conn


def _dias(inicio, fim) -> int:
    fim_efetivo = fim or date.today()
    return max(0, (fim_efetivo - inicio).days)


def guardar_lesao(team_id: str, player_id: str, zona: str, lado: str | None, tipo: str | None,
                  gravidade: str | None, data_inicio: str, data_fim: str | None, notas: str | None) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into lesoes (team_id, player_id, zona, lado, tipo, gravidade, data_inicio, data_fim, notas)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                returning id
                """,
                (team_id, player_id, zona, lado, tipo, gravidade, data_inicio, data_fim or None, notas),
            )
            return {"id": str(cur.fetchone()[0])}


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
    jogadores_bd = listar_jogadores(team_id)  # [{nome, posicao, ...}] — ver jogador_service
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select l.id, p.id, p.nome, coalesce(p.posicao,'—'), l.zona, l.lado, l.tipo,
                           l.gravidade, l.data_inicio, l.data_fim, l.notas
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
        lid, pid, nome, pos, zona, lado, tipo, grav, ini, fim, notas = r
        entry = por_jogador.setdefault(nome, {"player_id": str(pid), "jogador": nome, "posicao": pos, "lesoes": []})
        entry["lesoes"].append({
            "id": str(lid), "zona": zona, "lado": lado, "tipo": tipo, "gravidade": grav,
            "data_inicio": ini.isoformat() if ini else None,
            "data_fim": fim.isoformat() if fim else None,
            "dias": _dias(ini, fim) if ini else None,
            "em_curso": fim is None,
            "notas": notas,
        })

    jogadores = []
    # Inclui todos os jogadores do plantel (mesmo sem lesões).
    nomes_vistos = set()
    for jb in jogadores_bd:
        nome = jb.get("nome")
        nomes_vistos.add(nome)
        e = por_jogador.get(nome, {"player_id": jb.get("id"), "jogador": nome, "posicao": jb.get("posicao", "—"), "lesoes": []})
        _preencher_agregados(e)
        jogadores.append(e)
    # Jogadores com lesões mas que já não estão no plantel atual (raro).
    for nome, e in por_jogador.items():
        if nome not in nomes_vistos:
            _preencher_agregados(e)
            jogadores.append(e)

    jogadores.sort(key=lambda j: (j["estado"] != "lesionado", -j["n_lesoes"], str(j["jogador"]).lower()))
    return {"tem_dados": True, "jogadores": jogadores}


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
