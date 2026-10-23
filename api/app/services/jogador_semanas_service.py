"""Evolução semanal de um jogador: carga de cada microciclo com Z-score,
velocidade máxima face ao recorde, ACWR por métrica e variação das últimas
duas semanas.

- Carga da semana = soma de todas as sessões do microciclo (treinos e jogos).
- Z-score de cada semana = (valor − média) ÷ desvio-padrão das semanas do
  intervalo escolhido, do próprio jogador (precisa de ≥ 3 semanas).
- ACWR = última semana do intervalo ÷ média das 4 semanas anteriores
  (agudo ÷ crónico, desacoplado), com pelo menos 2 semanas de histórico.
- Δ 2 semanas = variação da última semana face à anterior, em %.
"""
from __future__ import annotations

import statistics

import pandas as pd

METRICAS = {
    "distancia": ("Distância Total (m)", "Distância total", "m"),
    "hsr": ("HSR (m)", "HSR", "m"),
    "sprint": ("Sprint (m)", "Sprint", "m"),
    "acc": ("Acc (n)", "Acelerações", "n"),
    "dcc": ("Dcc (n)", "Desacelerações", "n"),
}
COL_VMAX = "Vel. Máx (km/h)"
SEMANAS_CRONICO = 4


# ── Cálculos puros ───────────────────────────────────────────────────────────
def semanas_do_jogador(g: pd.DataFrame) -> list[dict]:
    """Uma linha por microciclo com os totais de cada métrica e a Vmáx."""
    if g is None or g.empty or "Microciclo (Nr)" not in g.columns:
        return []
    g = g.dropna(subset=["Microciclo (Nr)"])
    out = []
    for mc, s in g.groupby("Microciclo (Nr)"):
        linha = {"microciclo": int(mc), "sessoes": int(len(s)),
                 "inicio": s["Data"].min().date().isoformat() if "Data" in s else None,
                 "fim": s["Data"].max().date().isoformat() if "Data" in s else None}
        for k, (col, _, _) in METRICAS.items():
            linha[k] = round(float(s[col].sum()), 1) if col in s.columns and s[col].notna().any() else None
        linha["vmax"] = round(float(s[COL_VMAX].max()), 1) if COL_VMAX in s.columns and s[COL_VMAX].notna().any() else None
        out.append(linha)
    return sorted(out, key=lambda x: x["microciclo"])


def zscores(valores: list[float | None]) -> tuple[list[float | None], float | None]:
    """Z-score de cada valor face aos outros do intervalo, e a média."""
    vals = [v for v in valores if v is not None]
    if not vals:
        return [None] * len(valores), None
    media = statistics.fmean(vals)
    if len(vals) < 3:
        return [None] * len(valores), round(media, 1)
    dp = statistics.pstdev(vals)
    if dp == 0:
        return [0.0 if v is not None else None for v in valores], round(media, 1)
    return [None if v is None else round((v - media) / dp, 2) for v in valores], round(media, 1)


def acwr(todas: list[dict], ultima: int, chave: str) -> float | None:
    """Semana `ultima` ÷ média das SEMANAS_CRONICO semanas anteriores (com valor)."""
    atual = next((s[chave] for s in todas if s["microciclo"] == ultima), None)
    antes = [s[chave] for s in todas if s["microciclo"] < ultima and s[chave] is not None][-SEMANAS_CRONICO:]
    if atual is None or len(antes) < 2:
        return None
    cronico = statistics.fmean(antes)
    return round(atual / cronico, 2) if cronico > 0 else None


def variacao(a: float | None, b: float | None) -> float | None:
    """Variação de a → b, em %."""
    if a is None or b is None or a == 0:
        return None
    return round((b - a) / a * 100, 1)


def semana_incompleta(todas: list[dict], semana: dict) -> bool:
    """A semana é a mais recente do jogador e tem menos sessões do que é
    habitual (mediana das anteriores) — provavelmente ainda está a decorrer."""
    if semana["microciclo"] != todas[-1]["microciclo"] or len(todas) < 2:
        return False
    habitual = statistics.median(s["sessoes"] for s in todas[:-1])
    return semana["sessoes"] < habitual


def evolucao(g: pd.DataFrame, de: int | None, ate: int | None, n_padrao: int = 5) -> dict:
    todas = semanas_do_jogador(g)
    if not todas:
        return {"tem_dados": False, "microciclos": [], "semanas": []}
    mcs = [s["microciclo"] for s in todas]
    if ate is None or ate not in mcs:
        ate = mcs[-1]
    if de is None or de not in mcs or de > ate:
        anteriores = [m for m in mcs if m <= ate]
        de = anteriores[max(0, len(anteriores) - n_padrao)]
    semanas = [dict(s) for s in todas if de <= s["microciclo"] <= ate]
    medias = {}
    for k in METRICAS:
        zs, medias[k] = zscores([s[k] for s in semanas])
        for s, z in zip(semanas, zs):
            s[f"z_{k}"] = z
    recorde = max((s["vmax"] for s in todas if s["vmax"] is not None), default=None)
    for s in semanas:
        s["pct_recorde"] = round(s["vmax"] / recorde * 100) if recorde and s["vmax"] is not None else None
    ultima, penultima = semanas[-1], (semanas[-2] if len(semanas) > 1 else None)
    return {
        "tem_dados": True,
        "microciclos": mcs, "de": de, "ate": ate,
        "metricas": [{"chave": k, "label": l, "unidade": u} for k, (_, l, u) in METRICAS.items()],
        "semanas": semanas, "medias": medias, "recorde_vmax": recorde,
        "acwr": {k: acwr(todas, ultima["microciclo"], k) for k in METRICAS},
        "variacao_2_semanas": {k: variacao(penultima[k], ultima[k]) if penultima else None for k in METRICAS},
        "semana_referencia": ultima["microciclo"],
        "referencia_incompleta": semana_incompleta(todas, ultima),
    }


def obter(team_id: str, nome: str, de: int | None, ate: int | None) -> dict:
    from app.services.dados_equipa import carregar_df_equipa

    df = carregar_df_equipa(team_id)
    if df.empty or "Jogador" not in df.columns:
        return {"tem_dados": False, "microciclos": [], "semanas": []}
    return {"jogador": nome, **evolucao(df[df["Jogador"] == nome], de, ate)}
