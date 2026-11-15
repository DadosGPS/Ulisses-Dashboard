"""Períodos de uma sessão: partes do jogo e exercícios, jogador a jogador.

Os exports por períodos (Catapult «Period Name», STATSports «Drill Title»…)
trazem várias linhas por jogador no mesmo dia — uma por parte ou exercício,
às vezes mais uma linha com o total da sessão. Este módulo decide, linha a
linha, o que é cada uma:

  · total   → «Total», «Session», «Sessão completa», «Full game»…: é o total
              do dia. Se existir, é ele que vai para gps_sessions (as outras
              linhas não se somam — somá-las contava a sessão duas vezes);
  · parte   → 1.ª/2.ª parte (e prolongamento): relatório de jogo por parte;
  · exercicio → o resto: análise por exercício no relatório de treino.

Sem nenhuma linha de total, o total do dia continua a ser a soma das linhas
(o comportamento de sempre da importação).
"""
from __future__ import annotations

import re
import unicodedata

import pandas as pd

COL = "Período"

_TOTAIS = {
    "total", "totais", "session", "sessao", "sessao completa", "sessao total", "full session",
    "whole session", "full", "all", "jogo completo", "full game", "full match", "jogo", "match",
    "total session", "session total", "game", "todo",
}

# Ordem dos períodos de jogo: 1.ª parte, 2.ª parte, 1.ª/2.ª parte do prolongamento.
_PARTES = [
    (1, re.compile(r"^(1|i|primeir[ao]|first|1st|1ª|1a|1º|1o)\s*(\.|ª|º)?\s*(parte|half|tempo|periodo|period|h|p|t)\b|^(half|parte|periodo|period|tempo)\s*1$|^1h$|^h1$|^p1$|^1t$")),
    (2, re.compile(r"^(2|ii|segund[ao]|second|2nd|2ª|2a|2º|2o)\s*(\.|ª|º)?\s*(parte|half|tempo|periodo|period|h|p|t)\b|^(half|parte|periodo|period|tempo)\s*2$|^2h$|^h2$|^p2$|^2t$")),
]
_PROLONGAMENTO = re.compile(r"(prolongamento|extra time|overtime|\bet\b|\bot\b)")

ROTULO_PARTE = {1: "1.ª parte", 2: "2.ª parte"}


def _chave(nome) -> str:
    s = "".join(c for c in unicodedata.normalize("NFKD", str(nome)) if not unicodedata.combining(c))
    return " ".join(s.lower().replace("_", " ").replace("-", " ").split())


def vazio(v) -> bool:
    return v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() in ("", "nan", "None")


def classificar(nome) -> tuple[str, str | None, int]:
    """(categoria, rótulo normalizado, ordem) para o nome de um período.
    categoria ∈ total | parte | exercicio. O rótulo das partes é sempre
    «1.ª parte» / «2.ª parte» (seja qual for a grafia no ficheiro)."""
    if vazio(nome):
        return "exercicio", None, 0
    k = _chave(nome)
    if k in _TOTAIS:
        return "total", None, 0
    prolong = bool(_PROLONGAMENTO.search(k))
    sem_prolong = _PROLONGAMENTO.sub("", k).strip()
    for n, padrao in _PARTES:
        if padrao.search(sem_prolong):
            if prolong:
                return "parte", f"Prolongamento {n}", 2 + n
            return "parte", ROTULO_PARTE[n], n
    if prolong:
        return "parte", "Prolongamento", 3
    return "exercicio", str(nome).strip(), 0


def separar(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(linhas para o total do dia, linhas de período).

    As linhas de período (partes e exercícios) saem com as colunas extra
    `_categoria`, `_periodo` e `_ordem`. As linhas para o total do dia são:
    a linha de total quando o ficheiro a traz para esse jogador/dia/tipo, ou
    todas as linhas desse jogador/dia/tipo (somam-se a jusante)."""
    if df is None or df.empty or COL not in df.columns or df[COL].map(vazio).all():
        return df, pd.DataFrame()

    df = df.copy()
    info = df[COL].map(classificar)
    df["_categoria"] = info.map(lambda t: t[0])
    df["_periodo"] = info.map(lambda t: t[1])
    df["_ordem_parte"] = info.map(lambda t: t[2])
    tem_nome = ~df[COL].map(vazio)

    chave = [c for c in ("Jogador", "Data", "Tipo") if c in df.columns]
    chave_serie = df[chave].astype(str).agg("|".join, axis=1) if chave else pd.Series("", index=df.index)
    com_total = set(chave_serie[df["_categoria"] == "total"])
    usar_total = chave_serie.isin(com_total)
    linhas_sessao = df[~usar_total | (df["_categoria"] == "total")]

    periodos = df[tem_nome & (df["_categoria"] != "total")].copy()
    if not periodos.empty:
        # Ordem dentro da sessão: partes pela sua ordem natural; exercícios pela
        # ordem em que aparecem no ficheiro (depois das partes, se houver ambas).
        pos = periodos.groupby(chave_serie[periodos.index]).cumcount() if chave else pd.Series(range(len(periodos)), index=periodos.index)
        periodos["_ordem"] = periodos["_ordem_parte"].where(periodos["_categoria"] == "parte", 100 + pos)
    linhas_sessao = linhas_sessao.drop(columns=["_categoria", "_periodo", "_ordem_parte"])
    return linhas_sessao, periodos


def diferenca_total(df: pd.DataFrame, cols: list[str], tolerancia_pct: float = 5.0) -> list[dict]:
    """Jogador/dia em que a soma dos períodos difere do total trazido no
    ficheiro em mais de `tolerancia_pct` (só onde o ficheiro traz os dois).
    Diferenças pequenas são normais (tempo entre exercícios fora dos períodos)."""
    if df is None or df.empty or COL not in df.columns:
        return []
    d = df.copy()
    d["_cat"] = d[COL].map(lambda v: classificar(v)[0] if not vazio(v) else None)
    chave = [c for c in ("Jogador", "Data", "Tipo") if c in d.columns]
    if not chave:
        return []
    out = []
    for k, g in d.groupby(chave, dropna=False):
        tot = g[g["_cat"] == "total"]
        per = g[g["_cat"].isin(["parte", "exercicio"])]
        if tot.empty or per.empty:
            continue
        for col in cols:
            if col not in g.columns:
                continue
            t = pd.to_numeric(tot[col], errors="coerce").sum()
            s = pd.to_numeric(per[col], errors="coerce").sum()
            if t > 0 and abs(s - t) / t * 100 > tolerancia_pct:
                k = k if isinstance(k, tuple) else (k,)
                out.append({"jogador": k[0], "data": k[1] if len(k) > 1 else None, "coluna": col,
                            "total": float(t), "soma": float(s), "indice": int(tot.index[0])})
                break
    return out
