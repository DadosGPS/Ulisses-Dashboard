"""Decisões da semana, jogador a jogador.

1) Objetivo semanal por jogador: o objetivo do microciclo (fator semanal ×
   referência de jogo DO JOGADOR, por jogo completo da equipa) contra o que já fez em treino, com o
   que falta e quanto por sessão nas sessões que ainda restam.
2) Compensação pós-jogo: quem jogou pouco (ou não jogou) no último jogo e
   quanto lhe faltou face a um jogo completo — para o treino compensatório.

São contas para apoiar a decisão do preparador físico, não prescrições.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import pandas as pd

from app.services.microciclos_service import FATORES
from app.services.referencia_jogo import COL_DURACAO, duracao_jogo, mascara_jogo, referencias_jogo

MARGEM_PP = 20.0        # ± pontos percentuais face ao esperado para «atrás»/«à frente»
MIN_PCT_JOGO = 60.0     # abaixo de 60 % dos minutos do jogo → precisa de compensação
DURACAO_JOGO_PADRAO = 80.0
COMP_METRICAS = ["distancia", "hsr", "sprint", "acc", "dcc"]


# ── Cálculos puros ───────────────────────────────────────────────────────────
def _num(v, casas=0):
    return None if v is None or pd.isna(v) else round(float(v), casas)


def refs_por_jogador(df: pd.DataFrame, jogadores: dict[str, str]) -> dict[str, dict[str, float]]:
    """{jogador: {chave: referência de jogo por jogo completo}} para os FATORES
    (ver referencia_jogo; a duração desse jogo completo é duracao_jogo)."""
    jogos = df[mascara_jogo(df)] if not df.empty else df
    out: dict[str, dict[str, float]] = {j: {} for j in jogadores}
    for k, (col, _, _) in FATORES.items():
        if col not in df.columns:
            continue
        for jog, r in referencias_jogo(jogos, col, jogadores=jogadores).items():
            if jog in out and r.get("valor"):
                out[jog][k] = float(r["valor"])
    return out


def objetivo_semanal(df: pd.DataFrame, jogadores: dict[str, str], fatores: dict, inicio: date, fim: date,
                     treinos_planeados: list[str], hoje: date) -> dict:
    """Objetivo semanal por jogador (ver docstring do módulo)."""
    if df.empty or "Data" not in df.columns:
        sem = df
    else:
        dias = df["Data"].dt.date
        sem = df[(dias >= inicio) & (dias <= fim)]
        sem = sem[~mascara_jogo(sem)]
    datas_feitas = sorted({d.isoformat() for d in sem["Data"].dt.date}) if not sem.empty else []
    ultimo = max(datas_feitas) if datas_feitas else None
    corte = max(ultimo or "", (hoje - timedelta(days=1)).isoformat())
    restantes = [d for d in treinos_planeados if d > corte]
    total = len(set(datas_feitas) | set(treinos_planeados)) or 1
    # Sem treinos no plano não se sabe quantas sessões tem a semana: mostra-se
    # o feito, mas sem «atrás/à frente».
    esperado = round(len(datas_feitas) / total * 100, 1) if treinos_planeados else None

    refs = refs_por_jogador(df, jogadores)
    metricas = [k for k in FATORES if k in fatores and float(fatores[k] or 0) > 0]
    linhas = []
    for jog in sorted(jogadores):
        g = sem[sem["Jogador"] == jog] if not sem.empty else sem
        valores = {}
        for k in metricas:
            col = FATORES[k][0]
            feito = float(g[col].sum()) if col in g.columns and not g.empty else 0.0
            ref = refs.get(jog, {}).get(k)
            alvo = float(fatores[k]) * ref if ref else None
            pct = feito / alvo * 100 if alvo else None
            falta = max(alvo - feito, 0.0) if alvo else None
            estado = None
            if pct is not None and esperado is not None:
                estado = "atras" if pct < esperado - MARGEM_PP else "frente" if pct > esperado + MARGEM_PP else "ok"
            valores[k] = {
                "alvo": _num(alvo), "feito": _num(feito), "pct": _num(pct, 0), "falta": _num(falta),
                "por_sessao": _num(falta / len(restantes)) if falta is not None and restantes else None,
                "estado": estado,
            }
        linhas.append({"jogador": jog, "posicao": jogadores[jog] or "—", "sessoes": int(g["Data"].nunique()) if not g.empty else 0,
                       "valores": valores})
    return {
        "metricas": [{"chave": k, "label": FATORES[k][1], "unidade": FATORES[k][2], "fator": float(fatores[k])} for k in metricas],
        "sessoes_feitas": datas_feitas, "sessoes_restantes": restantes, "esperado_pct": esperado,
        "jogadores": linhas,
    }


def compensacao(df: pd.DataFrame, jogadores: dict[str, str], hoje: date, ausentes: set[str] | None = None) -> dict | None:
    """Compensação do último jogo até `hoje` (ver docstring do módulo)."""
    if df.empty or "Data" not in df.columns:
        return None
    jogos = df[mascara_jogo(df) & (df["Data"].dt.date <= hoje)]
    if jogos.empty:
        return None
    dia = jogos["Data"].max()
    jogo = jogos[jogos["Data"] == dia]
    dur_col = jogo[COL_DURACAO] if COL_DURACAO in jogo.columns else pd.Series(dtype=float)
    duracao = float(dur_col.max()) if dur_col.notna().any() else DURACAO_JOGO_PADRAO
    refs = refs_por_jogador(df, jogadores)
    # As referências estão por jogo completo da equipa (dur_ref minutos);
    # este jogo pode ter sido mais curto ou mais longo (torneio, prolongamento).
    dur_ref = duracao_jogo(df[mascara_jogo(df)]) or duracao
    depois = df[(df["Data"] > dia) & (df["Data"].dt.date <= hoje) & ~mascara_jogo(df)]
    adversario = None
    linhas = []
    for jog in sorted(jogadores):
        if ausentes and jog in ausentes:
            continue
        gj = jogo[jogo["Jogador"] == jog]
        minutos = float(gj[COL_DURACAO].sum()) if COL_DURACAO in gj.columns and not gj.empty and gj[COL_DURACAO].notna().any() else (0.0 if gj.empty else None)
        if minutos is None:  # jogou mas sem duração registada — não dá para saber
            continue
        pct_min = minutos / duracao * 100 if duracao else 0
        if pct_min >= MIN_PCT_JOGO:
            continue
        gd = depois[depois["Jogador"] == jog]
        falta, compensado = {}, {}
        for k in COMP_METRICAS:
            col = FATORES[k][0]
            ref = refs.get(jog, {}).get(k)
            if not ref or col not in df.columns:
                continue
            esperado = ref * duracao / dur_ref
            feito_jogo = float(gj[col].sum()) if not gj.empty else 0.0
            f = max(esperado - feito_jogo, 0.0)
            falta[k] = _num(f)
            ja = float(gd[col].sum()) if not gd.empty and col in gd.columns else 0.0
            compensado[k] = _num(min(ja / f * 100, 100), 0) if f > 0 else None
        linhas.append({"jogador": jog, "posicao": jogadores[jog] or "—", "minutos": _num(minutos), "pct_minutos": _num(pct_min, 0),
                       "falta": falta, "compensado_pct": compensado})
    linhas.sort(key=lambda r: (r["minutos"] or 0, r["jogador"]))
    return {
        "data": dia.date().isoformat(), "duracao_min": _num(duracao), "dias_desde": (hoje - dia.date()).days,
        "adversario": adversario, "minimo_pct": MIN_PCT_JOGO,
        "metricas": [{"chave": k, "label": FATORES[k][1], "unidade": FATORES[k][2]} for k in COMP_METRICAS if any(k in l["falta"] for l in linhas)],
        "jogadores": linhas,
    }


# ── Dados ────────────────────────────────────────────────────────────────────
def obter(team_id: str, hoje: date, microciclo: int | None = None) -> dict:
    from app.core.db import get_conn
    from app.services.dados_equipa import carregar_df_equipa

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select nome, coalesce(posicao, ''), estado from players where team_id = %s and ativo", (team_id,))
            plantel = cur.fetchall()
            mcs = []
            try:
                cur.execute("select numero, nome, data_inicio, data_fim, fatores, dias from microciclos where team_id = %s order by data_inicio", (team_id,))
                mcs = cur.fetchall()
            except Exception:
                conn.rollback()
    jogadores = {n: p for n, p, _ in plantel}
    ausentes = {n for n, _, e in plantel if e in ("lesionado", "em_recuperacao", "ausente")}
    df = carregar_df_equipa(team_id)
    if not df.empty and "Data" in df.columns:
        df = df.copy()
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
        df = df.dropna(subset=["Data"])
        df = df[df["Jogador"].isin(jogadores)]

    escolhido = None
    if microciclo is not None:
        escolhido = next((m for m in mcs if m[0] == microciclo), None)
    if escolhido is None:
        escolhido = next((m for m in mcs if m[2] <= hoje <= m[3]), None) or next((m for m in reversed(mcs) if m[2] <= hoje), None)

    objetivo = None
    if escolhido is not None:
        numero, nome, ini, fim, fatores, dias = escolhido
        fatores = json.loads(fatores) if isinstance(fatores, str) else (fatores or {})
        dias = json.loads(dias) if isinstance(dias, str) else (dias or {})
        treinos = sorted(k for k, v in dias.items() if isinstance(v, dict) and v.get("tipo") == "Treino")
        objetivo = {"microciclo": numero, "nome": nome, "inicio": ini.isoformat(), "fim": fim.isoformat(),
                    "tem_fatores": any(float(v or 0) > 0 for v in fatores.values()),
                    **objetivo_semanal(df, jogadores, fatores, ini, fim, treinos, hoje)}
    return {
        "hoje": hoje.isoformat(),
        "microciclos": [m[0] for m in mcs],
        "objetivo": objetivo,
        "compensacao": compensacao(df, jogadores, hoje, ausentes) if not df.empty else None,
    }
