"""Jogadores duplicados: encontrar e juntar.

O mesmo jogador pode chegar com o nome escrito de maneiras diferentes —
«Olle Brännström» no STATSports e «Olle Brannstrom» na folha de PSE, ou um
erro de escrita no formulário — e a app criava dois jogadores. Para evitar
novos duplicados, a importação compara os nomes sem acentos
(ingest_service._chave_nome); para os que já existem há:

- `sugerir_duplicados`: pares de jogadores ativos da equipa com nomes iguais
  sem acentos ou muito parecidos;
- `juntar`: passa todos os dados de um jogador (origem) para outro (destino)
  — sessões de GPS/PSE/wellness, períodos, lesões, planos de regresso,
  testes, força, decisões e pedidos de resposta — e apaga a origem. Quando os
  dois têm a mesma sessão (mesmo dia e tipo), as duas linhas são fundidas:
  fica o valor do destino e, onde este não tem, o da origem.
"""
from __future__ import annotations

import unicodedata
from difflib import SequenceMatcher

from app.core.db import get_conn
from app.services.dados_equipa import invalidar_cache_equipa
from app.services.lesoes_service import sincronizar_estado

# Colunas de gps_sessions fundidas quando origem e destino têm a mesma sessão.
_COLS_SESSAO = (
    "upload_id", "dia_md", "microciclo_nr", "distancia_total_m", "hsr_m", "sprint_m", "acc_n", "dcc_n",
    "vel_max_kmh", "pse_sessao", "duracao_min", "carga_interna", "hooper_index", "sono", "dor_musc",
    "stress", "humor", "fadiga",
)
# Tabelas que só guardam player_id, sem unicidade que o inclua.
_TABELAS_SIMPLES = ("gps_periodos", "lesoes", "planos_rtp", "testes_neuromusculares", "decisoes")


class ErroJuntar(Exception):
    """Erro com mensagem pronta a mostrar ao utilizador."""


def chave_nome(nome: str | None) -> str:
    """Nome sem acentos, minúsculas e espaços normalizados («Olle Brännström»
    e «olle  brannstrom» dão o mesmo)."""
    s = unicodedata.normalize("NFKD", str(nome or "")).encode("ascii", "ignore").decode()
    return " ".join(s.split()).lower()


def parecidos(a: str, b: str) -> bool:
    """Mesmo nome sem acentos, ou nomes quase iguais (erro de escrita de uma
    ou duas letras, ex.: «Borbos»/«Brobos», «Sivnert»/«Sinvert»)."""
    ka, kb = chave_nome(a), chave_nome(b)
    if not ka or not kb:
        return False
    if ka == kb:
        return True
    pa, pb = ka.split(), kb.split()
    # Primeiro nome igual e apelido muito parecido, ou nome completo muito parecido.
    if pa[0] == pb[0] and len(pa) > 1 and len(pb) > 1 and SequenceMatcher(None, pa[-1], pb[-1]).ratio() >= 0.8:
        return True
    return SequenceMatcher(None, ka, kb).ratio() >= 0.9


def sugerir_duplicados(team_id: str) -> list[dict]:
    """Pares prováveis, com o nº de sessões e lesões de cada um. Sugere manter
    o que tem mais sessões (normalmente o nome que vem do GPS)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select p.id::text, p.nome, p.estado,
                       (select count(*) from gps_sessions g where g.player_id = p.id),
                       (select count(*) from lesoes l where l.player_id = p.id),
                       (select max(g.data) from gps_sessions g where g.player_id = p.id)
                from players p where p.team_id = %s and p.ativo order by p.nome
                """,
                (team_id,),
            )
            jogadores = [
                {"player_id": r[0], "nome": r[1], "estado": r[2], "sessoes": r[3], "lesoes": r[4],
                 "ultima_sessao": r[5].isoformat() if r[5] else None}
                for r in cur.fetchall()
            ]
    pares = []
    for i, a in enumerate(jogadores):
        for b in jogadores[i + 1:]:
            if parecidos(a["nome"], b["nome"]):
                manter, juntar_ = (a, b) if (a["sessoes"], a["lesoes"]) >= (b["sessoes"], b["lesoes"]) else (b, a)
                pares.append({"manter": manter, "juntar": juntar_})
    return pares


def juntar(team_id: str, origem_id: str, destino_id: str) -> dict:
    """Passa tudo da origem para o destino e apaga a origem. Uma transação:
    ou passa tudo, ou nada muda."""
    if origem_id == destino_id:
        raise ErroJuntar("Escolhe dois jogadores diferentes.")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select id::text, nome from players where team_id = %s and id in (%s, %s)",
                        (team_id, origem_id, destino_id))
            nomes = dict(cur.fetchall())
            if origem_id not in nomes or destino_id not in nomes:
                raise ErroJuntar("Jogador não encontrado nesta equipa.")
            contagem: dict[str, int] = {}

            # 1) Sessões no mesmo dia e tipo: funde na linha do destino.
            atribs = ", ".join(f"{c} = coalesce(d.{c}, o.{c})" for c in _COLS_SESSAO)
            cur.execute(
                f"""
                update gps_sessions d set {atribs},
                       extra_metrics = coalesce(o.extra_metrics, '{{}}'::jsonb) || coalesce(d.extra_metrics, '{{}}'::jsonb)
                from gps_sessions o
                where d.team_id = %s and d.player_id = %s and o.team_id = d.team_id and o.player_id = %s
                  and o.data = d.data and o.tipo is not distinct from d.tipo
                """,
                (team_id, destino_id, origem_id),
            )
            contagem["sessoes_fundidas"] = cur.rowcount
            cur.execute(
                """
                delete from gps_sessions o using gps_sessions d
                where o.team_id = %s and o.player_id = %s and d.team_id = o.team_id and d.player_id = %s
                  and d.data = o.data and d.tipo is not distinct from o.tipo
                """,
                (team_id, origem_id, destino_id),
            )
            cur.execute("update gps_sessions set player_id = %s where team_id = %s and player_id = %s",
                        (destino_id, team_id, origem_id))
            contagem["sessoes_movidas"] = cur.rowcount

            # 2) Pedidos de resposta: um por jogador/tipo/dia — fica o do destino.
            cur.execute(
                """
                delete from pedidos_resposta o using pedidos_resposta d
                where o.team_id = %s and o.player_id = %s and d.team_id = o.team_id and d.player_id = %s
                  and d.tipo = o.tipo and d.data = o.data
                """,
                (team_id, origem_id, destino_id),
            )
            cur.execute("update pedidos_resposta set player_id = %s where team_id = %s and player_id = %s",
                        (destino_id, team_id, origem_id))

            # 3) Registos de força: únicos por sessão/jogador/ordem.
            cur.execute(
                """
                delete from forca_registos o using forca_registos d
                where o.player_id = %s and d.player_id = %s and d.sessao_id = o.sessao_id and d.ordem = o.ordem
                """,
                (origem_id, destino_id),
            )
            cur.execute("update forca_registos set player_id = %s where player_id = %s", (destino_id, origem_id))

            # 4) Tabelas só com player_id.
            for tabela in _TABELAS_SIMPLES:
                cur.execute(f"update {tabela} set player_id = %s where team_id = %s and player_id = %s",
                            (destino_id, team_id, origem_id))
                contagem[tabela] = cur.rowcount

            # 5) Decisões guardam também o nome (único por jogador/dia/sinal).
            cur.execute(
                """
                delete from decisoes o using decisoes d
                where o.team_id = %s and o.jogador = %s and d.team_id = o.team_id and d.jogador = %s
                  and d.data = o.data and d.sinal = o.sinal
                """,
                (team_id, nomes[origem_id], nomes[destino_id]),
            )
            cur.execute("update decisoes set jogador = %s where team_id = %s and jogador = %s",
                        (nomes[destino_id], team_id, nomes[origem_id]))

            # 6) Dados do jogador que o destino ainda não tem; apaga a origem.
            cur.execute(
                """
                update players d set posicao = coalesce(d.posicao, o.posicao),
                       telefone = coalesce(d.telefone, o.telefone),
                       consentimento_mensagens_em = coalesce(d.consentimento_mensagens_em, o.consentimento_mensagens_em),
                       data_nascimento = coalesce(d.data_nascimento, o.data_nascimento),
                       atleta_id = coalesce(d.atleta_id, o.atleta_id)
                from players o where d.id = %s and o.id = %s
                """,
                (destino_id, origem_id),
            )
            cur.execute("delete from players where id = %s and team_id = %s", (origem_id, team_id))
            sincronizar_estado(cur, team_id, destino_id)

    invalidar_cache_equipa(team_id)
    return {"ok": True, "mantido": nomes[destino_id], "removido": nomes[origem_id], **contagem}
