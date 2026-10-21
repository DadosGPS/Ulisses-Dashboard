"""Calendário da equipa — o que foi planeado e o que foi feito em cada dia.

Junta numa só vista:
  • o plano dos microciclos (tipo do dia, dia MD, objetivo) — tabela microciclos;
  • o realizado, vindo dos dados (sessões GPS, PSE e bem-estar por jogador);
  • eventos livres do dia (viagem, prevenção, treino de lesionados…).

Tudo resiliente a migrações por aplicar: sem a tabela, essa parte vem vazia.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import pandas as pd

from app.core.db import get_conn
from app.services.dados_equipa import carregar_df_equipa

CATEGORIAS = ["Treino extra", "Prevenção", "Ginásio", "Recuperação", "Treino de lesionados", "Viagem", "Descanso", "Reunião", "Outro"]
MAX_DIAS = 62


def _f(v):
    return None if v is None else float(v)


def _existe(cur, tabela: str) -> bool:
    cur.execute("select to_regclass(%s) is not null", (f"public.{tabela}",))
    return bool(cur.fetchone()[0])


def _plantel(cur, team_id: str) -> int:
    cur.execute("select count(*) from players where team_id = %s and ativo", (team_id,))
    return int(cur.fetchone()[0] or 0)


def realizado_por_dia(df: pd.DataFrame, inicio: date, fim: date) -> dict[date, dict]:
    """Por dia: tipo (Jogo se houve jogo), dia MD, n.º de jogadores com sessão,
    quantos têm PSE e quantos têm bem-estar, e médias de PSE/minutos/distância."""
    if df.empty or "Data" not in df.columns:
        return {}
    dias = df["Data"].dt.date
    sub = df[(dias >= inicio) & (dias <= fim)]
    out: dict[date, dict] = {}
    for dia, g in sub.groupby(sub["Data"].dt.date):
        jogo = ("Tipo" in g and (g["Tipo"] == "Jogo").any()) or ("Dia MD" in g and (g["Dia MD"] == "MD").any())
        com_sessao = g
        if "Duração (min)" in g or "Distância Total (m)" in g:
            cols = [c for c in ("Duração (min)", "Distância Total (m)") if c in g]
            com_sessao = g[g[cols].notna().any(axis=1)]

        def media(col, casas=0):
            if col not in g or not g[col].notna().any():
                return None
            return round(float(g[col].mean()), casas)

        md = g["Dia MD"].dropna() if "Dia MD" in g else pd.Series(dtype=object)
        out[dia] = {
            # Só bem-estar registado (sem sessão) não conta como treino.
            "tipo": "Jogo" if jogo else ("Treino" if not com_sessao.empty else None),
            "dia_md": md.mode().iloc[0] if not md.empty else None,
            "jogadores": int(com_sessao["Jogador"].nunique()),
            "pse_respostas": int(g.dropna(subset=["PSE Sessão"])["Jogador"].nunique()) if "PSE Sessão" in g else 0,
            "wellness_respostas": int(g.dropna(subset=["Hooper Index"])["Jogador"].nunique()) if "Hooper Index" in g else 0,
            "pse_media": media("PSE Sessão", 1),
            "duracao_media": media("Duração (min)"),
            "distancia_media": media("Distância Total (m)"),
            "hsr_media": media("HSR (m)"),
            "partilhada": bool("Equipa origem" in g and g["Equipa origem"].notna().any()),
        }
    return out


def obter(team_id: str, inicio: str, fim: str) -> dict:
    ini, fi = date.fromisoformat(inicio), date.fromisoformat(fim)
    if fi < ini or (fi - ini).days > MAX_DIAS:
        raise ValueError(f"Intervalo inválido (máximo {MAX_DIAS} dias).")

    planos: dict[date, dict] = {}
    info_mc: dict[int, dict] = {}
    eventos: dict[date, list] = {}
    pedidos: dict[date, dict] = {}
    with get_conn() as conn:
        with conn.cursor() as cur:
            plantel = _plantel(cur, team_id)
            if _existe(cur, "microciclos"):
                cur.execute(
                    """
                    select numero, perfil, data_inicio, data_fim, dias, fatores from microciclos
                    where team_id = %s and data_inicio <= %s and data_fim >= %s
                    """,
                    (team_id, fi, ini),
                )
                linhas_mc = cur.fetchall()
                numeros = [x[0] for x in linhas_mc]
                plano_valores: dict[tuple[int, str], dict] = {}
                if numeros:
                    cur.execute(
                        "select exists (select 1 from information_schema.columns where table_name = 'pse_planeado' and column_name = 'duracao_min')"
                    )
                    dur = bool(cur.fetchone()[0])
                    cur.execute(
                        f"select microciclo_nr, dia_md, pse_esperada, {'duracao_min' if dur else 'null'} from pse_planeado where team_id = %s and microciclo_nr = any(%s)",
                        (team_id, numeros),
                    )
                    for nr, mdk, p_, t_ in cur.fetchall():
                        plano_valores.setdefault((nr, mdk), {})
                        plano_valores[(nr, mdk)].update({"pse": _f(p_), "duracao_min": _f(t_)})
                    cur.execute(
                        "select microciclo_nr, dia_md, distancia_m, hsr_m, sprint_m from carga_externa_planeada where team_id = %s and microciclo_nr = any(%s)",
                        (team_id, numeros),
                    )
                    for nr, mdk, d_, h_, s_ in cur.fetchall():
                        plano_valores.setdefault((nr, mdk), {})
                        plano_valores[(nr, mdk)].update({"distancia_m": _f(d_), "hsr_m": _f(h_), "sprint_m": _f(s_)})
                for numero, perfil, a, b, dias_json, fatores_mc in linhas_mc:
                    fatores_mc = fatores_mc if isinstance(fatores_mc, dict) else json.loads(fatores_mc or "{}")
                    dias_json = dias_json if isinstance(dias_json, dict) else json.loads(dias_json or "{}")
                    d = a
                    while d <= b:
                        p = dias_json.get(d.isoformat(), {})
                        vazio = {"pse": None, "duracao_min": None, "distancia_m": None, "hsr_m": None, "sprint_m": None}
                        valores = plano_valores.get((numero, p.get("dia_md")), {}) if p.get("tipo", "Treino") == "Treino" else {}
                        planos[d] = {"microciclo": numero, "perfil": perfil, "tipo": p.get("tipo"),
                                     "dia_md": p.get("dia_md"), "objetivo": p.get("objetivo") or "",
                                     "planeado": {**vazio, **valores}, "pct": p.get("pct") or {}}
                        d += timedelta(days=1)
                    # Soma das % já planeadas na semana (só treinos), por variável.
                    soma: dict[str, float] = {}
                    for v in dias_json.values():
                        if v.get("tipo", "Treino") == "Treino":
                            for k, x in (v.get("pct") or {}).items():
                                soma[k] = round(soma.get(k, 0) + float(x), 1)
                    info_mc[numero] = {"fatores": fatores_mc, "pct_semana": soma}
            if _existe(cur, "calendario_eventos"):
                cur.execute(
                    "select id::text, data, titulo, categoria from calendario_eventos where team_id = %s and data between %s and %s order by criado_em",
                    (team_id, ini, fi),
                )
                for eid, d, titulo, cat in cur.fetchall():
                    eventos.setdefault(d, []).append({"id": eid, "titulo": titulo, "categoria": cat})
            if _existe(cur, "pedidos_resposta"):
                cur.execute(
                    """
                    select data, tipo, count(*), count(respondido_em) from pedidos_resposta
                    where team_id = %s and data between %s and %s group by data, tipo
                    """,
                    (team_id, ini, fi),
                )
                for d, tipo, total, resp in cur.fetchall():
                    pedidos.setdefault(d, {})[tipo] = {"total": int(total), "respondidos": int(resp)}

    df_equipa = carregar_df_equipa(team_id)
    real = realizado_por_dia(df_equipa, ini, fi)
    if info_mc:
        from app.services.microciclos_service import alvos_semanais, referencia_equipa
        ref = referencia_equipa(df_equipa)
        for info in info_mc.values():
            info["alvos"] = alvos_semanais(info["fatores"], ref)

    dias, resumo = [], {"Treino": 0, "Jogo": 0, "Folga": 0}
    extra: dict[str, int] = {}
    d = ini
    while d <= fi:
        r, p = real.get(d), planos.get(d)
        tipo = (r or {}).get("tipo") or (p or {}).get("tipo")
        if tipo in resumo:
            resumo[tipo] += 1
        for e in eventos.get(d, []):
            extra[e["categoria"]] = extra.get(e["categoria"], 0) + 1
        ped = pedidos.get(d, {})
        dias.append({
            "data": d.isoformat(),
            "plano": p,
            "real": r,
            "eventos": eventos.get(d, []),
            # PSE: respostas / quem treinou; bem-estar: respostas / plantel.
            # Pedidos por WhatsApp ainda sem dados contam como "x de y enviados".
            "pse": ({"respondidos": r["pse_respostas"], "total": r["jogadores"] or plantel} if r and r["tipo"]
                    else ped.get("pse") and {**ped["pse"]}),
            "wellness": ({"respondidos": r["wellness_respostas"], "total": plantel} if r and r["wellness_respostas"]
                         else ped.get("wellness") and {**ped["wellness"]}),
        })
        d += timedelta(days=1)

    return {
        "inicio": ini.isoformat(), "fim": fi.isoformat(), "plantel": plantel,
        "dias": dias, "resumo": resumo, "microciclos": {str(k): v for k, v in info_mc.items()},
        "extra": sorted(([k, v] for k, v in extra.items()), key=lambda x: -x[1]),
        "categorias": CATEGORIAS,
    }


def criar_evento(team_id: str, user_id: str, data: str, titulo: str, categoria: str) -> dict:
    titulo = " ".join((titulo or "").split())[:80]
    if not titulo:
        raise ValueError("Escreve o que foi feito.")
    if categoria not in CATEGORIAS:
        raise ValueError("Categoria inválida.")
    d = date.fromisoformat(data)
    with get_conn() as conn:
        with conn.cursor() as cur:
            if not _existe(cur, "calendario_eventos"):
                raise ValueError("Aplica a migração supabase/migrations/0013_calendario.sql para registar eventos.")
            cur.execute(
                "insert into calendario_eventos (team_id, data, titulo, categoria, criado_por) values (%s, %s, %s, %s, %s) returning id::text",
                (team_id, d, titulo, categoria, user_id),
            )
            return {"ok": True, "id": cur.fetchone()[0]}


def apagar_evento(team_id: str, evento_id: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("delete from calendario_eventos where id = %s and team_id = %s", (evento_id, team_id))
            return {"ok": cur.rowcount > 0}
