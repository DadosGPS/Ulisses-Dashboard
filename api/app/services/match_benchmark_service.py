"""Match-Day Benchmark (brief secção 11).

Para cada métrica de carga externa, calcula a referência de jogo (média das
sessões Tipo == "Jogo") e compara o treino mais recente com essa referência —
"que percentagem da exigência de jogo é que este treino atingiu".

Referência por jogador (cada jogador vs os seus próprios jogos) e agregada à
equipa (média das referências por jogador), para não enviesar por quem tem
mais jogos registados.
"""
from __future__ import annotations

import pandas as pd

from app.services.carga_externa_service import METRICAS
from app.services.dados_equipa import carregar_df_equipa


def _num(v, casas: int) -> float | None:
    if v is None or pd.isna(v):
        return None
    return round(float(v), casas)


def _agg(serie: pd.Series, peak: bool) -> float | None:
    s = serie.dropna()
    if s.empty:
        return None
    return float(s.max() if peak else s.mean())


def obter_match_benchmark(team_id: str) -> dict:
    vazio = {"tem_dados": False, "metricas": [], "equipa": [], "jogadores": [], "data_treino": None, "n_jogos": 0}
    df = carregar_df_equipa(team_id)
    if df.empty or "Tipo" not in df.columns or "Data" not in df.columns:
        return vazio

    df = df.copy()
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df = df.dropna(subset=["Data"])

    jogos = df[df["Tipo"] == "Jogo"]
    treinos = df[df["Tipo"] != "Jogo"]
    if jogos.empty or treinos.empty:
        return {**vazio, "sem_referencia": jogos.empty, "sem_treinos": treinos.empty}

    metricas = [m for m in METRICAS if m["col"] in df.columns and jogos[m["col"]].notna().any()]
    if not metricas:
        return vazio

    data_treino = treinos["Data"].max()
    treino_recente = treinos[treinos["Data"] == data_treino]

    # ── Por jogador: treino recente vs média de jogos do próprio jogador ────
    jogadores = []
    for nome, gt in treino_recente.groupby("Jogador"):
        gj = jogos[jogos["Jogador"] == nome]
        if gj.empty:
            continue
        posicao = gt["Posição"].dropna().iloc[0] if "Posição" in gt.columns and gt["Posição"].notna().any() else "—"
        linhas = {}
        for m in metricas:
            col, peak, casas = m["col"], m["peak"], m["casas"]
            benchmark = _agg(gj[col], peak)
            atual = _agg(gt[col], peak)
            pct = round(atual / benchmark * 100, 0) if (atual is not None and benchmark) else None
            linhas[m["chave"]] = {"atual": _num(atual, casas), "benchmark": _num(benchmark, casas), "pct": pct}
        jogadores.append({"jogador": nome, "posicao": posicao, "metricas": linhas})
    jogadores.sort(key=lambda r: r["jogador"].lower())

    # ── Equipa: média das referências/valores por jogador ───────────────────
    equipa = []
    for m in metricas:
        chave = m["chave"]
        benches = [j["metricas"][chave]["benchmark"] for j in jogadores if j["metricas"][chave]["benchmark"] is not None]
        atuais = [j["metricas"][chave]["atual"] for j in jogadores if j["metricas"][chave]["atual"] is not None]
        benchmark = sum(benches) / len(benches) if benches else None
        atual = sum(atuais) / len(atuais) if atuais else None
        pct = round(atual / benchmark * 100, 0) if (atual is not None and benchmark) else None
        equipa.append({
            "chave": chave, "label": m["label"], "unidade": m["unidade"], "cor": m["cor"],
            "benchmark": _num(benchmark, m["casas"]), "atual": _num(atual, m["casas"]), "pct": pct,
        })

    return {
        "tem_dados": True,
        "metricas": [{"chave": m["chave"], "label": m["label"], "unidade": m["unidade"], "cor": m["cor"], "casas": m["casas"]} for m in metricas],
        "equipa": equipa,
        "jogadores": jogadores,
        "data_treino": data_treino.strftime("%Y-%m-%d"),
        "n_jogos": int(jogos["Data"].nunique()),
    }
