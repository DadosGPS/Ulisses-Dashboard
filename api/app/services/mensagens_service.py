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

import json
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


# Fusos que se podem escolher por equipa (as horas de envio são locais).
FUSOS = ["Europe/Lisbon", "Europe/Stockholm", "Europe/Madrid", "Europe/London", "Atlantic/Azores", "America/Sao_Paulo"]


def agora(fuso: str | None = None) -> datetime:
    try:
        return datetime.now(ZoneInfo(fuso)) if fuso else datetime.now(FUSO)
    except Exception:
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
CONFIG_PADRAO = {
    "wellness_auto": False, "wellness_hora": "08:00", "wellness_dias": [1, 2, 3, 4, 5],
    "pse_auto": False, "pse_hora": "19:30", "lembrete_auto": False, "lembrete_apos_min": 120,
    "fuso": "Europe/Lisbon", "rotina_disponivel": False,
}
_COLS_ROTINA = "pse_auto, pse_hora, lembrete_auto, lembrete_apos_min, fuso"


def _hora(valor: str) -> str:
    try:
        h, m = (int(x) for x in str(valor).split(":"))
        assert 0 <= h < 24 and 0 <= m < 60
    except Exception:
        raise ValueError("Hora inválida — usa o formato HH:MM.")
    return f"{h:02d}:{m:02d}"


def _tem_rotina(cur) -> bool:
    """Colunas da migração 0020 (PSE automática, lembretes, fuso)."""
    cur.execute("select exists (select 1 from information_schema.columns where table_name = 'config_mensagens' and column_name = 'fuso')")
    row = cur.fetchone()
    return bool(row and row[0])


def _linha_config(row, rotina: bool) -> dict:
    cfg = {**CONFIG_PADRAO, "wellness_auto": bool(row[0]), "wellness_hora": row[1], "wellness_dias": list(row[2] or []),
           "rotina_disponivel": rotina}
    if rotina:
        cfg.update({"pse_auto": bool(row[3]), "pse_hora": row[4], "lembrete_auto": bool(row[5]),
                    "lembrete_apos_min": int(row[6]), "fuso": row[7]})
    return cfg


def obter_config(team_id: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            rotina = _tem_rotina(cur)
            cols = "wellness_auto, wellness_hora, wellness_dias" + (f", {_COLS_ROTINA}" if rotina else "")
            cur.execute(f"select {cols} from config_mensagens where team_id = %s", (team_id,))
            row = cur.fetchone()
    if not row:
        return {**CONFIG_PADRAO, "rotina_disponivel": rotina}
    return _linha_config(row, rotina)


def guardar_config(team_id: str, wellness_auto: bool, wellness_hora: str, wellness_dias: list[int],
                   pse_auto: bool | None = None, pse_hora: str | None = None, lembrete_auto: bool | None = None,
                   lembrete_apos_min: int | None = None, fuso: str | None = None) -> dict:
    hora = _hora(wellness_hora)
    dias = sorted({int(d) for d in wellness_dias if 1 <= int(d) <= 7})
    atual = obter_config(team_id)
    novo = {**atual, "wellness_auto": bool(wellness_auto), "wellness_hora": hora, "wellness_dias": dias}
    if pse_auto is not None:
        novo["pse_auto"] = bool(pse_auto)
    if pse_hora is not None:
        novo["pse_hora"] = _hora(pse_hora)
    if lembrete_auto is not None:
        novo["lembrete_auto"] = bool(lembrete_auto)
    if lembrete_apos_min is not None:
        if not 15 <= int(lembrete_apos_min) <= 720:
            raise ValueError("O lembrete vai de 15 minutos a 12 horas depois do envio.")
        novo["lembrete_apos_min"] = int(lembrete_apos_min)
    if fuso is not None:
        if fuso not in FUSOS:
            raise ValueError("Fuso horário inválido.")
        novo["fuso"] = fuso
    with get_conn() as conn:
        with conn.cursor() as cur:
            if atual["rotina_disponivel"]:
                cur.execute(
                    f"""
                    insert into config_mensagens (team_id, wellness_auto, wellness_hora, wellness_dias, {_COLS_ROTINA})
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (team_id) do update set wellness_auto = excluded.wellness_auto,
                        wellness_hora = excluded.wellness_hora, wellness_dias = excluded.wellness_dias,
                        pse_auto = excluded.pse_auto, pse_hora = excluded.pse_hora,
                        lembrete_auto = excluded.lembrete_auto, lembrete_apos_min = excluded.lembrete_apos_min,
                        fuso = excluded.fuso, atualizado_em = now()
                    """,
                    (team_id, novo["wellness_auto"], hora, dias, novo["pse_auto"], novo["pse_hora"],
                     novo["lembrete_auto"], novo["lembrete_apos_min"], novo["fuso"]),
                )
            else:
                cur.execute(
                    """
                    insert into config_mensagens (team_id, wellness_auto, wellness_hora, wellness_dias)
                    values (%s, %s, %s, %s)
                    on conflict (team_id) do update set wellness_auto = excluded.wellness_auto,
                        wellness_hora = excluded.wellness_hora, wellness_dias = excluded.wellness_dias,
                        atualizado_em = now()
                    """,
                    (team_id, novo["wellness_auto"], hora, dias),
                )
    return novo


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
def sessao_do_dia(team_id: str, dia: date) -> dict | None:
    """Há sessão neste dia? Pelo plano do microciclo (Treino/Jogo) ou, sem
    plano, por já haver dados GPS. Devolve {"tipo": "Treino"|"Jogo", "origem"}."""
    chave = dia.isoformat()
    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "select dias from microciclos where team_id = %s and data_inicio <= %s and data_fim >= %s",
                    (team_id, dia, dia),
                )
                for (dias,) in cur.fetchall():
                    if isinstance(dias, str):
                        dias = json.loads(dias or "{}")
                    d = (dias or {}).get(chave) if isinstance(dias, dict) else None
                    if d and d.get("tipo") in ("Treino", "Jogo"):
                        return {"tipo": d["tipo"], "origem": "plano"}
                    if d and d.get("tipo") == "Folga":
                        return None
            except Exception:
                conn.rollback()
            cur.execute("select tipo from gps_sessions where team_id = %s and data = %s limit 1", (team_id, dia))
            row = cur.fetchone()
    return {"tipo": row[0] or "Treino", "origem": "gps"} if row else None


def pendentes_para_lembrete(team_id: str, dia: date, apos_min: int, momento: datetime) -> dict[str, list[str]]:
    """Jogadores com pedido enviado há mais de `apos_min` minutos, sem resposta,
    ainda válido e sem lembrete — por tipo."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select tipo, player_id::text from pedidos_resposta
                where team_id = %s and data = %s and respondido_em is null and lembrete_em is null
                  and estado_envio = 'enviado' and expira_em > %s and enviado_em <= %s
                """,
                (team_id, dia, momento, momento - timedelta(minutes=apos_min)),
            )
            out: dict[str, list[str]] = {}
            for tipo, pid in cur.fetchall():
                out.setdefault(tipo, []).append(pid)
    return out


def _marcar_lembrete(team_id: str, dia: date, tipo: str, player_ids: list[str]) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "update pedidos_resposta set lembrete_em = now() where team_id = %s and data = %s and tipo = %s and player_id = any(%s::uuid[])",
                (team_id, dia, tipo, player_ids),
            )


def decidir_envios(cfg: dict, momento: datetime, tem_sessao: bool) -> list[str]:
    """Que envios automáticos tocam agora a esta equipa (cálculo puro)."""
    hhmm = momento.strftime("%H:%M")
    out = []
    if cfg.get("wellness_auto") and momento.isoweekday() in (cfg.get("wellness_dias") or []) and hhmm >= cfg["wellness_hora"]:
        out.append("wellness")
    if cfg.get("pse_auto") and tem_sessao and hhmm >= cfg.get("pse_hora", "23:59"):
        out.append("pse")
    return out


def envio_automatico(momento: datetime | None = None) -> dict:
    """Chamado pelo agendador de 15 em 15 minutos. Para cada equipa com envio
    automático: bem-estar de manhã nos dias escolhidos, PSE depois da hora
    definida nos dias com sessão, e um lembrete a quem ainda não respondeu.
    Cada jogador recebe cada pedido uma só vez por dia (o pedido existente
    impede duplicados) e no máximo um lembrete."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            rotina = _tem_rotina(cur)
            if rotina:
                cur.execute(f"""select team_id, wellness_auto, wellness_hora, wellness_dias, {_COLS_ROTINA} from config_mensagens
                                where wellness_auto or pse_auto or lembrete_auto""")
            else:
                cur.execute("select team_id, wellness_auto, wellness_hora, wellness_dias from config_mensagens where wellness_auto")
            equipas = [(str(r[0]), _linha_config(r[1:], rotina)) for r in cur.fetchall()]
    resultados = []
    for team_id, cfg in equipas:
        local = (momento or agora(cfg["fuso"])).astimezone(ZoneInfo(cfg["fuso"]))
        dia = local.date()
        sessao = sessao_do_dia(team_id, dia) if cfg.get("pse_auto") else None
        feito: dict = {"team_id": team_id}
        for tipo in decidir_envios(cfg, local, sessao is not None):
            r = enviar_pedidos(team_id, tipo, dia)
            feito[tipo] = {k: v for k, v in r.items() if k != "ignorados"}
        if cfg.get("lembrete_auto") and whatsapp_service.configurado():
            for tipo, ids in pendentes_para_lembrete(team_id, dia, cfg["lembrete_apos_min"], local).items():
                r = enviar_pedidos(team_id, tipo, dia, ids, reenviar=True)
                _marcar_lembrete(team_id, dia, tipo, ids)
                feito[f"lembrete_{tipo}"] = r["enviados"]
        if len(feito) > 1:
            resultados.append(feito)
    return {"momento": (momento or agora()).isoformat(), "equipas": resultados}


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
                # A PSE vai para a sessão de campo que já existe nesse dia (o
                # jogo, se houver; nunca a do ginásio, que tem PSE própria no
                # módulo de força); sem sessão, para a do plano — por defeito Treino.
                cur.execute("select tipo from gps_sessions where player_id = %s and data = %s and tipo <> 'Ginásio' "
                            "order by (tipo = 'Jogo') desc limit 1", (player_id, dia))
                row_t = cur.fetchone()
                tipo_sessao = row_t[0] if row_t else ((sessao_do_dia(str(team_id), dia) or {}).get("tipo") or "Treino")
                cur.execute(
                    """
                    insert into gps_sessions (team_id, player_id, data, tipo, pse_sessao, duracao_min, carga_interna)
                    values (%s, %s, %s, %s, %s, %s, %s * %s)
                    on conflict (team_id, player_id, data, tipo) do update set
                        pse_sessao = excluded.pse_sessao,
                        duracao_min = coalesce(gps_sessions.duracao_min, excluded.duracao_min),
                        carga_interna = excluded.pse_sessao * coalesce(gps_sessions.duracao_min, excluded.duracao_min)
                    """,
                    (team_id, player_id, dia, tipo_sessao, pse, duracao, pse, duracao),
                )
        invalidar_cache_equipa(str(team_id))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("update pedidos_resposta set respondido_em = now() where id = %s", (pedido_id,))
    return {"ok": True}
