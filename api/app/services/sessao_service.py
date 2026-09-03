"""Detalhe de uma sessão (brief secção 15).

Uma sessão = (Data, Tipo). Mostra a carga externa e interna por jogador, os
totais/médias de equipa, e a comparação com as sessões equivalentes (mesmo
Tipo e, quando existe, mesmo Dia MD) — para responder a "esta sessão foi mais
ou menos exigente do que o habitual para este tipo de dia?".
"""
from __future__ import annotations

import pandas as pd

from app.services.carga_externa_service import METRICAS
from app.services.dados_equipa import carregar_df_equipa

# Métricas mostradas no detalhe: carga externa + interna.
METRICAS_SESSAO = METRICAS + [
    {"chave": "carga_interna", "col": "Carga Interna", "label": "Carga Interna", "unidade": "UA", "cor": "#e63946", "casas": 0, "peak": False},
    {"chave": "pse_sessao", "col": "PSE Sessão", "label": "PSE", "unidade": "/10", "cor": "#3498db", "casas": 1, "peak": False},
]

LIMIAR_ESTADO_PCT = 15.0


def _num(v, casas):
    if v is None or pd.isna(v):
        return None
    return round(float(v), casas)


def _estado(atual, baseline):
    if atual is None or baseline is None or baseline == 0:
        return "insuficiente", None
    delta = (atual - baseline) / baseline * 100.0
    if delta >= LIMIAR_ESTADO_PCT:
        return "alto", round(delta, 1)
    if delta <= -LIMIAR_ESTADO_PCT:
        return "baixo", round(delta, 1)
    return "normal", round(delta, 1)


def obter_sessao(team_id: str, data: str, tipo: str | None = None) -> dict:
    df = carregar_df_equipa(team_id)
    if df.empty or "Data" not in df.columns:
        return {"tem_dados": False}

    df = df.copy()
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df = df.dropna(subset=["Data"])
    alvo = pd.to_datetime(data, errors="coerce")
    if pd.isna(alvo):
        return {"tem_dados": False}

    sessao = df[df["Data"] == alvo]
    if tipo and "Tipo" in sessao.columns:
        sessao = sessao[sessao["Tipo"] == tipo]
    if sessao.empty:
        return {"tem_dados": False}

    tipo_real = sessao["Tipo"].dropna().iloc[0] if "Tipo" in sessao.columns and sessao["Tipo"].notna().any() else (tipo or "—")
    dia_md = sessao["Dia MD"].dropna().iloc[0] if "Dia MD" in sessao.columns and sessao["Dia MD"].notna().any() else None
    microciclo = int(sessao["Microciclo (Nr)"].dropna().iloc[0]) if "Microciclo (Nr)" in sessao.columns and sessao["Microciclo (Nr)"].notna().any() else None

    metricas = [m for m in METRICAS_SESSAO if m["col"] in sessao.columns and sessao[m["col"]].notna().any()]

    # Referência: sessões equivalentes (mesmo tipo e, se houver, mesmo dia MD),
    # excluindo a própria. Valor de equipa por sessão = média por jogador.
    equiv = df.copy()
    if "Tipo" in equiv.columns:
        equiv = equiv[equiv["Tipo"] == tipo_real]
    if dia_md and "Dia MD" in equiv.columns:
        equiv = equiv[equiv["Dia MD"] == dia_md]
    equiv = equiv[equiv["Data"] != alvo]

    kpis = []
    for m in metricas:
        col, peak = m["col"], m["peak"]
        atual = float(sessao[col].max()) if peak else float(sessao[col].mean())
        baseline = None
        if not equiv.empty and col in equiv.columns and equiv[col].notna().any():
            por_sessao = equiv.groupby("Data")[col].max() if peak else equiv.groupby("Data")[col].mean()
            if not por_sessao.empty:
                baseline = float(por_sessao.mean())
        estado, delta = _estado(atual, baseline)
        kpis.append({
            "chave": m["chave"], "label": m["label"], "unidade": m["unidade"], "cor": m["cor"],
            "atual": _num(atual, m["casas"]), "baseline": _num(baseline, m["casas"]),
            "delta_pct": delta, "estado": estado, "n_baseline": int(equiv["Data"].nunique()) if not equiv.empty else 0,
        })

    # Tabela por jogador.
    jogadores = []
    for jogador, g in sessao.groupby("Jogador"):
        valores = {}
        for m in metricas:
            col = m["col"]
            valores[m["chave"]] = _num(g[col].max() if m["peak"] else g[col].sum(), m["casas"]) if g[col].notna().any() else None
        posicao = g["Posição"].dropna().iloc[0] if "Posição" in g.columns and g["Posição"].notna().any() else "—"
        jogadores.append({"jogador": jogador, "posicao": posicao, "valores": valores})
    if metricas:
        ancora = metricas[0]["chave"]
        jogadores.sort(key=lambda r: (r["valores"].get(ancora) is None, -(r["valores"].get(ancora) or 0)))

    duracao = _num(sessao["Duração (min)"].max(), 0) if "Duração (min)" in sessao.columns else None

    return {
        "tem_dados": True,
        "data": alvo.strftime("%Y-%m-%d"),
        "tipo": tipo_real,
        "dia_md": dia_md or "—",
        "microciclo": microciclo,
        "duracao_min": duracao,
        "n_jogadores": int(sessao["Jogador"].nunique()),
        "n_equivalentes": int(equiv["Data"].nunique()) if not equiv.empty else 0,
        "metricas": [{"chave": m["chave"], "label": m["label"], "unidade": m["unidade"], "cor": m["cor"], "casas": m["casas"]} for m in metricas],
        "kpis": kpis,
        "jogadores": jogadores,
    }
