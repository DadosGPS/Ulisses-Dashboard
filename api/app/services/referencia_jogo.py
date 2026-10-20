"""Referência de jogo — fonte única para tudo o que compara treino com jogo
(exposição HSR/Sprint, avisos, mapa de calor, match benchmark, planeamento).

Porquê: usar o «jogo mais exigente» em bruto penaliza quem joga pouco. Um
suplente que jogou 20 minutos fica com uma referência baixíssima e qualquer
semana de treino parece 3× o jogo; um único jogo atípico também distorce tudo.

Regra (métricas de volume — distância, HSR, sprint, acelerações, carga):
  1. Valor por 90 minutos (valor ÷ minutos × 90) nos jogos com pelo menos
     MIN_MINUTOS minutos jogados;
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
MIN_MINUTOS = 60
N_JOGOS = 5

FONTE_MEDIA_90 = "media_90"   # média por 90' dos últimos jogos completos
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

    Devolve {jogador: {"valor": float, "fonte": str, "n_jogos": int}}.
    """
    if col not in jogos.columns or "Jogador" not in jogos.columns:
        return {}
    j = jogos.dropna(subset=["Jogador", col])
    j = j[j[col] > 0]
    out: dict[str, dict] = {}

    tem_duracao = COL_DURACAO in j.columns and j[COL_DURACAO].notna().any()
    if peak or not tem_duracao:
        for jog, g in j.groupby("Jogador"):
            out[jog] = {"valor": float(g[col].max()), "fonte": FONTE_PICO, "n_jogos": int(len(g))}
        return out

    completos = j[j[COL_DURACAO] >= MIN_MINUTOS]
    if "Data" in completos.columns:
        completos = completos.sort_values("Data")
    for jog, g in completos.groupby("Jogador"):
        ult = g.tail(N_JOGOS)
        valor = float((ult[col] / ult[COL_DURACAO] * 90).mean())
        out[jog] = {"valor": valor, "fonte": FONTE_MEDIA_90, "n_jogos": int(len(ult))}

    # Quem jogou mas nunca 60', e quem não jogou de todo → posição/equipa.
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
            out[jog] = {"valor": float(pd.Series(vals).median()), "fonte": FONTE_POSICAO, "n_jogos": 0}
        elif mediana_equipa is not None:
            out[jog] = {"valor": mediana_equipa, "fonte": FONTE_EQUIPA, "n_jogos": 0}
        else:
            g = j[j["Jogador"] == jog]
            if not g.empty:  # sem nenhum jogo completo na equipa → pico próprio
                out[jog] = {"valor": float(g[col].max()), "fonte": FONTE_PICO, "n_jogos": int(len(g))}
    return out


def valores_referencia(refs: dict[str, dict]) -> dict[str, float]:
    """Atalho: {jogador: valor}."""
    return {jog: r["valor"] for jog, r in refs.items()}
