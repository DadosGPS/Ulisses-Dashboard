"""Academia — escalões × épocas por cima das equipas existentes.

Cada escalão numa época é uma equipa (teams) como sempre foi, por isso todas
as páginas atuais continuam a trabalhar só com os dados dessa equipa/época.
Esta camada acrescenta:
  • a arrumação das equipas por academia, escalão e época;
  • a criação da equipa da época seguinte, opcionalmente com o plantel
    copiado de outra equipa (as fichas de atleta mantêm-se);
  • a ficha permanente de cada atleta (`atletas`), ligada às suas linhas em
    `players` ao longo dos anos — base da ficha longitudinal (fase 2).

Os atletas entram na academia UM A UM, adicionados pelo preparador físico
(adicionar_atleta). Um atleta pode estar em várias equipas da mesma época
(ex.: um sub-16 que treina também nos sub-17): tem uma linha em `players` em
cada uma, todas com o mesmo atleta_id, e cada equipa vê as sessões das outras
(ver dados_equipa.carregar_df_equipa).

Resiliente à migração 0009 não estar aplicada: `disponivel()` diz se as
tabelas existem e quem chama mostra a instrução em vez de falhar.
"""
from __future__ import annotations

import re
from datetime import date

from app.core.db import get_conn

MSG_MIGRACAO = (
    "A estrutura da academia ainda não existe na base de dados. Aplica a migração "
    "supabase/migrations/0009_academia.sql no SQL Editor do Supabase."
)

ESCALOES = ["Sub-15", "Sub-16", "Sub-17", "Sub-19"]


def validar_escalao(escalao: str | None) -> str:
    e = (escalao or "").strip()
    for opc in ESCALOES:
        if e.lower() == opc.lower():
            return opc
    raise ValueError(f"Escalão inválido — opções: {', '.join(ESCALOES)}.")


def disponivel() -> bool:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select to_regclass('public.academias') is not null
                       and to_regclass('public.atletas') is not null
                       and exists (select 1 from information_schema.columns
                                   where table_name = 'teams' and column_name = 'academia_id')
                    """
                )
                return bool(cur.fetchone()[0])
    except Exception:
        return False


def epoca_atual(hoje: date | None = None) -> str:
    """Época desportiva (julho a junho): 2026-10-20 → '2026/27'."""
    d = hoje or date.today()
    ini = d.year if d.month >= 7 else d.year - 1
    return f"{ini}/{str(ini + 1)[-2:]}"


def epoca_seguinte(epoca: str) -> str:
    m = re.fullmatch(r"(\d{4})/(\d{2})", epoca or "")
    if not m:
        return epoca_atual()
    ini = int(m.group(1)) + 1
    return f"{ini}/{str(ini + 1)[-2:]}"


def validar_epoca(epoca: str) -> str:
    e = (epoca or "").strip()
    m = re.fullmatch(r"(\d{4})/(\d{2})", e)
    if not m or int(m.group(2)) != (int(m.group(1)) + 1) % 100:
        raise ValueError("Época inválida — usa o formato 2026/27.")
    return e


def _rotulo(nome: str, escalao: str | None, epoca: str | None) -> str:
    if escalao and epoca:
        return f"{escalao} · {epoca}"
    return nome


def _garantir_academia(cur, user_id: str) -> None:
    """Equipas do utilizador ainda sem academia (ex.: registo novo, criado pelo
    trigger de signup) ganham uma, com o utilizador como 'head'."""
    cur.execute(
        """
        select t.id, t.nome from teams t join team_members tm on tm.team_id = t.id
        where tm.user_id = %s and t.academia_id is null
        """,
        (user_id,),
    )
    for team_id, nome in cur.fetchall():
        cur.execute("insert into academias (nome) values (%s) returning id", (nome or "Academia",))
        academia_id = cur.fetchone()[0]
        cur.execute("update teams set academia_id = %s where id = %s", (academia_id, team_id))
        cur.execute(
            "insert into academia_membros (academia_id, user_id, papel) values (%s, %s, 'head') on conflict do nothing",
            (academia_id, user_id),
        )
        _ligar_atletas_cur(cur, str(team_id))


def obter_estrutura(user_id: str) -> dict:
    """Academias do utilizador com as suas equipas (escalão × época)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            _garantir_academia(cur, user_id)
            cur.execute(
                """
                select a.id, a.nome, am.papel
                from academias a join academia_membros am on am.academia_id = a.id
                where am.user_id = %s order by a.nome
                """,
                (user_id,),
            )
            academias = cur.fetchall()
            cur.execute(
                """
                select t.id, t.nome, t.academia_id, t.escalao, t.epoca,
                       (select count(*) from players p where p.team_id = t.id and p.ativo) as n_jogadores,
                       (select max(gs.data) from gps_sessions gs where gs.team_id = t.id) as ultima_sessao
                from teams t join team_members tm on tm.team_id = t.id
                where tm.user_id = %s
                """,
                (user_id,),
            )
            equipas = cur.fetchall()

    ordem_escalao = {e: i for i, e in enumerate(ESCALOES)}
    lista_eq = [
        {
            "team_id": str(tid), "nome": nome, "academia_id": str(aid) if aid else None,
            "escalao": esc, "epoca": ep, "rotulo": _rotulo(nome, esc, ep),
            "n_jogadores": int(nj or 0), "ultima_sessao": us.isoformat() if us else None,
        }
        for tid, nome, aid, esc, ep, nj, us in equipas
    ]
    # Época mais recente primeiro; dentro da época, pela ordem dos escalões.
    lista_eq.sort(key=lambda e: (-(int(e["epoca"][:4]) if e["epoca"] else 0), ordem_escalao.get(e["escalao"] or "", 99), e["rotulo"]))
    return {
        "disponivel": True,
        "epoca_atual": epoca_atual(),
        "escaloes": ESCALOES,
        "academias": [
            {"academia_id": str(aid), "nome": nome, "papel": papel,
             "equipas": [e for e in lista_eq if e["academia_id"] == str(aid)]}
            for aid, nome, papel in academias
        ],
        "equipas": lista_eq,
    }


def _papel(cur, user_id: str, academia_id: str) -> str | None:
    cur.execute("select papel from academia_membros where academia_id = %s and user_id = %s", (academia_id, user_id))
    row = cur.fetchone()
    return row[0] if row else None


def criar_equipa(user_id: str, academia_id: str, escalao: str, epoca: str, copiar_de: str | None = None) -> dict:
    escalao = validar_escalao(escalao)
    epoca = validar_epoca(epoca)
    with get_conn() as conn:
        with conn.cursor() as cur:
            if not _papel(cur, user_id, academia_id):
                raise PermissionError("Não pertences a esta academia.")
            cur.execute(
                "select 1 from teams where academia_id = %s and lower(escalao) = lower(%s) and epoca = %s",
                (academia_id, escalao, epoca),
            )
            if cur.fetchone():
                raise ValueError(f"Já existe a equipa {escalao} · {epoca}.")
            cur.execute(
                """
                insert into teams (nome, desporto, criado_por, academia_id, escalao, epoca)
                values (%s, 'Futebol', %s, %s, %s, %s) returning id
                """,
                (f"{escalao} · {epoca}", user_id, academia_id, escalao, epoca),
            )
            team_id = str(cur.fetchone()[0])
            cur.execute("insert into team_members (team_id, user_id, role) values (%s, %s, 'owner')", (team_id, user_id))

            copiados = 0
            if copiar_de:
                cur.execute(
                    """
                    select 1 from teams t join team_members tm on tm.team_id = t.id
                    where t.id = %s and t.academia_id = %s and tm.user_id = %s
                    """,
                    (copiar_de, academia_id, user_id),
                )
                if not cur.fetchone():
                    raise PermissionError("Não podes copiar o plantel dessa equipa.")
                _ligar_atletas_cur(cur, copiar_de)
                cur.execute(
                    """
                    insert into players (team_id, nome, posicao, atleta_id, data_nascimento)
                    select %s, nome, posicao, atleta_id, data_nascimento
                    from players where team_id = %s and ativo
                    on conflict (team_id, nome) do nothing
                    """,
                    (team_id, copiar_de),
                )
                copiados = cur.rowcount
    return {"ok": True, "team_id": team_id, "rotulo": f"{escalao} · {epoca}", "jogadores_copiados": copiados}


def atualizar_equipa(user_id: str, team_id: str, escalao: str | None, epoca: str | None) -> dict:
    escalao = validar_escalao(escalao) if (escalao or "").strip() else None
    epoca = validar_epoca(epoca) if epoca else None
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select 1 from team_members where team_id = %s and user_id = %s", (team_id, user_id))
            if not cur.fetchone():
                raise PermissionError("Não pertences a esta equipa.")
            cur.execute(
                """
                update teams set escalao = %s, epoca = %s,
                    nome = case when %s is not null and %s is not null then %s || ' · ' || %s else nome end
                where id = %s returning id
                """,
                (escalao, epoca, escalao, epoca, escalao, epoca, team_id),
            )
            ok = cur.fetchone() is not None
    return {"ok": ok}


# ── Fichas de atleta ─────────────────────────────────────────────────────────
def _ligar_atletas_cur(cur, team_id: str) -> int:
    """Liga jogadores da equipa ainda sem ficha a um atleta JÁ existente na
    academia com o mesmo nome (ex.: o import de GPS trouxe "João Silva" e o
    PF já o tinha adicionado). Não cria atletas — isso é sempre manual.
    Só liga quando o nome corresponde a um único atleta."""
    cur.execute("select academia_id from teams where id = %s", (team_id,))
    row = cur.fetchone()
    if not row or not row[0]:
        return 0
    academia_id = row[0]
    cur.execute(
        """
        update players p set atleta_id = a.id from atletas a
        where p.team_id = %s and p.atleta_id is null and a.academia_id = %s
          and lower(a.nome) = lower(p.nome)
          and (select count(*) from atletas a2 where a2.academia_id = a.academia_id and lower(a2.nome) = lower(a.nome)) = 1
        """,
        (team_id, academia_id),
    )
    return cur.rowcount


def _pode_gerir_equipa(cur, user_id: str, team_id: str) -> str:
    """Pode pôr/tirar atletas de uma equipa quem é membro dessa equipa ou
    responsável ('head') da academia. Devolve o academia_id."""
    cur.execute(
        """
        select t.academia_id,
               exists (select 1 from team_members tm where tm.team_id = t.id and tm.user_id = %s),
               (select am.papel from academia_membros am where am.academia_id = t.academia_id and am.user_id = %s)
        from teams t where t.id = %s
        """,
        (user_id, user_id, team_id),
    )
    row = cur.fetchone()
    if not row or not row[0] or not row[2]:
        raise PermissionError("Esta equipa não pertence à tua academia.")
    if not row[1] and row[2] != "head":
        raise PermissionError("Só o preparador físico da equipa (ou o responsável da academia) pode alterar o plantel.")
    return str(row[0])


def _inserir_em_equipa(cur, atleta_id: str, team_id: str) -> None:
    cur.execute("select nome, data_nascimento, posicao_principal from atletas where id = %s", (atleta_id,))
    row = cur.fetchone()
    if not row:
        raise ValueError("Atleta não encontrado.")
    nome, nasc, posicao = row
    cur.execute(
        """
        insert into players (team_id, nome, posicao, atleta_id, data_nascimento)
        values (%s, %s, %s, %s, %s)
        on conflict (team_id, nome) do update set atleta_id = excluded.atleta_id, ativo = true,
            data_nascimento = coalesce(players.data_nascimento, excluded.data_nascimento),
            posicao = coalesce(players.posicao, excluded.posicao)
        where players.atleta_id is null or players.atleta_id = excluded.atleta_id
        """,
        (team_id, nome, posicao, atleta_id, nasc),
    )
    if cur.rowcount == 0:
        raise ValueError(f"Já existe outro jogador chamado {nome} nessa equipa.")


def adicionar_atleta(user_id: str, academia_id: str, nome: str, data_nascimento: str | None,
                     posicao: str | None, pe_dominante: str | None, team_ids: list[str]) -> dict:
    nome = " ".join((nome or "").split())
    if len(nome) < 2:
        raise ValueError("Indica o nome do jogador.")
    if not team_ids:
        raise ValueError("Escolhe pelo menos uma equipa.")
    if pe_dominante and pe_dominante not in ("direito", "esquerdo", "ambos"):
        raise ValueError("Pé dominante inválido.")
    dn = date.fromisoformat(data_nascimento) if data_nascimento else None
    with get_conn() as conn:
        with conn.cursor() as cur:
            for tid in team_ids:
                if _pode_gerir_equipa(cur, user_id, tid) != academia_id:
                    raise PermissionError("Essa equipa é de outra academia.")
            cur.execute(
                """
                select 1 from atletas where academia_id = %s and lower(nome) = lower(%s)
                  and coalesce(data_nascimento, '1900-01-01'::date) = coalesce(%s::date, '1900-01-01'::date)
                """,
                (academia_id, nome, dn),
            )
            if cur.fetchone():
                raise ValueError(f"{nome} já está na academia — usa “+ equipa” na lista para o pôr noutra equipa.")
            cur.execute(
                """
                insert into atletas (academia_id, nome, data_nascimento, posicao_principal, pe_dominante)
                values (%s, %s, %s, %s, %s) returning id
                """,
                (academia_id, nome, dn, (posicao or "").strip() or None, pe_dominante or None),
            )
            atleta_id = str(cur.fetchone()[0])
            for tid in team_ids:
                _inserir_em_equipa(cur, atleta_id, tid)
    from app.services.dados_equipa import invalidar_cache_equipa
    for tid in team_ids:
        invalidar_cache_equipa(tid)
    return {"ok": True, "atleta_id": atleta_id}


def _academia_do_atleta(cur, atleta_id: str) -> str:
    cur.execute("select academia_id from atletas where id = %s", (atleta_id,))
    row = cur.fetchone()
    if not row:
        raise ValueError("Atleta não encontrado.")
    return str(row[0])


def adicionar_a_equipa(user_id: str, atleta_id: str, team_id: str) -> dict:
    """Põe um atleta (também) noutra equipa — ex.: sub-16 que passa a treinar nos sub-17."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            if _pode_gerir_equipa(cur, user_id, team_id) != _academia_do_atleta(cur, atleta_id):
                raise PermissionError("Essa equipa é de outra academia.")
            _inserir_em_equipa(cur, atleta_id, team_id)
    from app.services.dados_equipa import invalidar_cache_equipa
    invalidar_cache_equipa(None)
    return {"ok": True}


def remover_de_equipa(user_id: str, atleta_id: str, team_id: str) -> dict:
    """Tira o atleta do plantel ativo da equipa. O histórico fica guardado."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            if _pode_gerir_equipa(cur, user_id, team_id) != _academia_do_atleta(cur, atleta_id):
                raise PermissionError("Essa equipa é de outra academia.")
            cur.execute("update players set ativo = false where atleta_id = %s and team_id = %s", (atleta_id, team_id))
            n = cur.rowcount
    from app.services.dados_equipa import invalidar_cache_equipa
    invalidar_cache_equipa(None)
    return {"ok": n > 0}


def apagar_atleta(user_id: str, atleta_id: str, tudo: bool = False) -> dict:
    """Apaga a ficha. Normal (ex.: adicionado por engano): as linhas de jogador
    sem nenhuma sessão desaparecem; as que já têm dados ficam na equipa, sem ficha.
    `tudo=True` (direito ao apagamento, RGPD — só o responsável): apaga também
    todas as sessões, testes, lesões, planos de regresso, respostas e jogos."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            academia_id = _academia_do_atleta(cur, atleta_id)
            if tudo and _papel(cur, user_id, academia_id) != "head":
                raise PermissionError("Só o responsável da academia pode apagar todos os dados de um atleta.")
            cur.execute("select team_id from players where atleta_id = %s", (atleta_id,))
            for (tid,) in cur.fetchall():
                if _pode_gerir_equipa(cur, user_id, str(tid)) != academia_id:
                    raise PermissionError("Este atleta está numa equipa de outra academia.")
            if tudo:
                cur.execute("delete from players where atleta_id = %s", (atleta_id,))  # em cascata: sessões, testes, lesões…
            cur.execute(
                """
                delete from players p where p.atleta_id = %s
                  and not exists (select 1 from gps_sessions gs where gs.player_id = p.id)
                """,
                (atleta_id,),
            )
            cur.execute("delete from atletas where id = %s", (atleta_id,))
    from app.services.dados_equipa import invalidar_cache_equipa
    invalidar_cache_equipa(None)
    return {"ok": True}


def ligar_atletas(team_id: str) -> int:
    """Chamado depois de importar dados ou criar jogadores (só liga a fichas
    existentes). Silencioso se a
    migração 0009 ainda não estiver aplicada."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.atletas') is not null")
                if not cur.fetchone()[0]:
                    return 0
                return _ligar_atletas_cur(cur, team_id)
    except Exception:
        return 0
