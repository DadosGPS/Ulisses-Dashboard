"""Referência de jogo — fonte única para tudo o que compara treino com jogo
(exposição HSR/Sprint, avisos, mapa de calor, match benchmark, planeamento).

Porquê: usar o «jogo mais exigente» em bruto penaliza quem joga pouco. Um
suplente que jogou 20 minutos fica com uma referência baixíssima e qualquer
semana de treino parece 3× o jogo; um único jogo atípico também distorce tudo.

Regra (métricas de volume — distância, HSR, sprint, acelerações, carga):
  1. Valor por JOGO COMPLETO DA EQUIPA (valor ÷ minutos × duração do jogo),
     nos jogos em que o jogador fez pelo menos FRACAO_JOGO_COMPLETO dos
     minutos. A duração do jogo vem dos próprios dados (ver duracao_jogo):
     60' num sub-13, 70–80' num sub-15, 90' nos seniores. Normalizar sempre a
     90' fazia a referência de um sub-13 valer 1,5× o jogo que ele realmente
     joga, e qualquer semana de treino parecia «exposição baixa»;
  2. Média dos últimos N_JOGOS desses jogos;
  3. Jogador sem nenhum jogo assim → mediana dos colegas da mesma posição
     (ou da equipa, se a posição não tiver referência);
  4. Sem minutos nos dados → o pico de jogo do jogador (comportamento antigo).

Métricas de pico (velocidade máxima) não se normalizam por minutos: a
referência é o pico em jogo.
"""
from __future__ import annotations

import pandas as pd

COL_DURACAO = "Duração (min)"
FRACAO_JOGO_COMPLETO = 0.75   # jogo «completo» = ≥ 75 % da duração do jogo (60' em 80')
N_JOGOS = 5

FONTE_MEDIA_JOGO = "media_jogo"  # média por jogo completo dos últimos jogos completos
FONTE_MEDIA_90 = FONTE_MEDIA_JOGO  # nome antigo, mantido para os imports existentes
FONTE_POSICAO = "posicao"     # mediana da posição (jogador sem jogos completos)
FONTE_EQUIPA = "equipa"       # mediana da equipa (posição sem referência)
FONTE_PICO = "pico"           # pico em jogo (sem minutos ou métrica de pico)


def mascara_jogo(df: pd.DataFrame) -> pd.Series:
    """Sessões que contam como JOGO: Tipo «Jogo» ou dia «MD». Assim um jogo
    registado com Tipo «Treino» mas dia MD não entra na carga de treino."""
    m = pd.Series(False, index=df.index)
    if "Tipo" in df.columns:
        m |= df["Tipo"] == "Jogo"
    if "Dia MD" in df.columns:
        m |= df["Dia MD"].astype(str).str.strip().str.upper() == "MD"
    return m


def duracao_jogo(jogos: pd.DataFrame) -> float | None:
    """Duração de um jogo completo desta equipa, em minutos: em cada dia de
    jogo, a maior duração registada (quem jogou o jogo todo); depois a mediana
    desses jogos — um torneio de jogos curtos não muda a referência."""
    if jogos is None or jogos.empty or COL_DURACAO not in jogos.columns:
        return None
    d = pd.to_numeric(jogos[COL_DURACAO], errors="coerce")
    if "Data" not in jogos.columns:  # sem datas não se separam os jogos
        return float(d.max()) if (d > 0).any() else None
    por_jogo = d[d > 0].groupby(jogos.loc[d > 0, "Data"]).max()
    return float(por_jogo.median()) if not por_jogo.empty else None


def _posicoes(df: pd.DataFrame) -> dict[str, str]:
    if "Posição" not in df.columns or "Jogador" not in df.columns:
        return {}
    s = df.dropna(subset=["Jogador", "Posição"])
    if "Data" in s.columns:
        s = s.sort_values("Data")
    return {j: p for j, p in s.groupby("Jogador")["Posição"].last().items() if isinstance(p, str)}


def referencias_jogo(
    jogos: pd.DataFrame,
    col: str,
    peak: bool = False,
    jogadores: dict[str, str] | None = None,
) -> dict[str, dict]:
    """Referência de jogo por jogador para `col`.

    `jogos` = sessões de jogo (ver mascara_jogo). `jogadores` = {jogador:
    posição} de quem precisa de referência mesmo sem jogos (ex.: todos os que
    treinaram) — recebem a referência da posição/equipa.

    Devolve {jogador: {"valor": float, "fonte": str, "n_jogos": int,
    "duracao_ref": float | None}} — `valor` é por jogo completo de
    `duracao_ref` minutos (None nas métricas de pico).
    """
    if col not in jogos.columns or "Jogador" not in jogos.columns:
        return {}
    j = jogos.dropna(subset=["Jogador", col])
    j = j[j[col] > 0]
    out: dict[str, dict] = {}

    tem_duracao = COL_DURACAO in j.columns and j[COL_DURACAO].notna().any()
    dur_ref = duracao_jogo(j) if tem_duracao and not peak else None
    if peak or not dur_ref:
        for jog, g in j.groupby("Jogador"):
            out[jog] = {"valor": float(g[col].max()), "fonte": FONTE_PICO, "n_jogos": int(len(g)), "duracao_ref": None}
        return out

    completos = j[j[COL_DURACAO] >= FRACAO_JOGO_COMPLETO * dur_ref]
    if "Data" in completos.columns:
        completos = completos.sort_values("Data")
    for jog, g in completos.groupby("Jogador"):
        ult = g.tail(N_JOGOS)
        valor = float((ult[col] / ult[COL_DURACAO] * dur_ref).mean())
        out[jog] = {"valor": valor, "fonte": FONTE_MEDIA_JOGO, "n_jogos": int(len(ult)), "duracao_ref": dur_ref}

    # Quem nunca fez um jogo completo, e quem não jogou de todo → posição/equipa.
    posicoes = _posicoes(jogos)
    posicoes.update({k: v for k, v in (jogadores or {}).items() if isinstance(v, str) and v})
    precisam = (set(j["Jogador"].unique()) | set(jogadores or {})) - set(out)
    if not precisam:
        return out
    base = {jog: r["valor"] for jog, r in out.items()}
    por_posicao: dict[str, list[float]] = {}
    for jog, v in base.items():
        if jog in posicoes:
            por_posicao.setdefault(posicoes[jog], []).append(v)
    mediana_equipa = float(pd.Series(list(base.values())).median()) if base else None
    for jog in precisam:
        vals = por_posicao.get(posicoes.get(jog, ""))
        if vals:
            out[jog] = {"valor": float(pd.Series(vals).median()), "fonte": FONTE_POSICAO, "n_jogos": 0, "duracao_ref": dur_ref}
        elif mediana_equipa is not None:
            out[jog] = {"valor": mediana_equipa, "fonte": FONTE_EQUIPA, "n_jogos": 0, "duracao_ref": dur_ref}
        else:
            g = j[j["Jogador"] == jog]
            if not g.empty:  # sem nenhum jogo completo na equipa → pico próprio
                out[jog] = {"valor": float(g[col].max()), "fonte": FONTE_PICO, "n_jogos": int(len(g)), "duracao_ref": None}
    return out


def valores_referencia(refs: dict[str, dict]) -> dict[str, float]:
    """Atalho: {jogador: valor}."""
    return {jog: r["valor"] for jog, r in refs.items()}
