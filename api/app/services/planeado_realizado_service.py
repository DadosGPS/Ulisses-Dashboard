"""Planeado vs realizado da sessão de treino mais recente — para o Centro de
Controlo responder logo após cada treino a «fizemos o que planeámos?».

Junta o que já se guarda no Planeamento (PSE esperada em `pse_planeado` e
carga externa planeada em `carga_externa_planeada`, ambas por microciclo e
dia MD) com a média real da equipa nessa sessão, e calcula o desvio.
"""
from __future__ import annotations

import pandas as pd

from app.core.db import get_conn
from app.services.dados_equipa import carregar_df_equipa
from app.services.referencia_jogo import mascara_jogo

# (coluna no DataFrame, chave planeada, rótulo, unidade, casas)
METRICAS = [
    ("PSE Sessão", "pse", "PSE", "", 1),
    ("Distância Total (m)", "distancia_m", "Distância", "m", 0),
    ("HSR (m)", "hsr_m", "HSR", "m", 0),
    ("Sprint (m)", "sprint_m", "Sprint", "m", 0),
]

# Desvio |real − planeado| ÷ planeado: até OK_PCT está dentro do plano, até
# ATENCAO_PCT é um desvio a vigiar, acima disso ficou fora do plano.
OK_PCT = 10.0
ATENCAO_PCT = 20.0
N_JOGADORES_FORA = 6


def _estado(desvio: float | None) -> str:
    if desvio is None:
        return "sem_plano"
    a = abs(desvio)
    if a <= OK_PCT:
        return "ok"
    if a <= ATENCAO_PCT:
        return "atencao"
    return "fora"


def _desvio(real: float | None, plano: float | None) -> float | None:
    if real is None or plano is None or plano <= 0:
        return None
    return round((real - plano) / plano * 100.0, 0)


def comparar_sessao(df: pd.DataFrame, planeado: dict[tuple[int, str], dict]) -> dict:
    """Parte pura (testável): `planeado` = {(microciclo, dia_md): {pse,
    distancia_m, hsr_m, sprint_m}}."""
    vazio = {"tem_dados": False, "motivo": None}
    if df is None or df.empty or "Data" not in df.columns:
        return {**vazio, "motivo": "Ainda não há sessões."}
    df = df.copy()
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    treinos = df[~mascara_jogo(df)].dropna(subset=["Data"])
    if treinos.empty:
        return {**vazio, "motivo": "Ainda não há sessões de treino."}

    data = treinos["Data"].max()
    sessao = treinos[treinos["Data"] == data]
    dia = str(sessao["Dia MD"].dropna().iloc[0]) if "Dia MD" in sessao.columns and sessao["Dia MD"].notna().any() else None
    mc = int(sessao["Microciclo (Nr)"].dropna().iloc[0]) if "Microciclo (Nr)" in sessao.columns and sessao["Microciclo (Nr)"].notna().any() else None
    plano = planeado.get((mc, dia), {}) if mc is not None and dia else {}

    metricas = []
    for col, chave, label, unidade, casas in METRICAS:
        if col not in sessao.columns or sessao[col].dropna().empty:
            continue
        real = round(float(sessao[col].mean()), casas)
        p = plano.get(chave)
        d = _desvio(real, p)
        metricas.append({"chave": chave, "label": label, "unidade": unidade,
                         "planeado": p, "real": real, "desvio_pct": d, "estado": _estado(d)})

    # Jogadores mais afastados do plano de HSR (o alvo que mais se mexe por jogador).
    jogadores_fora = []
    if plano.get("hsr_m") and "HSR (m)" in sessao.columns:
        for jog, v in sessao.dropna(subset=["Jogador", "HSR (m)"]).groupby("Jogador")["HSR (m)"].mean().items():
            d = _desvio(float(v), plano["hsr_m"])
            if d is not None and abs(d) > ATENCAO_PCT:
                jogadores_fora.append({"jogador": jog, "real": round(float(v), 0), "desvio_pct": d})
        jogadores_fora.sort(key=lambda j: -abs(j["desvio_pct"]))

    return {
        "tem_dados": bool(metricas),
        "motivo": None if metricas else "A sessão mais recente não tem PSE nem métricas GPS.",
        "data": data.strftime("%Y-%m-%d"),
        "dia_md": dia,
        "microciclo": mc,
        "tem_plano": any(m["planeado"] is not None for m in metricas),
        "n_jogadores": int(sessao["Jogador"].nunique()) if "Jogador" in sessao.columns else 0,
        "limites": {"ok": OK_PCT, "atencao": ATENCAO_PCT},
        "metricas": metricas,
        "jogadores_fora": jogadores_fora[:N_JOGADORES_FORA],
    }


def _carregar_planeado(team_id: str) -> dict[tuple[int, str], dict]:
    """Planeado de toda a equipa, por (microciclo, dia MD). Resiliente a uma
    tabela em falta (migração por aplicar): devolve o que conseguir."""
    planeado: dict[tuple[int, str], dict] = {}
    consultas = [
        ("select microciclo_nr, dia_md, pse_esperada from pse_planeado where team_id = %s", ["pse"]),
        ("select microciclo_nr, dia_md, distancia_m, hsr_m, sprint_m from carga_externa_planeada where team_id = %s",
         ["distancia_m", "hsr_m", "sprint_m"]),
    ]
    for sql, chaves in consultas:
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (team_id,))
                    for row in cur.fetchall():
                        alvo = planeado.setdefault((int(row[0]), str(row[1])), {})
                        for chave, valor in zip(chaves, row[2:]):
                            if valor is not None:
                                alvo[chave] = float(valor)
        except Exception:
            continue
    return planeado


def obter_planeado_vs_realizado(team_id: str) -> dict:
    return comparar_sessao(carregar_df_equipa(team_id), _carregar_planeado(team_id))
