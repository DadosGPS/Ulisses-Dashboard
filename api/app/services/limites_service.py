"""Limiares de alerta configuráveis (guardados em profiles.settings.limites).

Os alertas do dashboard usam estes limiares; se o utilizador não tiver
definido nada, aplicam-se os valores por omissão (os mesmos que estavam
fixos no código). Cada métrica tem um limiar de "atenção" e outro de
"atenção alta".
"""
from __future__ import annotations

import json

from app.core.db import get_conn

DEFAULTS: dict[str, float] = {
    "acwr_alto": 1.3,
    "acwr_muito_alto": 1.5,
    "carga_change_alto": 30.0,
    "carga_change_muito_alto": 50.0,
    "wellness_change_alto": 10.0,
    "wellness_change_muito_alto": 20.0,
    "hsr_change_alto": 25.0,
    "hsr_change_muito_alto": 40.0,
    "velocidade_queda_alto": 8.0,
    "velocidade_queda_muito_alto": 12.0,
    "dados_horas": 48.0,
    # Sinais da página Análise (antes fixos no código, agora configuráveis e
    # partilhados pelo mesmo motor de alertas). Os defaults são exatamente os
    # valores que estavam escritos à mão em analise_service._calcular_alertas,
    # por isso o comportamento por omissão mantém-se inalterado.
    "hooper_alto": 12.0,                  # Hooper Index (absoluto, 0–16) → wellness muito baixo (14 quase nunca disparava)
    "dias_sem_dados": 7.0,                # dias sem sessão registada (jogador apto)
    "velocidade_queda_sustentada": 10.0,  # % abaixo do recorde da época (média das últimas 3)
    # Exposição HSR/Sprint da SEMANA (carga acumulada do microciclo) face ao
    # jogo mais exigente. Zonas de referência (Buchheit): abaixo de «baixo» é
    # exposição baixa, acima de «alto» é elevada. Configuráveis por contexto.
    "hsr_semana_baixo": 0.60,
    "hsr_semana_alto": 0.90,
    "sprint_semana_baixo": 0.60,
    "sprint_semana_alto": 0.90,
    # Prontidão: queda do CMJ (altura de salto) face à média dos testes
    # anteriores do PRÓPRIO jogador, e subida do Hooper (0–16, alto = pior)
    # face à sua média dos últimos 28 dias.
    "cmj_queda_alto": 5.0,
    "cmj_queda_muito_alto": 10.0,
    "hooper_subida_alto": 3.0,
    "hooper_subida_muito_alto": 5.0,
}


def _settings(user_id: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select settings from profiles where id = %s", (user_id,))
            row = cur.fetchone()
    if not row or not row[0]:
        return {}
    val = row[0]
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return {}
    return val if isinstance(val, dict) else {}


def obter_limites(user_id: str) -> dict:
    guardados = _settings(user_id).get("limites") or {}
    lim = dict(DEFAULTS)
    for k, v in guardados.items():
        if k in DEFAULTS:
            try:
                lim[k] = float(v)
            except (TypeError, ValueError):
                pass
    return lim


def guardar_limites(user_id: str, novos: dict) -> dict:
    lim = dict(DEFAULTS)
    for k, v in (novos or {}).items():
        if k in DEFAULTS:
            try:
                lim[k] = float(v)
            except (TypeError, ValueError):
                pass
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "update profiles set settings = jsonb_set(coalesce(settings, '{}'::jsonb), '{limites}', %s::jsonb) where id = %s returning 1",
                (json.dumps(lim), user_id),
            )
            ok = cur.fetchone()
    return lim if ok else lim


# ── Protocolo da academia ────────────────────────────────────────────────────
# Com o protocolo ativo, todas as equipas da academia usam os mesmos limiares
# (com exceções por escalão, ex.: Sub-13), em vez dos limites pessoais de quem
# abre a página. Sem isso, dois PF com limiares diferentes davam «jogadores em
# alerta» impossíveis de comparar ou somar.
MSG_PROTOCOLO = ("Os limites desta equipa seguem o protocolo da academia. "
                 "Só o responsável da academia os pode alterar.")


def _limpar(valores: dict | None) -> dict[str, float]:
    out: dict[str, float] = {}
    for k, v in (valores or {}).items():
        if k in DEFAULTS:
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                pass
    return out


def resolver(pessoais: dict | None, protocolo: dict | None, escalao: str | None) -> tuple[dict, dict]:
    """Limiares efetivos de uma equipa (parte pura). Devolve (limites, origem)."""
    prot = protocolo or {}
    if prot.get("ativo"):
        excecao = _limpar((prot.get("escaloes") or {}).get(escalao or "", {}))
        lim = {**DEFAULTS, **_limpar(prot.get("base")), **excecao}
        return lim, {"tipo": "academia", "escalao": escalao, "excecao_escalao": bool(excecao)}
    return {**DEFAULTS, **_limpar(pessoais)}, {"tipo": "pessoal", "escalao": escalao, "excecao_escalao": False}


def _contexto(cur, team_id: str, user_id: str) -> dict:
    """Academia, escalão, protocolo e papel do utilizador para esta equipa.
    Sem a migração 0022 (ou sem academia) → protocolo vazio."""
    try:
        cur.execute(
            """
            select t.academia_id, t.escalao, a.protocolo,
                   (select am.papel from academia_membros am where am.academia_id = t.academia_id and am.user_id = %s)
            from teams t left join academias a on a.id = t.academia_id
            where t.id = %s
            """,
            (user_id, team_id),
        )
        row = cur.fetchone()
    except Exception:
        cur.connection.rollback()
        row = None
    if not row:
        return {"academia_id": None, "escalao": None, "protocolo": {}, "papel": None}
    aid, esc, prot, papel = row
    if isinstance(prot, str):
        prot = json.loads(prot or "{}")
    return {"academia_id": str(aid) if aid else None, "escalao": esc, "protocolo": prot or {}, "papel": papel}


def obter_limites_equipa(team_id: str, user_id: str) -> dict:
    """Limiares que os alertas desta equipa devem usar (protocolo ou pessoais)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            ctx = _contexto(cur, team_id, user_id)
    lim, _ = resolver(_settings(user_id).get("limites"), ctx["protocolo"], ctx["escalao"])
    return lim


def origem_limites(team_id: str, user_id: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            ctx = _contexto(cur, team_id, user_id)
    _, origem = resolver(_settings(user_id).get("limites"), ctx["protocolo"], ctx["escalao"])
    return {**origem, "academia_id": ctx["academia_id"], "e_head": ctx["papel"] == "head",
            "protocolo_ativo": bool(ctx["protocolo"].get("ativo"))}


def guardar_limites_equipa(team_id: str, user_id: str, novos: dict, ambito: str | None = None) -> dict:
    """Guarda limiares a partir da página de uma equipa. Sem protocolo: nos
    limites pessoais. Com protocolo: só o responsável, na base (todas as
    equipas) ou, com ambito='escalao', só no escalão desta equipa."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            ctx = _contexto(cur, team_id, user_id)
            prot = dict(ctx["protocolo"] or {})
            if not prot.get("ativo"):
                pass
            elif ctx["papel"] != "head":
                raise PermissionError(MSG_PROTOCOLO)
            else:
                valores = _limpar(novos)
                if ambito == "escalao" and ctx["escalao"]:
                    esc = dict(prot.get("escaloes") or {})
                    esc[ctx["escalao"]] = valores
                    prot["escaloes"] = esc
                else:
                    prot["base"] = valores
                cur.execute("update academias set protocolo = %s::jsonb where id = %s", (json.dumps(prot), ctx["academia_id"]))
                lim, _ = resolver(None, prot, ctx["escalao"])
                return lim
    guardar_limites(user_id, novos)
    return obter_limites_equipa(team_id, user_id)


def definir_protocolo(academia_id: str, user_id: str, ativo: bool, limpar_escalao: str | None = None) -> dict:
    """Liga/desliga o protocolo (só o responsável). Ao ligar pela primeira vez,
    a base são os limites atuais de quem o liga. `limpar_escalao` remove a
    exceção desse escalão (volta à base)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select papel from academia_membros where academia_id = %s and user_id = %s", (academia_id, user_id))
            row = cur.fetchone()
            if not row or row[0] != "head":
                raise PermissionError("Só o responsável da academia pode alterar o protocolo.")
            cur.execute("select protocolo from academias where id = %s", (academia_id,))
            prot = cur.fetchone()[0] or {}
            if isinstance(prot, str):
                prot = json.loads(prot or "{}")
            prot = dict(prot)
            prot["ativo"] = bool(ativo)
            if ativo and not prot.get("base"):
                prot["base"] = {**DEFAULTS, **_limpar(_settings(user_id).get("limites"))}
            if limpar_escalao:
                esc = dict(prot.get("escaloes") or {})
                esc.pop(limpar_escalao, None)
                prot["escaloes"] = esc
            cur.execute("update academias set protocolo = %s::jsonb where id = %s", (json.dumps(prot), academia_id))
    return obter_protocolo(academia_id, user_id)


def obter_protocolo(academia_id: str, user_id: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select papel from academia_membros where academia_id = %s and user_id = %s", (academia_id, user_id))
            row = cur.fetchone()
            if not row:
                raise PermissionError("Não pertences a esta academia.")
            try:
                cur.execute("select protocolo from academias where id = %s", (academia_id,))
                prot = cur.fetchone()[0] or {}
            except Exception:
                cur.connection.rollback()
                prot = {}
    if isinstance(prot, str):
        prot = json.loads(prot or "{}")
    return {"ativo": bool(prot.get("ativo")), "base": {**DEFAULTS, **_limpar(prot.get("base"))},
            "escaloes": {k: _limpar(v) for k, v in (prot.get("escaloes") or {}).items()},
            "e_head": row[0] == "head"}
