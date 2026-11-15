"""«Hoje»: o que falta fazer no dia, num só ecrã.

Junta o plano do dia (microciclo), o estado do plantel, os dados GPS já
importados, as respostas de bem-estar e PSE dos jogadores e os alertas de
carga — e transforma isso numa lista de tarefas com o próximo passo de cada
uma. Não cria dados: só lê o que as outras partes da app já guardam.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

from app.core.db import get_conn

AUSENTES = {"lesionado", "em_recuperacao", "ausente"}


# ── Cálculos puros ───────────────────────────────────────────────────────────
def tarefas(dia: dict) -> list[dict]:
    """Lista de tarefas do dia a partir do resumo (ver `obter`). Cada tarefa:
    chave, estado (feito | pendente | aviso | na), titulo, detalhe, acao."""
    out: list[dict] = []
    sessao = dia["sessao"]
    disp = dia["plantel"]["disponiveis"]

    # Bem-estar da manhã: todos os dias com sessão (ou com pedidos enviados).
    w = dia["bem_estar"]
    if sessao or w["pedidos"]:
        falta = max(disp - w["respostas"], 0)
        out.append({
            "chave": "bem_estar", "estado": "feito" if falta == 0 and disp else "pendente",
            "titulo": "Bem-estar da manhã",
            "detalhe": {"respostas": w["respostas"], "total": disp, "falta": w["falta"]},
            "acao": "lembrar" if w["pedidos"] and falta else ("pedir" if falta else None),
        })

    # GPS: só faz sentido depois da sessão.
    if sessao:
        g = dia["gps"]
        out.append({
            "chave": "gps", "estado": "feito" if g["jogadores"] else "pendente",
            "titulo": "Importar GPS",
            "detalhe": {"jogadores": g["jogadores"], "ultimo": g["ultimo_dia"]},
            "acao": None if g["jogadores"] else "importar",
        })

        p = dia["pse"]
        falta = max(min(disp, g["jogadores"] or disp) - p["respostas"], 0)
        out.append({
            "chave": "pse", "estado": "feito" if falta == 0 and p["respostas"] else "pendente",
            "titulo": "PSE da sessão",
            "detalhe": {"respostas": p["respostas"], "total": min(disp, g["jogadores"] or disp), "falta": p["falta"]},
            "acao": "lembrar" if p["pedidos"] and falta else ("pedir" if falta else None),
        })

    comp = dia.get("compensacao")
    if comp and comp["jogadores"] and comp["dias_desde"] <= 2:
        por_fazer = [j for j in comp["jogadores"] if (j["compensado_pct"].get("hsr") or 0) < 80]
        out.append({
            "chave": "compensacao", "estado": "pendente" if por_fazer else "feito",
            "titulo": "Compensação pós-jogo",
            "detalhe": {"data": comp["data"], "jogadores": [{"nome": j["jogador"], "minutos": j["minutos"],
                                                             "hsr": j["falta"].get("hsr"), "sprint": j["falta"].get("sprint")} for j in por_fazer]},
            "acao": "ver_semana" if por_fazer else None,
        })

    obj = dia.get("objetivo")
    if obj and obj.get("tem_fatores") and obj["sessoes_feitas"] and obj["sessoes_restantes"]:
        atras = [j["jogador"] for j in obj["jogadores"] if any(v.get("estado") == "atras" for v in j["valores"].values())]
        out.append({
            "chave": "objetivo", "estado": "aviso" if atras else "feito",
            "titulo": "Objetivo da semana",
            "detalhe": {"atras": atras, "restantes": len(obj["sessoes_restantes"]), "microciclo": obj["microciclo"]},
            "acao": "ver_semana" if atras else None,
        })

    # Os jogadores em alerta saem das tarefas: são a lista «Para agir hoje»
    # (ver acoes_do_dia), com a decisão registada em cada linha.

    if dia["plano"]["proximos_sem_plano"]:
        out.append({
            "chave": "plano", "estado": "aviso", "titulo": "Planear os próximos dias",
            "detalhe": {"dias": dia["plano"]["proximos_sem_plano"]}, "acao": "planear",
        })
    return out


# Que decisão regista o botão «Feito» de cada sinal: os sinais que pedem menos
# carga ficam como «Reduzir carga»; os outros como «Ajustar plano».
REDUZIR = {"acwr", "cmj", "crescimento", "hsr_alto", "sprint_alto"}


def decisao_feito(sinal: str) -> str:
    return "reduzir" if sinal in REDUZIR else "ajustar"


def acoes_do_dia(alertas: list[dict], decisoes_hoje: list[dict]) -> list[dict]:
    """«Para agir hoje»: um item por jogador em alerta, com os seus sinais, a
    ação sugerida de cada um e o que já foi decidido hoje (feito/ignorado).
    Os jogadores com tudo decidido vão para o fim; os de atenção alta primeiro."""
    feitas = {(d["jogador"], d["sinal"]): d for d in decisoes_hoje}
    out = []
    for a in alertas:
        if a.get("status") == "normal" or not a.get("sinais"):
            continue
        sinais = []
        for s in a["sinais"]:
            d = feitas.get((a["player_name"], s["chave"]))
            sinais.append({
                "chave": s["chave"], "texto": s["texto"], "acao": s.get("acao"), "severidade": s.get("severidade"),
                "detalhe": {k: v for k, v in (s.get("detalhe") or {}).items() if k in ("valor", "limite")},
                "decisao_feito": decisao_feito(s["chave"]),
                "decidido": {"id": d["id"], "decisao": d["decisao"]} if d else None,
            })
        pendentes = sum(1 for x in sinais if not x["decidido"])
        out.append({"jogador": a["player_name"], "player_id": a.get("player_id"), "status": a["status"],
                    "nivel": "agir" if a["status"] == "high-attention" else "vigiar",
                    "sinais": sinais, "pendentes": pendentes})
    out.sort(key=lambda x: (x["pendentes"] == 0, x["nivel"] != "agir", x["jogador"]))
    return out


def estado_plantel(plantel: dict, acoes: list[dict], em_rtp: set[str]) -> dict:
    """Uma linha: disponíveis, condicionados (alerta «agir» por decidir ou em
    regresso ao jogo), lesionados e ausentes."""
    fora = {a["nome"] for a in plantel["ausentes"]}
    condicionados = sorted(({a["jogador"] for a in acoes if a["nivel"] == "agir" and a["pendentes"]} | em_rtp) - fora)
    lesionados = [a["nome"] for a in plantel["ausentes"] if a["estado"] in ("lesionado", "em_recuperacao")]
    ausentes = [a["nome"] for a in plantel["ausentes"] if a["estado"] == "ausente"]
    return {"total": plantel["total"], "disponiveis": plantel["total"] - len(fora) - len(condicionados),
            "condicionados": condicionados, "em_rtp": sorted(em_rtp - fora), "lesionados": lesionados, "ausentes": ausentes}


def _dias_json(v) -> dict:
    if isinstance(v, str):
        return json.loads(v or "{}")
    return v or {}


# ── Dados ────────────────────────────────────────────────────────────────────
def _plano(cur, team_id: str, dia: date) -> dict:
    """Microciclo do dia, o que está planeado e os próximos 3 dias sem plano."""
    plano = {"microciclo": None, "dia": None, "proximos_sem_plano": []}
    try:
        cur.execute(
            "select numero, nome, fase, data_inicio, data_fim, dias from microciclos where team_id = %s and data_fim >= %s and data_inicio <= %s order by data_inicio",
            (team_id, dia, dia + timedelta(days=3)),
        )
        mcs = cur.fetchall()
    except Exception:
        cur.connection.rollback()
        return plano
    planeados: dict[str, dict] = {}
    for numero, nome, fase, ini, fim, dias in mcs:
        if ini <= dia <= fim:
            plano["microciclo"] = {"numero": numero, "nome": nome, "fase": fase}
        for k, v in _dias_json(dias).items():
            if isinstance(v, dict):
                planeados[k] = v
    d = planeados.get(dia.isoformat())
    if d:
        plano["dia"] = {"tipo": d.get("tipo"), "dia_md": d.get("dia_md"), "objetivo": d.get("objetivo"),
                        "exercicios": len(d.get("exercicios") or []),
                        "nomes_exercicios": [e.get("nome") for e in (d.get("exercicios") or []) if isinstance(e, dict) and e.get("nome")][:8],
                        "pct": d.get("pct") or {}}
        for numero, _n, _f, ini, fim, _d in mcs:
            if ini <= dia <= fim:
                plano["fatores_mc"] = numero
    # Só lembra de planear quem já usa os microciclos.
    cur.execute("select exists (select 1 from microciclos where team_id = %s)", (team_id,))
    if cur.fetchone()[0]:
        plano["proximos_sem_plano"] = [
            (dia + timedelta(days=i)).isoformat() for i in range(1, 4) if (dia + timedelta(days=i)).isoformat() not in planeados
        ]
    return plano


def _plantel(cur, team_id: str) -> dict:
    cur.execute("select id::text, nome, estado, estado_motivo from players where team_id = %s and ativo order by nome", (team_id,))
    linhas = cur.fetchall()
    ausentes = [{"nome": n, "estado": e, "motivo": m} for _, n, e, m in linhas if e in AUSENTES]
    return {"total": len(linhas), "disponiveis": len(linhas) - len(ausentes), "ausentes": ausentes,
            "nomes": {pid: n for pid, n, e, _ in linhas if e not in AUSENTES}}


def _sessoes_do_dia(cur, team_id: str, dia: date) -> dict:
    cur.execute(
        """
        select p.id::text, max(g.distancia_total_m), max(g.pse_sessao),
               max(coalesce(g.hooper_index, g.sono))
        from gps_sessions g join players p on p.id = g.player_id
        where g.team_id = %s and g.data = %s and p.ativo
        group by p.id
        """,
        (team_id, dia),
    )
    gps, pse, bem = set(), set(), set()
    for pid, dist, ps, w in cur.fetchall():
        if dist is not None:
            gps.add(pid)
        if ps is not None:
            pse.add(pid)
        if w is not None:
            bem.add(pid)
    cur.execute("select max(data) from gps_sessions where team_id = %s and distancia_total_m is not null", (team_id,))
    ultimo = cur.fetchone()[0]
    return {"gps": gps, "pse": pse, "bem": bem, "ultimo_gps": ultimo.isoformat() if ultimo else None}


def _em_rtp(cur, team_id: str) -> set[str]:
    cur.execute("savepoint rtp")
    try:
        cur.execute("""select p.nome from planos_rtp r join players p on p.id = r.player_id
                       where r.team_id = %s and r.estado = 'ativo' and p.ativo""", (team_id,))
        nomes = {r[0] for r in cur.fetchall()}
        cur.execute("release savepoint rtp")
        return nomes
    except Exception:
        cur.execute("rollback to savepoint rtp")
        return set()


def _treino_do_dia(team_id: str, plano: dict, estado: dict) -> dict | None:
    """O treino de hoje: objetivo, exercícios e alvo de cada jogador (o mesmo
    cálculo do relatório de treino), com quem fica de fora ou condicionado."""
    dia = plano.get("dia")
    if not dia or dia.get("tipo") != "Treino":
        return None
    out = {"dia_md": dia.get("dia_md"), "objetivo": dia.get("objetivo"), "exercicios": dia.get("nomes_exercicios") or [],
           "fonte_alvo": None, "alvos": [], "metricas": []}
    pct = {k: v for k, v in (dia.get("pct") or {}).items() if v}
    if not pct:
        return out
    try:
        from app.services import relatorios_service as rs
        from app.services.semana_jogadores_service import refs_por_jogador
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("select fatores from microciclos where team_id = %s and numero = %s", (team_id, plano.get("fatores_mc")))
                r = cur.fetchone()
        fatores = _dias_json(r[0]) if r else {}
        df = rs._df_equipa(team_id)
        if df.empty:
            return out
        jogadores = {j: rs._posicao(g) for j, g in df.groupby("Jogador")}
        alvos, fonte = rs.alvos_do_dia(jogadores, refs_por_jogador(df, jogadores), fatores, pct, None)
    except Exception:
        return out
    fora = set(estado["lesionados"]) | set(estado["ausentes"])
    cond = set(estado["condicionados"])
    metricas = [k for k in ("distancia", "hsr", "sprint", "acc", "dcc") if any(k in a for a in alvos.values())]
    out["fonte_alvo"], out["metricas"] = fonte, metricas
    out["alvos"] = sorted(
        ({"jogador": j, "posicao": jogadores.get(j, "—"), "situacao": "fora" if j in fora else "condicionado" if j in cond else "apto",
          **{k: round(a[k]) for k in metricas if a.get(k)}} for j, a in alvos.items() if a),
        key=lambda x: ({"condicionado": 0, "apto": 1, "fora": 2}[x["situacao"]], x["jogador"]))
    return out


def obter(team_id: str, user_id: str, dia: date, hoje: date) -> dict:
    from app.services import mensagens_service as ms

    with get_conn() as conn:
        with conn.cursor() as cur:
            plano = _plano(cur, team_id, dia)
            plantel = _plantel(cur, team_id)
            s = _sessoes_do_dia(cur, team_id, dia)
            em_rtp = _em_rtp(cur, team_id)

    sessao = None
    if plano["dia"] and plano["dia"].get("tipo") in ("Treino", "Jogo"):
        sessao = {"tipo": plano["dia"]["tipo"], "origem": "plano"}
    elif s["gps"] or s["pse"]:
        sessao = {"tipo": "Treino", "origem": "gps"}

    # Mensagens (pedidos e links de WhatsApp) — só se as tabelas existirem.
    msg = {"disponivel": ms.tabelas_disponiveis(), "whatsapp": False, "config": None}
    pedidos = {"wellness": [], "pse": []}
    if msg["disponivel"]:
        from app.services import whatsapp_service
        msg["whatsapp"] = whatsapp_service.configurado()
        msg["config"] = ms.obter_config(team_id)
        estado = ms.estado_do_dia(team_id, dia)
        pedidos = {t: estado[t]["pedidos"] for t in ("wellness", "pse")}

    nomes = plantel.pop("nomes")

    def bloco(tipo: str, respondidos: set) -> dict:
        lista = pedidos[tipo]
        faltam = sorted(((pid, n) for pid, n in nomes.items() if pid not in respondidos), key=lambda x: x[1])
        por_nome = {p["nome"]: p for p in lista}
        return {
            "respostas": len([pid for pid in respondidos if pid in nomes]),
            "pedidos": len(lista),
            "falta": [{"player_id": pid, "nome": n, "whatsapp": (por_nome.get(n) or {}).get("whatsapp"),
                       "token": (por_nome.get(n) or {}).get("token"),
                       "estado_envio": (por_nome.get(n) or {}).get("estado_envio"),
                       "pedido": n in por_nome} for pid, n in faltam],
        }

    from app.routers.dashboard import _build_alerts
    from app.services.limites_service import obter_limites_equipa
    try:
        alertas = [a for a in _build_alerts(team_id, obter_limites_equipa(team_id, user_id)) if a["status"] != "normal"]
    except Exception:
        alertas = []
    decisoes_hoje: list[dict] = []
    decisoes_ok = False
    try:
        from app.services import decisoes_service as ds
        r = ds.listar(team_id, dia.isoformat())
        decisoes_ok = r["disponivel"]
        decisoes_hoje = [d for d in r["decisoes"] if d["data"] == dia.isoformat()]
    except Exception:
        pass
    acoes = acoes_do_dia(alertas, decisoes_hoje)
    estado = estado_plantel(plantel, acoes, em_rtp)

    resumo = {
        "data": dia.isoformat(), "hoje": hoje.isoformat(), "e_passado": dia < hoje,
        "sessao": sessao, "plano": plano, "plantel": plantel,
        "gps": {"jogadores": len(s["gps"]), "ultimo_dia": s["ultimo_gps"]},
        "bem_estar": bloco("wellness", s["bem"]),
        "pse": bloco("pse", s["pse"]),
        "alertas": {"n": len(alertas), "jogadores": [
            {"nome": a["player_name"], "status": a["status"], "motivo": a["reason_text"], "valor": a["metric_value"]} for a in alertas]},
        "mensagens": msg,
        "acoes": acoes, "decisoes_disponivel": decisoes_ok, "estado_plantel": estado,
        "treino": _treino_do_dia(team_id, plano, estado),
    }
    try:
        from app.services import semana_jogadores_service
        semana = semana_jogadores_service.obter(team_id, dia)
        resumo["compensacao"], resumo["objetivo"] = semana["compensacao"], semana["objetivo"]
    except Exception:
        resumo["compensacao"] = resumo["objetivo"] = None
    resumo["tarefas"] = tarefas(resumo)
    # O detalhe completo vive na página «Semana por jogador»; aqui só o resumo.
    resumo.pop("objetivo", None)
    if resumo["plano"].get("dia"):
        resumo["plano"]["dia"].pop("pct", None)
    resumo["plano"].pop("fatores_mc", None)
    resumo["feitas"] = sum(1 for t in resumo["tarefas"] if t["estado"] == "feito")
    return resumo
