"""Match-Day Benchmark (brief secção 11).

Para cada métrica de carga externa, calcula a referência de jogo (média das
sessões Tipo == "Jogo") e compara o treino mais recente com essa referência —
"que percentagem da exigência de jogo é que este treino atingiu".

Referência por jogador (cada jogador vs os seus próprios jogos) e agregada à
equipa (média das referências por jogador), para não enviesar por quem tem
mais jogos registados.
"""
from __future__ import annotations

from collections import defaultdict

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


def obter_match_benchmark(team_id: str, jogador: str | None = None) -> dict:
    vazio = {"tem_dados": False, "metricas": [], "equipa": [], "jogadores": [], "data_treino": None, "n_jogos": 0}
    df = carregar_df_equipa(team_id)
    if df.empty or "Tipo" not in df.columns or "Data" not in df.columns:
        return vazio

    df = df.copy()
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df = df.dropna(subset=["Data"])
    if jogador and "Jogador" in df.columns:
        df = df[df["Jogador"] == jogador]

    jogos = df[df["Tipo"] == "Jogo"]
    treinos = df[df["Tipo"] != "Jogo"]
    if jogos.empty or treinos.empty:
        return {**vazio, "sem_referencia": jogos.empty, "sem_treinos": treinos.empty}

    metricas = [m for m in METRICAS if m["col"] in df.columns and jogos[m["col"]].notna().any()]
    if not metricas:
        return vazio

    data_treino = treinos["Data"].max()
    treino_recente = treinos[treinos["Data"] == data_treino]

    # Referência = jogo MAIS EXIGENTE até à data do treino comparado (pico por
    # métrica), não a média — é o pior caso de exigência de jogo que o jogador
    # já enfrentou, o padrão em preparação física para aferir treinos.
    jogos_ref = jogos[jogos["Data"] <= data_treino]
    if jogos_ref.empty:
        jogos_ref = jogos

    # ── Por jogador: treino recente vs jogo mais exigente do próprio jogador ─
    jogadores = []
    for nome, gt in treino_recente.groupby("Jogador"):
        gj = jogos_ref[jogos_ref["Jogador"] == nome]
        if gj.empty:
            continue
        posicao = gt["Posição"].dropna().iloc[0] if "Posição" in gt.columns and gt["Posição"].notna().any() else "—"
        linhas = {}
        for m in metricas:
            col, peak, casas = m["col"], m["peak"], m["casas"]
            benchmark = _agg(gj[col], peak=True)  # pico: o jogo mais exigente
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

    # ── Por posição: média dos jogadores de cada posição, por métrica ───────
    # Referência posicional (no espírito do Buchheit): um extremo e um central
    # têm perfis de exigência diferentes, por isso ver a % média por posição diz
    # onde o treino está a preparar bem — ou a sub-preparar — para o jogo.
    grupos: dict[str, list] = defaultdict(list)
    for j in jogadores:
        grupos[j["posicao"]].append(j)
    posicoes = []
    for pos, membros in grupos.items():
        linhas = {}
        for m in metricas:
            ch = m["chave"]
            pcts = [x["metricas"][ch]["pct"] for x in membros if x["metricas"][ch]["pct"] is not None]
            atuais = [x["metricas"][ch]["atual"] for x in membros if x["metricas"][ch]["atual"] is not None]
            benches = [x["metricas"][ch]["benchmark"] for x in membros if x["metricas"][ch]["benchmark"] is not None]
            linhas[ch] = {
                "pct": round(sum(pcts) / len(pcts), 0) if pcts else None,
                "atual": _num(sum(atuais) / len(atuais), m["casas"]) if atuais else None,
                "benchmark": _num(sum(benches) / len(benches), m["casas"]) if benches else None,
            }
        posicoes.append({"posicao": pos, "n_jogadores": len(membros), "metricas": linhas})
    posicoes.sort(key=lambda p: str(p["posicao"]))

    return {
        "tem_dados": True,
        "metricas": [{"chave": m["chave"], "label": m["label"], "unidade": m["unidade"], "cor": m["cor"], "casas": m["casas"]} for m in metricas],
        "equipa": equipa,
        "posicoes": posicoes,
        "jogadores": jogadores,
        "data_treino": data_treino.strftime("%Y-%m-%d"),
        "n_jogos": int(jogos_ref["Data"].nunique()),
    }
