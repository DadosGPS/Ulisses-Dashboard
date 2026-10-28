"""Regresso ao jogo (return-to-play) — planos por etapas, avaliados
automaticamente a partir do GPS.

Cada etapa define metas POR SESSÃO em % da referência de jogo do jogador
ANTES da lesão (média por 90' dos últimos jogos completos — ver
referencia_jogo; a velocidade máxima usa o recorde pré-lesão). Uma etapa fica
cumprida quando `sessoes_por_etapa` sessões, depois de concluída a anterior,
atingem TODAS as metas definidas dessa etapa. As etapas avançam por ordem:
uma sessão que já cumpriria uma etapa posterior só conta para a atual.
"""
from __future__ import annotations

import json

import pandas as pd

from app.core.db import get_conn
from app.services.referencia_jogo import mascara_jogo, referencias_jogo
from utils.calculos import recorde_vmax

METRICAS_RTP = [
    # chave na etapa, coluna, rótulo, é pico?
    ("pct_distancia", "Distância Total (m)", "Distância", False),
    ("pct_hsr", "HSR (m)", "HSR", False),
    ("pct_sprint", "Sprint (m)", "Sprint", False),
    ("pct_vmax", "Vel. Máx (km/h)", "Vel. máx", True),
]

# Progressão por omissão (editável em cada plano). Valores por sessão, em % da
# referência de jogo pré-lesão; None = esta métrica não é exigida na etapa.
# Critérios clínicos por etapa: marcados pelo staff (fisioterapia / PF). Uma
# etapa só fica cumprida quando as metas de GPS E todos os critérios estão
# cumpridos — o GPS diz que o jogador aguentou a carga, não que está pronto.
ETAPAS_PADRAO = [
    {"nome": "Reintegração", "pct_distancia": 50, "pct_hsr": 30, "pct_sprint": None, "pct_vmax": None,
     "criterios": [{"texto": "Sem dor nas atividades do dia a dia", "cumprido": False},
                   {"texto": "Amplitude articular completa", "cumprido": False}]},
    {"nome": "Volume", "pct_distancia": 75, "pct_hsr": 50, "pct_sprint": 30, "pct_vmax": 80,
     "criterios": [{"texto": "Dor ≤ 2/10 durante e depois da sessão", "cumprido": False},
                   {"texto": "Força ≥ 80 % do lado são (ou da avaliação pré-lesão)", "cumprido": False}]},
    {"nome": "Intensidade", "pct_distancia": 90, "pct_hsr": 75, "pct_sprint": 60, "pct_vmax": 90,
     "criterios": [{"texto": "Força ≥ 90 % do lado são", "cumprido": False},
                   {"texto": "Assimetria no salto (CMJ / unipodal) < 10 %", "cumprido": False}]},
    {"nome": "Exigência de jogo", "pct_distancia": 100, "pct_hsr": 100, "pct_sprint": 90, "pct_vmax": 95,
     "criterios": [{"texto": "Força ≥ 95 % do lado são", "cumprido": False},
                   {"texto": "Treino completo com a equipa sem limitações", "cumprido": False},
                   {"texto": "Alta do departamento médico e confiança do jogador", "cumprido": False}]},
]
# Resposta à carga: uma sessão só conta se, no dia seguinte, o Hooper não
# subir HOOPER_RESPOSTA pontos ou mais acima da média do jogador antes do plano.
HOOPER_RESPOSTA = 3.0
SESSOES_POR_ETAPA = 2

MSG_MIGRACAO = (
    "A tabela dos planos de regresso ao jogo ainda não existe. Aplica a migração "
    "supabase/migrations/0007_planos_rtp.sql no SQL Editor do Supabase."
)


def _limpar_etapas(etapas: list[dict] | None) -> list[dict]:
    limpas = []
    for i, e in enumerate(etapas or []):
        nova = {"nome": str(e.get("nome") or f"Etapa {i + 1}")[:60]}
        for chave, *_ in METRICAS_RTP:
            v = e.get(chave)
            try:
                nova[chave] = None if v in (None, "") else max(0.0, min(200.0, float(v)))
            except (TypeError, ValueError):
                nova[chave] = None
        if e.get("notas"):
            nova["notas"] = str(e["notas"])[:300]
        criterios = []
        for c in (e.get("criterios") or [])[:8]:
            texto = str((c or {}).get("texto") or "").strip()[:120]
            if texto:
                criterios.append({"texto": texto, "cumprido": bool(c.get("cumprido"))})
        nova["criterios"] = criterios
        limpas.append(nova)
    return limpas


def _referencias_pre_lesao(df: pd.DataFrame, jogador: str, inicio: pd.Timestamp) -> dict[str, dict]:
    """Referência de jogo de cada métrica com os dados ANTERIORES ao início do
    plano (jogador sem jogos completos → mediana da posição)."""
    antes = df[df["Data"] < inicio]
    jogos = antes[mascara_jogo(antes)]
    pos = antes.loc[antes["Jogador"] == jogador, "Posição"].dropna() if "Posição" in antes.columns else pd.Series(dtype=object)
    alvo = {jogador: pos.iloc[-1] if not pos.empty and isinstance(pos.iloc[-1], str) else ""}
    refs: dict[str, dict] = {}
    for chave, col, _, pico in METRICAS_RTP:
        if col not in antes.columns:
            continue
        if pico:  # recorde pré-lesão em qualquer sessão
            serie = antes.loc[antes["Jogador"] == jogador, col].dropna()
            rec = recorde_vmax(serie)
            if rec:
                refs[chave] = {"valor": rec, "fonte": "recorde"}
            continue
        r = referencias_jogo(jogos, col, jogadores=alvo).get(jogador)
        if r and r["valor"] > 0:
            refs[chave] = {"valor": r["valor"], "fonte": r["fonte"]}
    return refs


def avaliar_plano(df: pd.DataFrame, jogador: str, data_inicio: str, etapas: list[dict],
                  sessoes_por_etapa: int = SESSOES_POR_ETAPA) -> dict:
    """Parte pura (testável): progresso do plano a partir das sessões."""
    etapas = _limpar_etapas(etapas)
    vazio_ref = {"referencias": {}, "sessoes": [], "etapas": [], "etapa_atual": None, "concluido": False, "progresso_pct": 0}
    if df is None or df.empty or "Jogador" not in df.columns or not etapas:
        return {**vazio_ref, "etapas": [{**e, "estado": "pendente"} for e in etapas]}
    df = df.copy()
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    inicio = pd.Timestamp(data_inicio)
    refs = _referencias_pre_lesao(df, jogador, inicio)

    sess = df[(df["Jogador"] == jogador) & (df["Data"] >= inicio)].sort_values("Data")
    cols = [c for _, c, _, _ in METRICAS_RTP if c in sess.columns]
    if cols:
        sess = sess.dropna(subset=cols, how="all")
    e_jogo = mascara_jogo(sess) if not sess.empty else pd.Series(dtype=bool)

    def pcts(row) -> dict[str, float | None]:
        out = {}
        for chave, col, _, _ in METRICAS_RTP:
            ref = refs.get(chave)
            v = row.get(col)
            out[chave] = round(float(v) / ref["valor"] * 100, 0) if ref and pd.notna(v) else None
        return out

    def cumpre(p: dict, etapa: dict) -> bool:
        metas = [(k, etapa[k]) for k, *_ in METRICAS_RTP if etapa.get(k) is not None]
        return bool(metas) and all(p.get(k) is not None and p[k] >= meta for k, meta in metas)

    # Wellness do jogador: média antes do plano e Hooper de cada dia, para a
    # resposta no dia seguinte a cada sessão.
    hooper_dia: dict = {}
    hooper_base = None
    if "Hooper Index" in df.columns:
        h = df[(df["Jogador"] == jogador)].dropna(subset=["Hooper Index", "Data"])
        antes = h[(h["Data"] < inicio) & (h["Data"] >= inicio - pd.Timedelta(days=28))]["Hooper Index"]
        hooper_base = float(antes.mean()) if not antes.empty else None
        hooper_dia = h.groupby(h["Data"].dt.normalize())["Hooper Index"].max().to_dict()

    def resposta(dia: pd.Timestamp) -> str | None:
        """'ok' | 'negativa' | None (sem wellness no dia seguinte)."""
        seguinte = hooper_dia.get(dia.normalize() + pd.Timedelta(days=1))
        if seguinte is None or hooper_base is None:
            return None
        return "negativa" if float(seguinte) - hooper_base >= HOOPER_RESPOSTA else "ok"

    estado_etapas = [{**e, "estado": "pendente", "sessoes_cumpridas": 0, "data_conclusao": None, "gps_cumprido": False,
                      "melhor": {k: None for k, *_ in METRICAS_RTP}} for e in etapas]
    atual = 0
    lista_sessoes = []
    for idx, row in sess.iterrows():
        p = pcts(row)
        etapa_sessao = None
        resp = resposta(row["Data"])
        if atual < len(estado_etapas):
            e = estado_etapas[atual]
            for k in p:
                if p[k] is not None and (e["melhor"][k] is None or p[k] > e["melhor"][k]):
                    e["melhor"][k] = p[k]
            if not e["gps_cumprido"] and cumpre(p, e) and resp != "negativa":
                e["sessoes_cumpridas"] += 1
                etapa_sessao = atual
                if e["sessoes_cumpridas"] >= max(1, int(sessoes_por_etapa)):
                    e["gps_cumprido"] = True
                    e["data_gps"] = row["Data"].strftime("%Y-%m-%d")
                    # A etapa só fecha com os critérios clínicos todos marcados.
                    if all(c["cumprido"] for c in e.get("criterios", [])):
                        e["estado"] = "concluida"
                        e["data_conclusao"] = e["data_gps"]
                        atual += 1
        lista_sessoes.append({
            "data": row["Data"].strftime("%Y-%m-%d"),
            "dia_md": row.get("Dia MD") if isinstance(row.get("Dia MD"), str) else None,
            "jogo": bool(e_jogo.loc[idx]) if idx in e_jogo.index else False,
            "pct": p,
            "resposta": resp,
            "conta_para_etapa": etapa_sessao + 1 if etapa_sessao is not None else None,
        })
    # Etapa com o GPS cumprido à espera de critérios: se entretanto forem
    # marcados todos, fecha e passa à seguinte (as sessões a seguir já
    # contaram para esta, por isso a seguinte começa do zero).
    while atual < len(estado_etapas):
        e = estado_etapas[atual]
        if e["gps_cumprido"] and all(c["cumprido"] for c in e.get("criterios", [])):
            e["estado"] = "concluida"
            e["data_conclusao"] = e.get("data_gps")
            atual += 1
            continue
        e["estado"] = "aguarda_criterios" if e["gps_cumprido"] else "atual"
        break

    n = len(estado_etapas)
    progresso = (atual + (estado_etapas[atual]["sessoes_cumpridas"] / max(1, sessoes_por_etapa) if atual < n else 0)) / n * 100
    return {
        "referencias": {k: {"valor": round(r["valor"], 1), "fonte": r["fonte"]} for k, r in refs.items()},
        "sessoes": lista_sessoes[-12:][::-1],
        "etapas": estado_etapas,
        "etapa_atual": atual + 1 if atual < n else None,
        "concluido": atual >= n,
        "progresso_pct": round(progresso, 0),
    }


# ── Persistência ─────────────────────────────────────────────────────────────
def _tabela_existe() -> bool:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.planos_rtp')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


def listar_planos(team_id: str) -> dict:
    from app.services.dados_equipa import carregar_df_equipa
    from app.services.estado_service import listar_estados

    jogadores = [j for j in listar_estados(team_id) if j.get("ativo")]
    base = {
        "etapas_padrao": ETAPAS_PADRAO,
        "sessoes_por_etapa_padrao": SESSOES_POR_ETAPA,
        "metricas": [{"chave": k, "label": l} for k, _, l, _ in METRICAS_RTP],
        "jogadores": [{"player_id": j["player_id"], "nome": j["nome"], "estado": j["estado"],
                       "estado_desde": j["estado_desde"]} for j in jogadores],
    }
    if not _tabela_existe():
        return {**base, "disponivel": False, "motivo": MSG_MIGRACAO, "planos": [], "sugestoes": []}

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select r.id, r.player_id, p.nome, r.lesao_id, r.data_inicio, r.etapas,
                       r.sessoes_por_etapa, r.estado, r.notas
                from planos_rtp r join players p on p.id = r.player_id
                where r.team_id = %s and r.estado <> 'cancelado'
                order by (r.estado = 'ativo') desc, r.data_inicio desc
                """,
                (team_id,),
            )
            linhas = cur.fetchall()

    df = carregar_df_equipa(team_id)
    planos = []
    for (pid, player_id, nome, lesao_id, inicio, etapas, n_sess, estado, notas) in linhas:
        etapas = etapas if isinstance(etapas, list) else json.loads(etapas or "[]")
        avaliacao = avaliar_plano(df, nome, inicio.isoformat(), etapas, n_sess)
        planos.append({
            "id": str(pid), "player_id": str(player_id), "jogador": nome,
            "lesao_id": str(lesao_id) if lesao_id else None,
            "data_inicio": inicio.isoformat(), "sessoes_por_etapa": n_sess,
            "estado": estado, "notas": notas, **avaliacao,
        })
    com_plano = {p["player_id"] for p in planos if p["estado"] == "ativo"}
    sugestoes = [j for j in base["jogadores"] if j["estado"] in ("em_recuperacao", "lesionado") and j["player_id"] not in com_plano]
    return {**base, "disponivel": True, "motivo": None, "planos": planos, "sugestoes": sugestoes}


def criar_plano(team_id: str, player_id: str, data_inicio: str, etapas: list[dict] | None,
                sessoes_por_etapa: int | None, lesao_id: str | None, notas: str | None) -> dict:
    if not _tabela_existe():
        return {"ok": False, "erro": MSG_MIGRACAO}
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into planos_rtp (team_id, player_id, lesao_id, data_inicio, etapas, sessoes_por_etapa, notas)
                select %s, p.id, %s, %s, %s::jsonb, %s, %s from players p where p.id = %s and p.team_id = %s
                returning id
                """,
                (team_id, lesao_id or None, data_inicio, json.dumps(_limpar_etapas(etapas or ETAPAS_PADRAO)),
                 int(sessoes_por_etapa or SESSOES_POR_ETAPA), notas, player_id, team_id),
            )
            row = cur.fetchone()
    return {"ok": bool(row), "id": str(row[0]) if row else None}


def atualizar_plano(team_id: str, plano_id: str, etapas: list[dict] | None = None,
                    sessoes_por_etapa: int | None = None, estado: str | None = None,
                    notas: str | None = None, data_inicio: str | None = None) -> dict:
    if not _tabela_existe():
        return {"ok": False, "erro": MSG_MIGRACAO}
    if estado is not None and estado not in ("ativo", "concluido", "cancelado"):
        return {"ok": False, "erro": "Estado inválido."}
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update planos_rtp set
                    etapas = coalesce(%s::jsonb, etapas),
                    sessoes_por_etapa = coalesce(%s, sessoes_por_etapa),
                    estado = coalesce(%s, estado),
                    notas = coalesce(%s, notas),
                    data_inicio = coalesce(%s::date, data_inicio),
                    atualizado_em = now()
                where id = %s and team_id = %s
                returning id
                """,
                (json.dumps(_limpar_etapas(etapas)) if etapas is not None else None,
                 int(sessoes_por_etapa) if sessoes_por_etapa else None, estado, notas, data_inicio or None,
                 plano_id, team_id),
            )
            row = cur.fetchone()
    return {"ok": bool(row)}
