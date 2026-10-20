"""Questionário de bem-estar e PSE no telemóvel do jogador.

Fluxo:
  1. Um pedido (bem-estar de manhã, ou PSE depois do treino) cria uma linha
     em `pedidos_resposta` por jogador, com um token secreto;
  2. O jogador recebe por WhatsApp um link pessoal  <app_url>/r/<token>;
  3. Abre no telemóvel, sem login, responde — a resposta grava-se na sessão
     do dia em `gps_sessions` (o mesmo sítio onde o resto da app lê).

Só recebem mensagens jogadores ativos com telefone válido E consentimento
registado (`players.consentimento_mensagens_em`) — nos escalões de formação
o consentimento tem de vir também do encarregado de educação.
Sem Twilio configurado, os envios ficam «simulados»: os links aparecem na
página Mensagens para partilhar à mão.
"""
from __future__ import annotations

import secrets
from urllib.parse import quote
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import get_settings
from app.core.db import get_conn
from app.services import whatsapp_service
from app.services.dados_equipa import invalidar_cache_equipa

FUSO = ZoneInfo("Europe/Lisbon")
VALIDADE = {"wellness": timedelta(hours=18), "pse": timedelta(hours=36)}

MSG_MIGRACAO = (
    "As tabelas das mensagens ainda não existem. Aplica a migração "
    "supabase/migrations/0008_mensagens_jogadores.sql no SQL Editor do Supabase."
)


def agora() -> datetime:
    return datetime.now(FUSO)


def primeiro_nome(nome: str) -> str:
    return (nome or "").strip().split(" ")[0] or "atleta"


def texto_mensagem(tipo: str, nome: str, link: str) -> str:
    n = primeiro_nome(nome)
    if tipo == "wellness":
        return f"Bom dia, {n}! Como te sentes hoje? Responde ao questionário de bem-estar (30 segundos): {link}"
    return f"{n}, treino terminado. Qual foi o esforço da sessão de hoje, de 0 a 10? Responde aqui: {link}"


def link_pedido(token: str) -> str:
    return f"{get_settings().app_url.rstrip('/')}/r/{token}"


def link_whatsapp(telefone: str | None, texto: str) -> str | None:
    """Link «clique para conversar» do WhatsApp (gratuito): abre a conversa com
    o jogador já com a mensagem escrita — quem envia só carrega em enviar."""
    numero = whatsapp_service.normalizar_telefone(telefone)
    if not numero:
        return None
    return f"https://wa.me/{numero.lstrip('+')}?text={quote(texto)}"


def tabelas_disponiveis() -> bool:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select to_regclass('public.pedidos_resposta') is not null
                       and to_regclass('public.config_mensagens') is not null
                       and exists (select 1 from information_schema.columns
                                   where table_name = 'players' and column_name = 'telefone')
                    """
                )
                return bool(cur.fetchone()[0])
    except Exception:
        return False


# ── Configuração ─────────────────────────────────────────────────────────────
CONFIG_PADRAO = {"wellness_auto": False, "wellness_hora": "08:00", "wellness_dias": [1, 2, 3, 4, 5]}


def obter_config(team_id: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select wellness_auto, wellness_hora, wellness_dias from config_mensagens where team_id = %s", (team_id,))
            row = cur.fetchone()
    if not row:
        return dict(CONFIG_PADRAO)
    return {"wellness_auto": bool(row[0]), "wellness_hora": row[1], "wellness_dias": list(row[2] or [])}


def guardar_config(team_id: str, wellness_auto: bool, wellness_hora: str, wellness_dias: list[int]) -> dict:
    try:
        h, m = (int(x) for x in str(wellness_hora).split(":"))
        assert 0 <= h < 24 and 0 <= m < 60
    except Exception:
        raise ValueError("Hora inválida — usa o formato HH:MM.")
    hora = f"{h:02d}:{m:02d}"
    dias = sorted({int(d) for d in wellness_dias if 1 <= int(d) <= 7})
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into config_mensagens (team_id, wellness_auto, wellness_hora, wellness_dias)
                values (%s, %s, %s, %s)
                on conflict (team_id) do update set wellness_auto = excluded.wellness_auto,
                    wellness_hora = excluded.wellness_hora, wellness_dias = excluded.wellness_dias,
                    atualizado_em = now()
                """,
                (team_id, bool(wellness_auto), hora, dias),
            )
    return {"wellness_auto": bool(wellness_auto), "wellness_hora": hora, "wellness_dias": dias}


# ── Jogadores ────────────────────────────────────────────────────────────────
def listar_contactos(team_id: str) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, nome, posicao, estado, telefone, consentimento_mensagens_em
                from players where team_id = %s and ativo order by nome
                """,
                (team_id,),
            )
            linhas = cur.fetchall()
    out = []
    for pid, nome, pos, estado, tel, consent in linhas:
        valido = whatsapp_service.normalizar_telefone(tel)
        motivo = None
        if not tel:
            motivo = "sem telefone"
        elif not valido:
            motivo = "telefone inválido"
        elif not consent:
            motivo = "sem consentimento registado"
        out.append({
            "player_id": str(pid), "nome": nome, "posicao": pos, "estado": estado,
            "telefone": tel, "consentimento_em": consent.isoformat() if consent else None,
            "pode_receber": motivo is None, "motivo": motivo,
        })
    return out


def guardar_contacto(team_id: str, player_id: str, telefone: str | None, consentimento: bool) -> dict:
    tel = (telefone or "").strip() or None
    if tel and not whatsapp_service.normalizar_telefone(tel):
        raise ValueError("Número inválido. Usa o formato +351 912 345 678.")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update players set telefone = %s,
                    consentimento_mensagens_em = case
                        when %s then coalesce(consentimento_mensagens_em, current_date) else null end
                where id = %s and team_id = %s
                returning id
                """,
                (whatsapp_service.normalizar_telefone(tel) if tel else None, bool(consentimento), player_id, team_id),
            )
            ok = cur.fetchone() is not None
    return {"ok": ok}


# ── Envio ────────────────────────────────────────────────────────────────────
def enviar_pedidos(team_id: str, tipo: str, dia: date, player_ids: list[str] | None = None,
                   duracao_min: float | None = None, reenviar: bool = False) -> dict:
    """Cria (ou reutiliza) o pedido de cada jogador e envia a mensagem.

    Um jogador que já tem pedido deste tipo para este dia não recebe outra vez,
    a não ser com `reenviar` (e nunca depois de ter respondido)."""
    if tipo not in VALIDADE:
        raise ValueError("Tipo de pedido inválido.")
    contactos = listar_contactos(team_id)
    if player_ids is not None:
        escolhidos = set(player_ids)
        contactos = [c for c in contactos if c["player_id"] in escolhidos]
    usar_twilio = whatsapp_service.configurado()
    s = get_settings()
    template = s.twilio_template_wellness if tipo == "wellness" else s.twilio_template_pse
    expira = agora() + VALIDADE[tipo]
    resumo = {"enviados": 0, "simulados": 0, "erros": 0, "ja_enviados": 0, "ignorados": [], "modo": "whatsapp" if usar_twilio else "simulacao"}

    for c in contactos:
        if not c["pode_receber"]:
            resumo["ignorados"].append({"nome": c["nome"], "motivo": c["motivo"]})
            continue
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into pedidos_resposta (team_id, player_id, tipo, data, token, duracao_min, expira_em)
                    values (%s, %s, %s, %s, %s, %s, %s)
                    on conflict (team_id, player_id, tipo, data) do update set
                        duracao_min = coalesce(excluded.duracao_min, pedidos_resposta.duracao_min),
                        expira_em = greatest(excluded.expira_em, pedidos_resposta.expira_em)
                    returning id, token, estado_envio, respondido_em, (xmax = 0) as novo
                    """,
                    (team_id, c["player_id"], tipo, dia, secrets.token_urlsafe(24), duracao_min, expira),
                )
                pid, token, estado, respondido, novo = cur.fetchone()
        if not novo and (respondido or (not reenviar and estado in ("enviado", "simulado"))):
            resumo["ja_enviados"] += 1
            continue

        link = link_pedido(token)
        if usar_twilio:
            ok, erro = whatsapp_service.enviar(
                c["telefone"], texto_mensagem(tipo, c["nome"], link),
                template_sid=template or None, variaveis={"1": primeiro_nome(c["nome"]), "2": link},
            )
            novo_estado = "enviado" if ok else "erro"
        else:
            ok, erro, novo_estado = True, None, "simulado"
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "update pedidos_resposta set estado_envio = %s, erro = %s, enviado_em = now() where id = %s",
                    (novo_estado, erro, pid),
                )
        resumo["enviados" if novo_estado == "enviado" else "simulados" if novo_estado == "simulado" else "erros"] += 1
    return resumo


def estado_do_dia(team_id: str, dia: date) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select r.tipo, p.nome, r.token, r.estado_envio, r.erro, r.enviado_em, r.respondido_em, r.expira_em, p.telefone
                from pedidos_resposta r join players p on p.id = r.player_id
                where r.team_id = %s and r.data = %s order by p.nome
                """,
                (team_id, dia),
            )
            linhas = cur.fetchall()
    agora_ = agora()
    por_tipo: dict[str, list] = {"wellness": [], "pse": []}
    for tipo, nome, token, estado, erro, enviado, respondido, expira, telefone in linhas:
        link = link_pedido(token)
        por_tipo[tipo].append({
            "nome": nome, "estado_envio": estado, "erro": erro,
            "enviado_em": enviado.isoformat() if enviado else None,
            "respondido": respondido is not None,
            "expirado": expira < agora_ and respondido is None,
            "link": link,
            "token": token,
            "whatsapp": link_whatsapp(telefone, texto_mensagem(tipo, nome, link)),
        })
    return {
        tipo: {"pedidos": lista, "respondidos": sum(1 for x in lista if x["respondido"]), "total": len(lista)}
        for tipo, lista in por_tipo.items()
    }


def marcar_enviado(team_id: str, token: str) -> dict:
    """Envio manual (WhatsApp com 1 toque): regista que a mensagem foi aberta
    para envio, para a lista de hoje mostrar quem já recebeu."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update pedidos_resposta set estado_envio = 'manual', enviado_em = now()
                where team_id = %s and token = %s and estado_envio <> 'enviado'
                returning id
                """,
                (team_id, token),
            )
            return {"ok": cur.fetchone() is not None}


# ── Envio automático (agendador) ─────────────────────────────────────────────
def envio_automatico(momento: datetime | None = None) -> dict:
    """Chamado pelo agendador várias vezes por manhã. Envia o bem-estar às
    equipas com envio automático ligado, em dia escolhido, depois da hora
    definida — uma vez por jogador e por dia (o pedido existente impede
    duplicados)."""
    momento = (momento or agora()).astimezone(FUSO)
    hhmm = momento.strftime("%H:%M")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select team_id, wellness_hora, wellness_dias from config_mensagens where wellness_auto",
            )
            equipas = cur.fetchall()
    resultados = []
    for team_id, hora, dias in equipas:
        if momento.isoweekday() not in (dias or []) or hhmm < hora:
            continue
        r = enviar_pedidos(str(team_id), "wellness", momento.date())
        resultados.append({"team_id": str(team_id), **{k: v for k, v in r.items() if k != "ignorados"}})
    return {"momento": momento.isoformat(), "equipas": resultados}


# ── Resposta do jogador (público, por token) ─────────────────────────────────
def _pedido(token: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select r.id, r.team_id, r.player_id, r.tipo, r.data, r.duracao_min, r.respondido_em, r.expira_em, p.nome
                from pedidos_resposta r join players p on p.id = r.player_id
                where r.token = %s
                """,
                (token,),
            )
            return cur.fetchone()


def obter_pedido_publico(token: str) -> dict | None:
    row = _pedido(token) if token and len(token) >= 16 else None
    if not row:
        return None
    _, _, _, tipo, dia, _, respondido, expira, nome = row
    return {
        "tipo": tipo, "data": dia.isoformat(), "nome": primeiro_nome(nome),
        "respondido": respondido is not None, "expirado": expira < agora(),
    }


def _inteiro(v, minimo: int, maximo: int) -> int:
    try:
        n = int(round(float(v)))
    except (TypeError, ValueError):
        raise ValueError("Resposta inválida.")
    if not minimo <= n <= maximo:
        raise ValueError(f"Os valores têm de estar entre {minimo} e {maximo}.")
    return n


def responder(token: str, respostas: dict) -> dict:
    row = _pedido(token) if token and len(token) >= 16 else None
    if not row:
        raise LookupError("Link inválido.")
    pedido_id, team_id, player_id, tipo, dia, duracao, _, expira, _ = row
    if expira < agora():
        raise PermissionError("Este link já expirou.")

    if tipo == "wellness":
        from app.services.wellness_service import registar_wellness
        valores = {k: _inteiro(respostas.get(k), 1, 5) for k in ("sono", "dor_musc", "stress", "humor")}
        registar_wellness(str(team_id), str(player_id), dia.isoformat(), **valores, notas=respostas.get("notas"))
    else:
        pse = _inteiro(respostas.get("pse"), 0, 10)
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into gps_sessions (team_id, player_id, data, tipo, pse_sessao, duracao_min, carga_interna)
                    values (%s, %s, %s, 'Treino', %s, %s, %s * %s)
                    on conflict (team_id, player_id, data, tipo) do update set
                        pse_sessao = excluded.pse_sessao,
                        duracao_min = coalesce(gps_sessions.duracao_min, excluded.duracao_min),
                        carga_interna = excluded.pse_sessao * coalesce(gps_sessions.duracao_min, excluded.duracao_min)
                    """,
                    (team_id, player_id, dia, pse, duracao, pse, duracao),
                )
        invalidar_cache_equipa(str(team_id))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("update pedidos_resposta set respondido_em = now() where id = %s", (pedido_id,))
    return {"ok": True}
