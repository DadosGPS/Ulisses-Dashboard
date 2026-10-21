"""Equipa técnica da academia — convites, papéis e permissões.

Papéis (o que se escolhe no convite → o que fica na base de dados):
  responsável ('head')     → academia_membros 'head',    todas as equipas como 'owner'
  preparador físico ('pf') → academia_membros 'staff',   equipas escolhidas como 'pf'
  treinador ('treinador')  → academia_membros 'leitura', equipas escolhidas como 'treinador' (só consulta)

Convite = link pessoal com token (válido 14 dias). Quem o abre cria conta ou
entra, e ao aceitar fica nas equipas do convite. Pode limitar-se a um email.
"""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone

from app.core.db import get_conn

PAPEIS = {"head": "Responsável", "pf": "Preparador físico", "treinador": "Treinador (só consulta)"}
PAPEL_ACADEMIA = {"head": "head", "pf": "staff", "treinador": "leitura"}
ROLE_EQUIPA = {"head": "owner", "pf": "pf", "treinador": "treinador"}
ROLES_EDICAO = {"owner", "pf"}
METODOS_ESCRITA = {"POST", "PUT", "PATCH", "DELETE"}

MSG_MIGRACAO = "Os convites precisam da migração supabase/migrations/0017_convites_papeis.sql."


def disponivel() -> bool:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.convites') is not null")
                return bool(cur.fetchone()[0])
    except Exception:
        return False


def papel_de(papel_academia: str | None, roles_equipas: list[str]) -> str:
    """Papel 'legível' de um membro: head / pf / treinador."""
    if papel_academia == "head":
        return "head"
    if papel_academia == "leitura" or (roles_equipas and all(r == "treinador" for r in roles_equipas)):
        return "treinador"
    return "pf"


# ── Permissões (usadas pelo middleware de só-consulta) ───────────────────────
_RE_EQUIPA = re.compile(r"^/api/(?:teams|academia/equipas)/([0-9a-fA-F-]{36})(?:/|$)")


def motivo_bloqueio(cur, user_id: str, metodo: str, caminho: str) -> str | None:
    """Devolve a mensagem de recusa se o utilizador só pode consultar o que o
    pedido quer alterar; None se pode avançar (as outras verificações de
    pertença continuam a ser feitas por cada endpoint)."""
    if metodo.upper() not in METODOS_ESCRITA or caminho.startswith("/api/convites"):
        return None
    m = _RE_EQUIPA.match(caminho)
    if m:
        cur.execute("select role from team_members where team_id = %s and user_id = %s", (m.group(1), user_id))
        row = cur.fetchone()
        if row and row[0] == "treinador":
            return "O teu papel nesta equipa é Treinador: só consulta. Pede ao responsável para alterar o teu papel."
        return None
    if caminho.startswith("/api/academia") or caminho.startswith("/api/ingest"):
        cur.execute("select papel from academia_membros where user_id = %s", (user_id,))
        papeis = {r[0] for r in cur.fetchall()}
        if papeis and papeis <= {"leitura"}:
            return "O teu papel na academia é só de consulta."
    return None


# ── Leitura ──────────────────────────────────────────────────────────────────
def _academia_e_papel(cur, user_id: str) -> tuple[str, str]:
    cur.execute(
        """
        select academia_id::text, papel from academia_membros where user_id = %s
        order by case papel when 'head' then 0 when 'staff' then 1 else 2 end limit 1
        """,
        (user_id,),
    )
    row = cur.fetchone()
    if not row:
        raise PermissionError("Ainda não pertences a nenhuma academia.")
    return row[0], row[1]


def _equipas(cur, academia_id: str) -> list[dict]:
    cur.execute(
        "select id::text, coalesce(escalao || ' · ' || epoca, nome), escalao, epoca from teams where academia_id = %s order by epoca desc nulls last, escalao",
        (academia_id,),
    )
    return [{"team_id": t, "rotulo": r, "escalao": e, "epoca": ep} for t, r, e, ep in cur.fetchall()]


def _equipas_editaveis(cur, user_id: str, academia_id: str, papel_academia: str) -> set[str]:
    if papel_academia == "head":
        return {e["team_id"] for e in _equipas(cur, academia_id)}
    cur.execute(
        """
        select tm.team_id::text from team_members tm join teams t on t.id = tm.team_id
        where tm.user_id = %s and t.academia_id = %s and tm.role in ('owner', 'pf')
        """,
        (user_id, academia_id),
    )
    return {r[0] for r in cur.fetchall()}


def listar(user_id: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            academia_id, meu = _academia_e_papel(cur, user_id)
            equipas = _equipas(cur, academia_id)
            editaveis = _equipas_editaveis(cur, user_id, academia_id, meu)
            cur.execute(
                """
                select am.user_id::text, coalesce(p.nome, '—'), u.email, am.papel
                from academia_membros am
                left join profiles p on p.id = am.user_id
                left join auth.users u on u.id = am.user_id
                where am.academia_id = %s
                """,
                (academia_id,),
            )
            membros_raw = cur.fetchall()
            cur.execute(
                """
                select tm.user_id::text, tm.team_id::text, tm.role from team_members tm
                join teams t on t.id = tm.team_id where t.academia_id = %s
                """,
                (academia_id,),
            )
            por_membro: dict[str, list] = {}
            for uid, tid, role in cur.fetchall():
                por_membro.setdefault(uid, []).append((tid, role))
            cur.execute(
                """
                select c.id::text, c.papel, c.team_ids::text[], c.email, c.nome, c.token, c.criado_em, c.expira_em,
                       coalesce(p.nome, '—')
                from convites c left join profiles p on p.id = c.criado_por
                where c.academia_id = %s and c.aceite_em is null and not c.revogado and c.expira_em > now()
                order by c.criado_em desc
                """,
                (academia_id,),
            )
            convites = cur.fetchall()
    rotulo = {e["team_id"]: e["rotulo"] for e in equipas}
    membros = []
    for uid, nome, email, papel_acad in membros_raw:
        eqs = por_membro.get(uid, [])
        membros.append({
            "user_id": uid, "nome": nome, "email": email, "eu": uid == user_id,
            "papel": papel_de(papel_acad, [r for _, r in eqs]),
            "equipas": [{"team_id": t, "rotulo": rotulo.get(t, "?"), "role": r} for t, r in eqs],
        })
    membros.sort(key=lambda m: (["head", "pf", "treinador"].index(m["papel"]), m["nome"].lower()))
    return {
        "disponivel": True, "academia_id": academia_id, "meu_papel": papel_de(meu, []) if meu != "staff" else "pf",
        "pode_gerir": meu == "head", "pode_convidar": meu == "head" or bool(editaveis),
        "equipas": equipas, "equipas_editaveis": sorted(editaveis), "papeis": PAPEIS, "membros": membros,
        "convites": [{
            "id": i, "papel": pa, "equipas": [rotulo.get(t, "?") for t in (tids or [])], "email": em, "nome": no,
            "token": tok, "criado_em": cr.isoformat(), "expira_em": ex.isoformat(), "convidado_por": por,
        } for i, pa, tids, em, no, tok, cr, ex, por in convites],
    }


# ── Convites ─────────────────────────────────────────────────────────────────
def criar_convite(user_id: str, papel: str, team_ids: list[str], email: str | None, nome: str | None) -> dict:
    if papel not in PAPEIS:
        raise ValueError("Papel inválido.")
    email = (email or "").strip().lower() or None
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("Email inválido.")
    with get_conn() as conn:
        with conn.cursor() as cur:
            academia_id, meu = _academia_e_papel(cur, user_id)
            if papel == "head" and meu != "head":
                raise PermissionError("Só um responsável pode convidar outro responsável.")
            if papel != "head":
                if not team_ids:
                    raise ValueError("Escolhe pelo menos uma equipa.")
                editaveis = _equipas_editaveis(cur, user_id, academia_id, meu)
                fora = set(team_ids) - editaveis
                if fora:
                    raise PermissionError("Só podes convidar para equipas onde és preparador físico ou responsável.")
            token = secrets.token_urlsafe(24)
            cur.execute(
                """
                insert into convites (academia_id, papel, team_ids, email, nome, token, criado_por)
                values (%s, %s, %s::uuid[], %s, %s, %s, %s) returning id::text
                """,
                (academia_id, papel, team_ids if papel != "head" else [], email, (nome or "").strip()[:80] or None, token, user_id),
            )
            return {"ok": True, "id": cur.fetchone()[0], "token": token}


def revogar_convite(user_id: str, convite_id: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            academia_id, meu = _academia_e_papel(cur, user_id)
            cur.execute(
                "update convites set revogado = true where id = %s and academia_id = %s and (criado_por = %s or %s) and aceite_em is null",
                (convite_id, academia_id, user_id, meu == "head"),
            )
            return {"ok": cur.rowcount > 0}


def _carregar_convite(cur, token: str):
    cur.execute(
        """
        select c.id::text, c.academia_id::text, a.nome, c.papel, c.team_ids::text[], c.email, c.nome, c.expira_em,
               c.aceite_em, c.revogado, coalesce(p.nome, '—')
        from convites c join academias a on a.id = c.academia_id left join profiles p on p.id = c.criado_por
        where c.token = %s
        """,
        (token,),
    )
    return cur.fetchone()


def estado_convite(expira_em, aceite_em, revogado, agora: datetime | None = None) -> str:
    agora = agora or datetime.now(timezone.utc)
    if revogado:
        return "revogado"
    if aceite_em:
        return "aceite"
    if expira_em <= agora:
        return "expirado"
    return "valido"


def obter_convite_publico(token: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            row = _carregar_convite(cur, token)
            if not row:
                raise ValueError("Convite não encontrado.")
            _, academia_id, academia, papel, tids, email, nome, exp, aceite, revog, por = row
            rot = {e["team_id"]: e["rotulo"] for e in _equipas(cur, academia_id)}
    return {
        "academia": academia, "papel": papel, "papel_rotulo": PAPEIS[papel], "nome": nome,
        "equipas": ["Todas as equipas"] if papel == "head" else [rot.get(t, "?") for t in (tids or [])],
        "email": email, "convidado_por": por, "expira_em": exp.isoformat(),
        "estado": estado_convite(exp, aceite, revog),
    }


def aceitar_convite(user_id: str, email_utilizador: str | None, token: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            row = _carregar_convite(cur, token)
            if not row:
                raise ValueError("Convite não encontrado.")
            cid, academia_id, _, papel, tids, email, _, exp, aceite, revog, _ = row
            estado = estado_convite(exp, aceite, revog)
            if estado != "valido":
                raise ValueError({"aceite": "Este convite já foi usado.", "expirado": "Este convite expirou — pede um novo.",
                                  "revogado": "Este convite foi cancelado."}[estado])
            if email and (email_utilizador or "").lower() != email.lower():
                raise PermissionError(f"Este convite é para {email}. Entra com essa conta.")
            # Equipa vazia criada no registo (antes dos convites) → remove-se.
            _remover_equipa_vazia_do_registo(cur, user_id)
            papel_acad = PAPEL_ACADEMIA[papel]
            cur.execute(
                """
                insert into academia_membros (academia_id, user_id, papel) values (%s, %s, %s)
                on conflict (academia_id, user_id) do update set papel = case
                    when academia_membros.papel = 'head' or excluded.papel = 'head' then 'head'
                    when academia_membros.papel = 'staff' or excluded.papel = 'staff' then 'staff'
                    else 'leitura' end
                """,
                (academia_id, user_id, papel_acad),
            )
            equipas = [e["team_id"] for e in _equipas(cur, academia_id)] if papel == "head" else list(tids or [])
            role = ROLE_EQUIPA[papel]
            for t in equipas:
                cur.execute(
                    """
                    insert into team_members (team_id, user_id, role) values (%s, %s, %s)
                    on conflict (team_id, user_id) do update set role = case
                        when team_members.role in ('owner', 'pf') and excluded.role = 'treinador' then team_members.role
                        else excluded.role end
                    """,
                    (t, user_id, role),
                )
            cur.execute("update convites set aceite_por = %s, aceite_em = now() where id = %s", (user_id, cid))
    return {"ok": True, "equipas": equipas, "team_id": equipas[0] if equipas else None}


def _remover_equipa_vazia_do_registo(cur, user_id: str) -> None:
    cur.execute(
        """
        select t.id, t.academia_id from teams t join team_members tm on tm.team_id = t.id
        where tm.user_id = %s and t.criado_por = %s
          and (select count(*) from team_members x where x.team_id = t.id) = 1
          and not exists (select 1 from players p where p.team_id = t.id)
          and not exists (select 1 from gps_sessions g where g.team_id = t.id)
        """,
        (user_id, user_id),
    )
    for team_id, academia_id in cur.fetchall():
        cur.execute("delete from teams where id = %s", (team_id,))
        if academia_id:
            cur.execute(
                """
                delete from academias a where a.id = %s
                  and not exists (select 1 from teams t where t.academia_id = a.id)
                  and not exists (select 1 from academia_membros m where m.academia_id = a.id and m.user_id <> %s)
                """,
                (academia_id, user_id),
            )


# ── Gestão de membros (só responsáveis) ──────────────────────────────────────
def alterar_membro(user_id: str, alvo_id: str, papel: str, team_ids: list[str]) -> dict:
    if papel not in PAPEIS:
        raise ValueError("Papel inválido.")
    with get_conn() as conn:
        with conn.cursor() as cur:
            academia_id, meu = _academia_e_papel(cur, user_id)
            if meu != "head":
                raise PermissionError("Só um responsável pode alterar papéis.")
            cur.execute("select papel from academia_membros where academia_id = %s and user_id = %s", (academia_id, alvo_id))
            row = cur.fetchone()
            if not row:
                raise ValueError("Membro não encontrado.")
            if row[0] == "head" and papel != "head":
                _garantir_outro_head(cur, academia_id, alvo_id)
            todas = [e["team_id"] for e in _equipas(cur, academia_id)]
            alvo_equipas = todas if papel == "head" else [t for t in team_ids if t in todas]
            if papel != "head" and not alvo_equipas:
                raise ValueError("Escolhe pelo menos uma equipa.")
            cur.execute("update academia_membros set papel = %s where academia_id = %s and user_id = %s",
                        (PAPEL_ACADEMIA[papel], academia_id, alvo_id))
            cur.execute("delete from team_members where user_id = %s and team_id = any(%s::uuid[]) and not (team_id = any(%s::uuid[]))",
                        (alvo_id, todas, alvo_equipas))
            for t in alvo_equipas:
                cur.execute(
                    "insert into team_members (team_id, user_id, role) values (%s, %s, %s) on conflict (team_id, user_id) do update set role = excluded.role",
                    (t, alvo_id, ROLE_EQUIPA[papel]),
                )
    return {"ok": True}


def remover_membro(user_id: str, alvo_id: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            academia_id, meu = _academia_e_papel(cur, user_id)
            if meu != "head":
                raise PermissionError("Só um responsável pode remover membros.")
            cur.execute("select papel from academia_membros where academia_id = %s and user_id = %s", (academia_id, alvo_id))
            row = cur.fetchone()
            if not row:
                raise ValueError("Membro não encontrado.")
            if row[0] == "head":
                _garantir_outro_head(cur, academia_id, alvo_id)
            todas = [e["team_id"] for e in _equipas(cur, academia_id)]
            cur.execute("delete from team_members where user_id = %s and team_id = any(%s::uuid[])", (alvo_id, todas))
            cur.execute("delete from academia_membros where academia_id = %s and user_id = %s", (academia_id, alvo_id))
    return {"ok": True}


def _garantir_outro_head(cur, academia_id: str, alvo_id: str) -> None:
    cur.execute("select count(*) from academia_membros where academia_id = %s and papel = 'head' and user_id <> %s",
                (academia_id, alvo_id))
    if cur.fetchone()[0] == 0:
        raise ValueError("A academia ficaria sem responsável. Nomeia outro responsável primeiro.")
