"""Carga Externa — secção principal do produto (brief de redesign).

Serviço único que alimenta a página de Carga Externa e, por reutilização, as
comparações por jogador e por posição. Toda a leitura assenta em
`carregar_df_equipa()` (DataFrame canónico partilhado), por isso qualquer
métrica que exista nos dados fica automaticamente disponível.

Hierarquia do brief: dado bruto → métrica → baseline → comparação → estado.
"""
from __future__ import annotations

import pandas as pd

from app.services.dados_equipa import carregar_df_equipa

# Métricas de carga externa. `peak=True` agrega por máximo (Vmax é um pico, não
# um acumulado); as restantes agregam por média-por-jogador ao nível de equipa,
# o que é robusto a variações no tamanho do plantel entre sessões.
METRICAS: list[dict] = [
    {"chave": "distancia_total_m", "col": "Distância Total (m)", "label": "Distância Total", "unidade": "m",    "cor": "#2563eb", "casas": 0, "peak": False},
    {"chave": "hsr_m",             "col": "HSR (m)",             "label": "HSR",             "unidade": "m",    "cor": "#f59e0b", "casas": 0, "peak": False},
    {"chave": "sprint_m",          "col": "Sprint (m)",          "label": "Sprint",          "unidade": "m",    "cor": "#dc2626", "casas": 0, "peak": False},
    {"chave": "acc_n",             "col": "Acc (n)",             "label": "Acelerações",     "unidade": "n",    "cor": "#14b8a6", "casas": 0, "peak": False},
    {"chave": "dcc_n",             "col": "Dcc (n)",             "label": "Desacelerações",  "unidade": "n",    "cor": "#10b981", "casas": 0, "peak": False},
    {"chave": "vel_max_kmh",       "col": "Vel. Máx (km/h)",     "label": "Vel. Máx",        "unidade": "km/h", "cor": "#8b5cf6", "casas": 1, "peak": True},
]

# Limiar de desvio face ao baseline para classificar o estado (%). Não é um
# diagnóstico — é uma flag de monitorização, como o brief exige.
LIMIAR_ESTADO_PCT = 15.0


def _num(v, casas: int) -> float | None:
    if v is None or pd.isna(v):
        return None
    return round(float(v), casas)


def _estado(atual: float | None, baseline: float | None, n_baseline: int) -> tuple[str, float | None]:
    """Devolve (estado, delta_pct). Estados: alto | baixo | normal | insuficiente."""
    if atual is None or baseline is None or n_baseline < 2 or baseline == 0:
        return "insuficiente", None
    delta = (atual - baseline) / baseline * 100.0
    if delta >= LIMIAR_ESTADO_PCT:
        return "alto", round(delta, 1)
    if delta <= -LIMIAR_ESTADO_PCT:
        return "baixo", round(delta, 1)
    return "normal", round(delta, 1)


def _vazio() -> dict:
    return {
        "tem_dados": False,
        "filtros_disponiveis": {"tipos": [], "posicoes": [], "dias_md": [], "microciclos": [], "jogadores": []},
        "sessao_recente": None,
        "metricas": [],
        "kpis": [],
        "jogadores": [],
        "evolucao": {},
    }


def obter_carga_externa(
    team_id: str,
    tipo: str | None = None,
    posicao: str | None = None,
    dia_md: str | None = None,
    microciclo: int | None = None,
    jogador: str | None = None,
    baseline_dias: int = 28,
) -> dict:
    df = carregar_df_equipa(team_id)
    if df.empty or "Data" not in df.columns:
        return _vazio()

    df = df.copy()
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df = df.dropna(subset=["Data"])
    if df.empty:
        return _vazio()

    # Opções de filtro — sempre do universo completo, para o utilizador poder
    # mudar de filtro sem ficar preso ao subconjunto atual.
    def _opcoes(col: str) -> list:
        if col not in df.columns:
            return []
        return sorted(v for v in df[col].dropna().unique().tolist())

    filtros_disponiveis = {
        "tipos": _opcoes("Tipo"),
        "posicoes": _opcoes("Posição"),
        "dias_md": _opcoes("Dia MD"),
        "microciclos": [int(v) for v in _opcoes("Microciclo (Nr)")],
        "jogadores": _opcoes("Jogador"),
    }

    # Filtros de contexto (não temporais) — separados dos temporais para se
    # poderem calcular baselines comparáveis ("esta semana vs as outras semanas"
    # mantém o mesmo jogador/tipo/posição, variando só o microciclo).
    cdf = df
    if jogador and "Jogador" in cdf.columns:
        cdf = cdf[cdf["Jogador"] == jogador]
    if tipo and "Tipo" in cdf.columns:
        cdf = cdf[cdf["Tipo"] == tipo]
    if posicao and "Posição" in cdf.columns:
        cdf = cdf[cdf["Posição"] == posicao]

    # Filtros temporais (microciclo/dia) — definem o escopo do que se mostra.
    fdf = cdf
    if dia_md and "Dia MD" in fdf.columns:
        fdf = fdf[fdf["Dia MD"] == dia_md]
    if microciclo is not None and "Microciclo (Nr)" in fdf.columns:
        fdf = fdf[fdf["Microciclo (Nr)"] == microciclo]

    base = {
        "tem_dados": True,
        "filtros_disponiveis": filtros_disponiveis,
        "filtros": {
            "tipo": tipo, "posicao": posicao, "dia_md": dia_md,
            "microciclo": microciclo, "baseline_dias": baseline_dias,
        },
    }

    if fdf.empty:
        return {**base, "escopo": None, "sessao_recente": None, "metricas": [], "kpis": [], "jogadores": [], "evolucao": {}}

    # Métricas com dados reais no subconjunto filtrado.
    metricas_disp = [m for m in METRICAS if m["col"] in fdf.columns and fdf[m["col"]].notna().any()]

    sessao_recente = fdf["Data"].max()

    # ── Escopo temporal — o que a página mostra ──────────────────────────────
    #  • Dia escolhido        → só esse dia (a ocorrência mais recente).
    #  • Microciclo (sem dia) → total da semana (soma dos dias por jogador).
    #  • Nada                 → sessão mais recente.
    if dia_md:
        modo = "dia"
    elif microciclo is not None:
        modo = "semana"
    else:
        modo = "sessao"

    if modo == "semana":
        janela = fdf                       # todos os dias do microciclo
        dia_janela = None
    else:                                   # dia ou sessao → um único dia
        dia_janela = sessao_recente
        janela = fdf[fdf["Data"] == dia_janela]

    def _valor_equipa(jdf: pd.DataFrame, col: str, peak: bool) -> float | None:
        """Valor de equipa no conjunto dado: pico global (Vmax) ou, para as
        restantes, média entre jogadores do total de cada jogador (robusto ao
        tamanho do plantel)."""
        if col not in jdf.columns:
            return None
        s = jdf[col].dropna()
        if s.empty:
            return None
        if peak:
            return float(s.max())
        por_jog = jdf.dropna(subset=[col]).groupby("Jogador")[col].sum()
        return float(por_jog.mean()) if not por_jog.empty else None

    def _baseline_periodo(col: str, peak: bool) -> tuple[float | None, int]:
        """Média de períodos comparáveis (exclui o período atual): outras
        semanas (modo semana) ou outros dias do mesmo Dia MD (modo dia)."""
        if modo == "semana":
            if "Microciclo (Nr)" not in cdf.columns:
                return None, 0
            valores = {mc: _valor_equipa(g, col, peak) for mc, g in cdf.groupby("Microciclo (Nr)")}
            outros = [v for k, v in valores.items() if k != microciclo and v is not None]
        else:  # dia
            sub = cdf[cdf["Dia MD"] == dia_md] if (dia_md and "Dia MD" in cdf.columns) else cdf
            valores = {d: _valor_equipa(g, col, peak) for d, g in sub.groupby("Data")}
            outros = [v for k, v in valores.items() if k != dia_janela and v is not None]
        if not outros:
            return None, 0
        return sum(outros) / len(outros), len(outros)

    # ── Séries de evolução (equipa por dia) + KPIs vs baseline do escopo ─────
    evolucao: dict[str, list[dict]] = {}
    kpis: list[dict] = []
    for m in metricas_disp:
        col, peak = m["col"], m["peak"]
        sub = fdf.dropna(subset=[col])
        if sub.empty:
            continue
        # Série temporal (equipa por dia): média por jogador (ou pico, p/ Vmax).
        serie = sub.groupby("Data")[col].max() if peak else sub.groupby("Data")[col].mean()
        serie = serie.sort_index()
        evolucao[m["chave"]] = [
            {"data": d.strftime("%Y-%m-%d"), "valor": _num(v, m["casas"])}
            for d, v in serie.items()
        ]

        atual = _valor_equipa(janela, col, peak)
        if modo == "sessao":
            anteriores = serie[serie.index < sessao_recente]
            if baseline_dias > 0 and not anteriores.empty:
                corte = sessao_recente - pd.Timedelta(days=baseline_dias)
                janela_b = anteriores[anteriores.index >= corte]
                anteriores = janela_b if not janela_b.empty else anteriores
            baseline = float(anteriores.mean()) if not anteriores.empty else None
            n_baseline = int(len(anteriores))
        else:
            baseline, n_baseline = _baseline_periodo(col, peak)

        estado, delta = _estado(atual, baseline, n_baseline)
        kpis.append({
            "chave": m["chave"], "label": m["label"], "unidade": m["unidade"], "cor": m["cor"],
            "atual": _num(atual, m["casas"]), "baseline": _num(baseline, m["casas"]),
            "delta_pct": delta, "estado": estado, "n_baseline": n_baseline,
        })

    # ── Tabela/barras por jogador (agregado ao escopo escolhido) ─────────────
    jogadores: list[dict] = []
    for nome_jog, g in janela.groupby("Jogador"):
        valores: dict[str, float | None] = {}
        for m in metricas_disp:
            col = m["col"]
            if col not in g.columns or g[col].notna().sum() == 0:
                valores[m["chave"]] = None
                continue
            valores[m["chave"]] = _num(g[col].max() if m["peak"] else g[col].sum(), m["casas"])

        dist = valores.get("distancia_total_m")
        hsr = valores.get("hsr_m")
        sprint = valores.get("sprint_m")
        duracao = g["Duração (min)"].sum() if "Duração (min)" in g.columns else None

        derivados = {
            "dist_min": _num(dist / duracao, 1) if dist and duracao else None,
            "hsr_min": _num(hsr / duracao, 1) if hsr and duracao else None,
            "pct_hsr": _num(hsr / dist * 100, 1) if dist and hsr else None,
            "pct_sprint": _num(sprint / hsr * 100, 1) if hsr and sprint else None,
        }

        posicao_jog = g["Posição"].dropna().iloc[0] if "Posição" in g.columns and g["Posição"].notna().any() else "—"
        jogadores.append({
            "jogador": nome_jog,
            "posicao": posicao_jog,
            "valores": valores,
            "derivados": derivados,
        })

    # Ordenar por distância total (métrica âncora) desc, quando existe.
    if metricas_disp:
        ancora = metricas_disp[0]["chave"]
        jogadores.sort(key=lambda r: (r["valores"].get(ancora) is None, -(r["valores"].get(ancora) or 0)))

    # ── Rótulos do escopo (para a UI dizer exatamente o que está a mostrar) ──
    if modo == "semana":
        escopo = {
            "modo": "semana",
            "label": f"Semana {microciclo} · total da semana",
            "baseline_label": "média das outras semanas",
            "data": None,
        }
    elif modo == "dia":
        d_leg = dia_janela.strftime("%d/%m/%Y") if dia_janela is not None else ""
        escopo = {
            "modo": "dia",
            "label": f"{dia_md} · {d_leg}".strip(" ·"),
            "baseline_label": "média dos dias equivalentes",
            "data": dia_janela.strftime("%Y-%m-%d") if dia_janela is not None else None,
        }
    else:
        escopo = {
            "modo": "sessao",
            "label": "Sessão mais recente",
            "baseline_label": f"baseline de {baseline_dias} dias",
            "data": sessao_recente.strftime("%Y-%m-%d"),
        }

    return {
        **base,
        "escopo": escopo,
        "sessao_recente": sessao_recente.strftime("%Y-%m-%d"),
        "metricas": [{"chave": m["chave"], "label": m["label"], "unidade": m["unidade"], "cor": m["cor"], "casas": m["casas"]} for m in metricas_disp],
        "kpis": kpis,
        "jogadores": jogadores,
        "evolucao": evolucao,
    }
