"""Relatórios de sessão: treino (alvo por jogador + exercícios) e jogo (por
parte + face à época de cada jogador).

Relatório de treino — responde a «fizeram o que era preciso hoje?»:
  · alvo individual do dia = % do dia no plano (Calendário) × fator semanal
    do microciclo × referência de jogo DO JOGADOR (ver referencia_jogo). Sem
    % no plano, usa o planeado da equipa para esse dia MD (o mesmo alvo para
    todos); sem nenhum dos dois, não há alvo — só a comparação com o habitual;
  · bandas: < 80 % · 80–90 · 90–110 (dentro) · 110–120 · > 120 %;
  · «vs habitual» = o próprio jogador nos outros treinos com o mesmo dia MD
    (variação habitual, ver variacao.py);
  · exercícios: por jogador quando o ficheiro trazia a coluna «Período»
    (gps_periodos); senão, a folha de exercícios da equipa (exercises). Cada
    exercício é comparado, por minuto, com a sua média nas outras sessões.

Relatório de jogo:
  · equipa = jogadores com ≥ 75 % dos minutos do jogo (FRACAO_JOGO_COMPLETO),
    face aos outros jogos da época com o mesmo critério;
  · por jogador, a comparação com a própria época é feita POR MINUTO (e a
    velocidade máxima em bruto): comparar totais punia sempre quem jogou
    menos. Só entram jogos de pelo menos MIN_MINUTOS_HIST minutos;
  · 1.ª vs 2.ª parte vem das linhas de período (coluna «Período»).
"""
from __future__ import annotations

import json
from datetime import date

import pandas as pd

from app.services.referencia_jogo import COL_DURACAO, FRACAO_JOGO_COMPLETO, duracao_jogo, mascara_jogo
from app.services.variacao import classificar
from utils.calculos import recorde_vmax

# chave → (coluna canónica, rótulo, unidade, casas, por_minuto)
METRICAS: dict[str, tuple[str, str, str, int, bool]] = {
    "distancia": ("Distância Total (m)", "Distância", "m", 0, True),
    "hsr": ("HSR (m)", "HSR", "m", 0, True),
    "sprint": ("Sprint (m)", "Sprint", "m", 0, True),
    "acc": ("Acc (n)", "Acelerações", "n", 0, True),
    "dcc": ("Dcc (n)", "Desacelerações", "n", 0, True),
    "vmax": ("Vel. Máx (km/h)", "Vel. máx.", "km/h", 1, False),
}
VOLUME = ["distancia", "hsr", "sprint", "acc", "dcc"]
BANDAS = [(80, "muito_abaixo"), (90, "abaixo"), (110, "dentro"), (120, "acima")]  # > 120 → muito_acima
MIN_MINUTOS_HIST = 30


def _n(v, casas=0):
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return round(float(v), casas)


def _dp(xs: list[float]) -> float:
    m = sum(xs) / len(xs)
    return (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5


def banda(pct: float | None) -> str | None:
    if pct is None:
        return None
    for lim, nome in BANDAS:
        if pct < lim:
            return nome
    return "muito_acima"


def _metricas_presentes(df: pd.DataFrame) -> list[str]:
    return [k for k, (col, *_r) in METRICAS.items() if col in df.columns and df[col].notna().any()]


def _desc(chaves: list[str]) -> list[dict]:
    return [{"chave": k, "label": METRICAS[k][1], "unidade": METRICAS[k][2], "casas": METRICAS[k][3]} for k in chaves]


def _preparar(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty or "Data" not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df = df.dropna(subset=["Data", "Jogador"])
    for k, (col, *_r) in METRICAS.items():
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if COL_DURACAO in df.columns:
        df[COL_DURACAO] = pd.to_numeric(df[COL_DURACAO], errors="coerce")
    return df


def _posicao(g: pd.DataFrame) -> str:
    if "Posição" in g.columns and g["Posição"].notna().any():
        return str(g["Posição"].dropna().iloc[-1])
    return "—"


def _vmax_recordes(df: pd.DataFrame) -> dict[str, float]:
    col = METRICAS["vmax"][0]
    if col not in df.columns:
        return {}
    return {j: r for j, g in df.groupby("Jogador") if (r := recorde_vmax(g[col])) is not None}


def _por_minuto(valor, minutos):
    if valor is None or minutos is None or not minutos or pd.isna(valor) or pd.isna(minutos):
        return None
    return float(valor) / float(minutos)


# ══════════════════════════════════════════════════════════════════════════
# Relatório de treino
# ══════════════════════════════════════════════════════════════════════════
def alvos_do_dia(jogadores: dict[str, str], refs: dict[str, dict[str, float]], fatores: dict | None,
                 pct_dia: dict | None, plano_equipa: dict | None) -> tuple[dict[str, dict[str, float]], str | None]:
    """{jogador: {chave: alvo}} e a fonte («individual» | «equipa» | None).

    individual: pct_dia[k] % × fatores[k] × referência de jogo do jogador.
    equipa: o valor planeado da equipa para o dia (igual para todos)."""
    fatores = fatores or {}
    pct_dia = {k: float(v) for k, v in (pct_dia or {}).items() if v not in (None, "") and float(v) > 0}
    if pct_dia and any(float(fatores.get(k) or 0) > 0 for k in pct_dia):
        out = {}
        for jog in jogadores:
            r = refs.get(jog, {})
            out[jog] = {k: p / 100 * float(fatores[k]) * r[k] for k, p in pct_dia.items()
                        if float(fatores.get(k) or 0) > 0 and r.get(k)}
        return out, "individual"
    plano = {k: float(v) for k, v in (plano_equipa or {}).items() if v not in (None, "") and float(v) > 0}
    if plano:
        return {jog: dict(plano) for jog in jogadores}, "equipa"
    return {jog: {} for jog in jogadores}, None


def relatorio_treino(df: pd.DataFrame, dia: date, alvos: dict[str, dict[str, float]], fonte_alvo: str | None,
                     periodos: pd.DataFrame | None = None, exercicios_equipa: pd.DataFrame | None = None) -> dict:
    """Puro: `df` = sessões canónicas da equipa; `periodos` = gps_periodos
    canónicos da equipa (todas as datas, para a média de cada exercício)."""
    df = _preparar(df)
    if df.empty:
        return {"tem_dados": False}
    treinos = df[~mascara_jogo(df)]
    if "Tipo" in treinos.columns:
        treinos = treinos[treinos["Tipo"] != "Ginásio"]
    sessao = treinos[treinos["Data"].dt.date == dia]
    if sessao.empty:
        return {"tem_dados": False}

    metricas = _metricas_presentes(sessao)
    dia_md = sessao["Dia MD"].dropna().iloc[0] if "Dia MD" in sessao.columns and sessao["Dia MD"].notna().any() else None
    anteriores = treinos[treinos["Data"].dt.date < dia]
    if dia_md and "Dia MD" in anteriores.columns:
        anteriores_md = anteriores[anteriores["Dia MD"] == dia_md]
    else:
        anteriores_md = anteriores.iloc[0:0]
    recordes = _vmax_recordes(df)

    linhas = []
    for jog, g in sessao.groupby("Jogador"):
        minutos = float(g[COL_DURACAO].sum()) if COL_DURACAO in g.columns and g[COL_DURACAO].notna().any() else None
        hist = anteriores_md[anteriores_md["Jogador"] == jog]
        valores = {}
        for k in metricas:
            col = METRICAS[k][0]
            v = float(g[col].max()) if k == "vmax" else float(g[col].sum())
            alvo = alvos.get(jog, {}).get(k) if k in VOLUME else None
            pct = v / alvo * 100 if alvo else None
            refs_h = [float(x) for x in hist.groupby("Data")[col].agg("max" if k == "vmax" else "sum").dropna()] if not hist.empty else []
            c = classificar(v, refs_h)
            valores[k] = {
                "valor": _n(v, METRICAS[k][3]), "alvo": _n(alvo), "pct": _n(pct), "banda": banda(pct),
                "habitual": _n(sum(refs_h) / len(refs_h), METRICAS[k][3]) if refs_h else None,
                "habitual_dp": _n(_dp(refs_h), METRICAS[k][3]) if len(refs_h) >= 2 else None,
                "vs_habitual": c["estado"], "delta_pct": c["delta_pct"],
            }
        vmax = valores.get("vmax", {}).get("valor")
        rec = recordes.get(jog)
        # Banda do jogador = a da métrica principal (a distância, se tiver alvo).
        # Uma média de % entre métricas era dominada pelo sprint (alvos de
        # poucos metros fazem % enormes).
        principal = next((k for k in VOLUME if valores.get(k, {}).get("pct") is not None), None)
        pct_p = valores[principal]["pct"] if principal else None
        linhas.append({
            "jogador": jog, "posicao": _posicao(g), "minutos": _n(minutos),
            "dist_min": _n(_por_minuto(valores.get("distancia", {}).get("valor"), minutos), 1),
            "pct_vmax": _n(vmax / rec * 100, 0) if vmax and rec else None, "recorde_vmax": _n(rec, 1),
            "metrica_principal": principal, "pct_alvo": pct_p, "banda": banda(pct_p),
            "valores": valores,
        })
    ancora = "distancia" if "distancia" in metricas else (metricas[0] if metricas else None)
    linhas.sort(key=lambda r: -(r["valores"].get(ancora, {}).get("valor") or 0) if ancora else 0)

    # KPIs de equipa: média por jogador, % do alvo médio, contagem por banda.
    kpis = []
    for k in metricas:
        vals = [r["valores"][k]["valor"] for r in linhas if r["valores"][k]["valor"] is not None]
        pcts = [r["valores"][k]["pct"] for r in linhas if r["valores"][k]["pct"] is not None]
        kpis.append({"chave": k, "media": _n(sum(vals) / len(vals), METRICAS[k][3]) if vals else None,
                     "pct_alvo": _n(sum(pcts) / len(pcts)) if pcts else None,
                     "abaixo": sum(1 for p in pcts if p < 90), "dentro": sum(1 for p in pcts if 90 <= p <= 110),
                     "acima": sum(1 for p in pcts if p > 110)})
    bandas_jog = [r["banda"] for r in linhas if r["banda"]]
    resumo_alvo = {"abaixo": sum(1 for b in bandas_jog if b in ("muito_abaixo", "abaixo")),
                   "dentro": sum(1 for b in bandas_jog if b == "dentro"),
                   "acima": sum(1 for b in bandas_jog if b in ("acima", "muito_acima"))}

    exercicios, fonte_ex = _exercicios_treino(dia, periodos, exercicios_equipa)
    duracao = sessao[COL_DURACAO].max() if COL_DURACAO in sessao.columns else None
    return {
        "tem_dados": True, "data": dia.isoformat(), "dia_md": dia_md,
        "microciclo": int(sessao["Microciclo (Nr)"].dropna().iloc[0]) if "Microciclo (Nr)" in sessao.columns and sessao["Microciclo (Nr)"].notna().any() else None,
        "duracao_min": _n(duracao), "n_jogadores": len(linhas),
        "fonte_alvo": fonte_alvo, "n_habitual": int(anteriores_md["Data"].nunique()) if not anteriores_md.empty else 0,
        "metricas": _desc(metricas), "kpis": kpis, "resumo_alvo": resumo_alvo, "jogadores": linhas,
        "exercicios": exercicios, "fonte_exercicios": fonte_ex,
    }


def _exercicios_treino(dia: date, periodos: pd.DataFrame | None, exercicios_equipa: pd.DataFrame | None) -> tuple[dict | None, str | None]:
    """Exercícios do dia com a comparação com a média de cada exercício na época."""
    cols = {k: METRICAS[k][0] for k in VOLUME}
    if periodos is not None and not periodos.empty:
        p = periodos[periodos["Categoria"] == "exercicio"].copy()
        p["Data"] = pd.to_datetime(p["Data"], errors="coerce")
        hoje = p[p["Data"].dt.date == dia]
        if not hoje.empty:
            p["_nome"] = p["Período"].str.strip().str.lower()
            hoje = p[p["Data"].dt.date == dia]
            outros = p[p["Data"].dt.date != dia]
            itens, por_jogador = [], []
            for nome, g in sorted(hoje.groupby("_nome"), key=lambda t: t[1]["Ordem"].min()):
                dur = g[COL_DURACAO].median() if COL_DURACAO in g.columns else None
                item = {"exercicio": g["Período"].iloc[0], "n_jogadores": int(g["Jogador"].nunique()), "duracao_min": _n(dur)}
                min_tot = g[COL_DURACAO].sum() if COL_DURACAO in g.columns else 0
                for k, col in cols.items():
                    if col not in g.columns or g[col].isna().all():
                        continue
                    item[k] = _n(g[col].mean())
                    item[f"{k}_min"] = _n(g[col].sum() / min_tot, 2) if min_tot else None
                h = outros[outros["_nome"] == nome]
                d = "distancia" if "distancia_min" in item else None
                if d and not h.empty and COL_DURACAO in h.columns and h[COL_DURACAO].sum() > 0:
                    soma = h.groupby("Data")[[cols[d], COL_DURACAO]].sum()
                    soma = soma[soma[COL_DURACAO] > 0]
                    por_sessao = (soma[cols[d]] / soma[COL_DURACAO]).dropna()
                    if len(por_sessao):
                        media = float(por_sessao.mean())
                        item["media_epoca_min"] = _n(media, 2)
                        item["vs_epoca_pct"] = _n((item["distancia_min"] / media - 1) * 100) if media and item.get("distancia_min") is not None else None
                        item["n_epoca"] = int(len(por_sessao))
                itens.append(item)
                # Por jogador: intensidade (m/min) face à média da equipa NESTE exercício.
                med = item.get("distancia_min")
                for _, r in g.iterrows():
                    dm = _por_minuto(r.get(cols["distancia"]), r.get(COL_DURACAO))
                    por_jogador.append({
                        "jogador": r["Jogador"], "exercicio": item["exercicio"], "minutos": _n(r.get(COL_DURACAO)),
                        **{k: _n(r.get(col)) for k, col in cols.items() if col in g.columns},
                        "dist_min": _n(dm, 1), "vs_equipa_pct": _n((dm / med - 1) * 100) if dm is not None and med else None,
                    })
            return {"itens": itens, "por_jogador": por_jogador}, "jogador"
    if exercicios_equipa is not None and not exercicios_equipa.empty:
        e = exercicios_equipa.copy()
        e["Data"] = pd.to_datetime(e["Data"], errors="coerce")
        e["_nome"] = e["Exercício"].astype(str).str.strip().str.lower()
        hoje = e[e["Data"].dt.date == dia]
        if hoje.empty:
            return None, None
        outros = e[e["Data"].dt.date != dia]
        itens = []
        for _, r in hoje.iterrows():
            dur = r.get(COL_DURACAO)
            item = {"exercicio": r["Exercício"], "n_jogadores": _n(r.get("Nº Jogadores")), "duracao_min": _n(dur)}
            for k, col in cols.items():
                if col in e.columns and pd.notna(r.get(col)):
                    item[k] = _n(r[col])
                    item[f"{k}_min"] = _n(_por_minuto(r[col], dur), 2)
            h = outros[(outros["_nome"] == r["_nome"]) & (outros[COL_DURACAO] > 0)] if COL_DURACAO in outros.columns else outros.iloc[0:0]
            if not h.empty and item.get("distancia_min") is not None:
                media = float((h[cols["distancia"]] / h[COL_DURACAO]).mean())
                item["media_epoca_min"] = _n(media, 2)
                item["vs_epoca_pct"] = _n((item["distancia_min"] / media - 1) * 100) if media else None
                item["n_epoca"] = int(len(h))
            itens.append(item)
        return {"itens": itens, "por_jogador": []}, "equipa"
    return None, None


# ══════════════════════════════════════════════════════════════════════════
# Relatório de jogo
# ══════════════════════════════════════════════════════════════════════════
def _linha_jogo(g: pd.DataFrame, metricas: list[str]) -> dict:
    minutos = float(g[COL_DURACAO].sum()) if COL_DURACAO in g.columns and g[COL_DURACAO].notna().any() else None
    v = {}
    for k in metricas:
        col = METRICAS[k][0]
        if not g[col].notna().any():
            v[k] = None
        else:
            v[k] = float(g[col].max()) if k == "vmax" else float(g[col].sum())
    return {"minutos": minutos, "valores": v}


def relatorio_jogo(df: pd.DataFrame, dia: date, periodos: pd.DataFrame | None = None,
                   jogador: str | None = None, adversarios: dict[str, str] | None = None) -> dict:
    df = _preparar(df)
    if df.empty:
        return {"tem_dados": False}
    jogos = df[mascara_jogo(df)]
    jogo = jogos[jogos["Data"].dt.date == dia]
    if jogo.empty:
        return {"tem_dados": False}
    adversarios = adversarios or {}
    metricas = _metricas_presentes(jogo)
    dur = jogo[COL_DURACAO].max() if COL_DURACAO in jogo.columns and jogo[COL_DURACAO].notna().any() else None
    dur_ref = duracao_jogo(jogos) or (float(dur) if dur else None)
    minimo_completo = FRACAO_JOGO_COMPLETO * float(dur) if dur else None

    # Uma linha por jogador e jogo (todos os jogos — para a época de cada um).
    por_jogo: dict[tuple, dict] = {}
    for (jog, d), g in jogos.groupby(["Jogador", jogos["Data"].dt.date]):
        por_jogo[(jog, d)] = {**_linha_jogo(g, metricas), "posicao": _posicao(g)}

    def taxa(l, k):
        return l["valores"].get(k) if k == "vmax" else _por_minuto(l["valores"].get(k), l["minutos"])

    # ── Equipa: jogadores com jogo (quase) completo, face aos outros jogos ──
    def completos(d):
        dmax = max((l["minutos"] or 0) for (j, dd), l in por_jogo.items() if dd == d) or 0
        return [l for (j, dd), l in por_jogo.items() if dd == d and l["minutos"] and l["minutos"] >= FRACAO_JOGO_COMPLETO * dmax]
    datas = sorted({d for (_, d) in por_jogo})
    equipa_hoje = completos(dia)
    kpis = []
    for k in metricas:
        hoje_vals = [l["valores"][k] for l in equipa_hoje if l["valores"].get(k) is not None]
        epoca = [sum(vs) / len(vs) for d in datas if d != dia
                 for vs in [[l["valores"][k] for l in completos(d) if l["valores"].get(k) is not None]] if vs]
        media = sum(hoje_vals) / len(hoje_vals) if hoje_vals else None
        m_ep = sum(epoca) / len(epoca) if epoca else None
        kpis.append({"chave": k, "valor": _n(media, METRICAS[k][3]), "media_epoca": _n(m_ep, METRICAS[k][3]),
                     "delta_pct": _n((media / m_ep - 1) * 100) if media is not None and m_ep else None})

    # ── Jogadores: totais + estado POR MINUTO face à própria época ──────────
    linhas = []
    for (jog, d), l in sorted(por_jogo.items(), key=lambda t: -(t[1]["minutos"] or 0)):
        if d != dia:
            continue
        hist = [h for (j, dd), h in por_jogo.items() if j == jog and dd != dia and (h["minutos"] or 0) >= MIN_MINUTOS_HIST]
        valores = {}
        for k in metricas:
            atual = taxa(l, k)
            refs = [x for h in hist if (x := taxa(h, k)) is not None]
            c = classificar(atual, refs, limiar_z=1.0, limiar_pct=15.0)
            valores[k] = {"valor": _n(l["valores"].get(k), METRICAS[k][3]),
                          "por_min": _n(atual, 2) if k != "vmax" else None,
                          "media_epoca_min": _n(sum(refs) / len(refs), 2) if refs and k != "vmax" else None,
                          "media_epoca": _n(sum(refs) / len(refs), 1) if refs and k == "vmax" else None,
                          "estado": c["estado"], "delta_pct": c["delta_pct"]}
        linhas.append({"jogador": jog, "posicao": l["posicao"], "minutos": _n(l["minutos"]), "n_jogos_epoca": len(hist),
                       "dist_min": _n(_por_minuto(l["valores"].get("distancia"), l["minutos"]), 1), "valores": valores})

    # ── Perfil por posição: por jogo completo (taxa × duração de referência) ─
    posicoes = []
    if dur_ref:
        for pos in sorted({l["posicao"] for l in por_jogo.values() if l["posicao"] != "—"}):
            item = {"posicao": pos}
            for k in [m for m in ("distancia", "hsr", "sprint") if m in metricas]:
                def media_pos(filtro):
                    xs = [t * dur_ref for (j, d), l in por_jogo.items() if filtro(d) and l["posicao"] == pos
                          and (l["minutos"] or 0) >= MIN_MINUTOS_HIST and (t := taxa(l, k)) is not None]
                    return sum(xs) / len(xs) if xs else None
                h, e = media_pos(lambda d: d == dia), media_pos(lambda d: d != dia)
                item[k] = {"jogo": _n(h), "epoca": _n(e), "delta_pct": _n((h / e - 1) * 100) if h is not None and e else None}
            posicoes.append(item)

    partes = _partes_jogo(dia, periodos, metricas)
    out = {
        "tem_dados": True, "data": dia.isoformat(), "adversario": adversarios.get(dia.isoformat()),
        "duracao_min": _n(dur), "duracao_ref": _n(dur_ref), "minimo_completo": _n(minimo_completo),
        "n_completos": len(equipa_hoje), "n_jogos_epoca": len(datas) - 1,
        "metricas": _desc(metricas), "kpis": kpis, "jogadores": linhas, "posicoes": posicoes, "partes": partes,
        "min_minutos_hist": MIN_MINUTOS_HIST,
    }
    if jogador:
        out["individual"] = _individual_jogo(jogador, por_jogo, dia, metricas, periodos, adversarios)
    return out


def _partes_jogo(dia: date, periodos: pd.DataFrame | None, metricas: list[str]) -> dict | None:
    if periodos is None or periodos.empty:
        return None
    p = periodos[(periodos["Categoria"] == "parte")].copy()
    p["Data"] = pd.to_datetime(p["Data"], errors="coerce")
    p = p[p["Data"].dt.date == dia]
    if p.empty:
        return None
    nomes = [n for n, _ in sorted(p.groupby("Período")["Ordem"].min().items(), key=lambda t: t[1])]
    vol = [k for k in metricas if k in VOLUME]
    # Equipa: só quem jogou as duas primeiras partes (a comparação é justa).
    dois = nomes[:2]
    ambos = set.intersection(*[set(p[p["Período"] == n]["Jogador"]) for n in dois]) if len(dois) == 2 else set()
    equipa = []
    for n in nomes:
        g = p[(p["Período"] == n) & (p["Jogador"].isin(ambos) if ambos else True)]
        mins = g[COL_DURACAO].sum() if COL_DURACAO in g.columns else 0
        linha = {"periodo": n, "n_jogadores": int(g["Jogador"].nunique()), "minutos_medios": _n(g[COL_DURACAO].mean()) if COL_DURACAO in g.columns else None}
        for k in vol:
            col = METRICAS[k][0]
            if col in g.columns:
                linha[f"{k}_min"] = _n(g[col].sum() / mins, 2) if mins else None
        if "vmax" in metricas and METRICAS["vmax"][0] in g.columns:
            linha["vmax"] = _n(g[METRICAS["vmax"][0]].mean(), 1)
        equipa.append(linha)
    variacao = {}
    if len(equipa) >= 2:
        a, b = equipa[0], equipa[1]
        for k in [*vol, "vmax"]:
            ka = f"{k}_min" if k != "vmax" else "vmax"
            if a.get(ka) and b.get(ka) is not None:
                variacao[k] = _n((b[ka] / a[ka] - 1) * 100)
    por_jogador = []
    for jog, g in p.groupby("Jogador"):
        for _, r in g.sort_values("Ordem").iterrows():
            por_jogador.append({"jogador": jog, "periodo": r["Período"], "minutos": _n(r.get(COL_DURACAO)),
                                **{k: _n(r.get(METRICAS[k][0]), METRICAS[k][3]) for k in metricas if METRICAS[k][0] in g.columns}})
    return {"nomes": nomes, "equipa": equipa, "variacao_pct": variacao, "n_ambas": len(ambos), "por_jogador": por_jogador}


def _individual_jogo(jogador: str, por_jogo: dict, dia: date, metricas: list[str], periodos, adversarios) -> dict | None:
    hist = sorted(((d, l) for (j, d), l in por_jogo.items() if j == jogador), key=lambda t: t[0], reverse=True)
    if not hist:
        return None
    validos = [l for d, l in hist if (l["minutos"] or 0) >= MIN_MINUTOS_HIST]
    jogos = []
    for d, l in hist:
        outros = [h for dd, h in hist if dd != d and (h["minutos"] or 0) >= MIN_MINUTOS_HIST]
        vals = {}
        for k in metricas:
            atual = l["valores"].get(k) if k == "vmax" else _por_minuto(l["valores"].get(k), l["minutos"])
            refs = [x for h in outros if (x := (h["valores"].get(k) if k == "vmax" else _por_minuto(h["valores"].get(k), h["minutos"]))) is not None]
            vals[k] = {"valor": _n(l["valores"].get(k), METRICAS[k][3]),
                       "estado": classificar(atual, refs, limiar_z=1.0, limiar_pct=15.0)["estado"] if (l["minutos"] or 0) >= MIN_MINUTOS_HIST else "insuficiente"}
        jogos.append({"data": d.isoformat(), "adversario": adversarios.get(d.isoformat()), "minutos": _n(l["minutos"]),
                      "atual": d == dia, "valores": vals})
    media = {}
    for k in metricas:
        xs = [l["valores"][k] for l in validos if l["valores"].get(k) is not None]
        media[k] = _n(sum(xs) / len(xs), METRICAS[k][3]) if xs else None
    recordes = {}
    for k in metricas:
        melhor = max(((d, l["valores"][k]) for d, l in hist if l["valores"].get(k) is not None), key=lambda t: t[1], default=None)
        if melhor:
            recordes[k] = {"valor": _n(melhor[1], METRICAS[k][3]), "data": melhor[0].isoformat(), "adversario": adversarios.get(melhor[0].isoformat())}
    # Mostradores do jogo escolhido: por minuto (vmax em bruto) face aos outros
    # jogos válidos do jogador — média, ±1 DP, mín./máx. e posição no ranking.
    atual_l = next((l for d, l in hist if d == dia), None)
    gauges = {}
    if atual_l is not None:
        def taxa(l, k):
            return l["valores"].get(k) if k == "vmax" else _por_minuto(l["valores"].get(k), l["minutos"])
        for k in metricas:
            a = taxa(atual_l, k)
            outros = [x for d, l in hist if d != dia and (l["minutos"] or 0) >= MIN_MINUTOS_HIST and (x := taxa(l, k)) is not None]
            todos = sorted([*outros, a] if a is not None else outros, reverse=True)
            gauges[k] = {"valor": _n(a, 2 if k != "vmax" else 1), "total": _n(atual_l["valores"].get(k), METRICAS[k][3]),
                         "media": _n(sum(outros) / len(outros), 2) if outros else None,
                         "dp": _n(_dp(outros), 2) if len(outros) >= 2 else None,
                         "min": _n(min(outros), 2) if outros else None, "max": _n(max(outros), 2) if outros else None,
                         "rank": (todos.index(a) + 1) if a is not None else None, "n": len(todos),
                         "estado": classificar(a, outros, limiar_z=1.0, limiar_pct=15.0)["estado"] if (atual_l["minutos"] or 0) >= MIN_MINUTOS_HIST else "insuficiente"}
    mins = [l["minutos"] for l in validos if l["minutos"]]
    return {"jogador": jogador, "posicao": hist[0][1]["posicao"], "jogos": jogos, "gauges": gauges,
            "minutos_jogo": _n(atual_l["minutos"]) if atual_l else None,
            "media_epoca": media, "minutos_medios": _n(sum(mins) / len(mins)) if mins else None,
            "n_validos": len(validos), "recordes": recordes}


# ══════════════════════════════════════════════════════════════════════════
# Dados (BD)
# ══════════════════════════════════════════════════════════════════════════
PERIODO_DB = {"duracao_min": COL_DURACAO, "distancia_total_m": "Distância Total (m)", "hsr_m": "HSR (m)",
              "sprint_m": "Sprint (m)", "acc_n": "Acc (n)", "dcc_n": "Dcc (n)", "vel_max_kmh": "Vel. Máx (km/h)"}


def carregar_periodos(team_id: str) -> pd.DataFrame:
    """gps_periodos da equipa (jogadores ativos) com nomes canónicos. Vazio se
    a migração 0026 não estiver aplicada."""
    from app.core.db import get_conn
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""select p.nome, p.posicao, g.data, g.tipo, g.periodo, g.categoria, g.ordem,
                                       {', '.join('g.' + c for c in PERIODO_DB)}
                                from gps_periodos g join players p on p.id = g.player_id
                                where g.team_id = %s and p.ativo""", (team_id,))
                linhas = cur.fetchall()
    except Exception:
        return pd.DataFrame()
    df = pd.DataFrame(linhas, columns=["Jogador", "Posição", "Data", "Tipo", "Período", "Categoria", "Ordem", *PERIODO_DB.values()])
    for c in PERIODO_DB.values():
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _exercicios_equipa(team_id: str) -> pd.DataFrame:
    from app.core.db import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""select data, exercicio, n_jogadores, duracao_min, distancia_total_m, hsr_m, sprint_m, acc_n, dcc_n
                           from exercises where team_id = %s and data is not null and exercicio is not null""", (team_id,))
            linhas = cur.fetchall()
    df = pd.DataFrame(linhas, columns=["Data", "Exercício", "Nº Jogadores", COL_DURACAO, "Distância Total (m)", "HSR (m)", "Sprint (m)", "Acc (n)", "Dcc (n)"])
    for c in df.columns[2:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _df_equipa(team_id: str) -> pd.DataFrame:
    from app.services.dados_equipa import carregar_df_equipa
    return _preparar(carregar_df_equipa(team_id))


def _escolher(datas_desc: list[date], data: str | None) -> date:
    """A data pedida se tiver sessão; senão a sessão mais próxima antes dela
    (ou a mais recente). Ao trocar entre os separadores Treino/Jogo a data
    vem do outro relatório e raramente é um dia do mesmo tipo."""
    if not data:
        return datas_desc[0]
    pedido = date.fromisoformat(data)
    if pedido in datas_desc:
        return pedido
    return next((d for d in datas_desc if d <= pedido), datas_desc[-1])


def obter_treino(team_id: str, data: str | None = None) -> dict:
    from app.core.db import get_conn
    from app.services.semana_jogadores_service import refs_por_jogador

    df = _df_equipa(team_id)
    if df.empty:
        return {"tem_dados": False, "sessoes": []}
    treinos = df[~mascara_jogo(df)]
    if "Tipo" in treinos.columns:
        treinos = treinos[treinos["Tipo"] != "Ginásio"]
    md = treinos.groupby(treinos["Data"].dt.date)["Dia MD"].first() if "Dia MD" in treinos.columns else pd.Series(dtype=object)
    datas = sorted(set(treinos["Data"].dt.date), reverse=True)
    sessoes = [{"data": d.isoformat(), "dia_md": md.get(d) if not md.empty and pd.notna(md.get(d)) else None} for d in datas[:120]]
    if not datas:
        return {"tem_dados": False, "sessoes": []}
    dia = _escolher(datas, data)

    jogadores = {j: _posicao(g) for j, g in df.groupby("Jogador")}
    fatores, pct_dia, plano_equipa = None, None, None
    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""select numero, fatores, dias from microciclos
                               where team_id = %s and data_inicio <= %s and data_fim >= %s limit 1""", (team_id, dia, dia))
                r = cur.fetchone()
            except Exception:
                conn.rollback()
                r = None
            if r:
                numero, fatores, dias = r
                fatores = json.loads(fatores) if isinstance(fatores, str) else (fatores or {})
                dias = json.loads(dias) if isinstance(dias, str) else (dias or {})
                pct_dia = (dias.get(dia.isoformat()) or {}).get("pct")
                dia_md = (dias.get(dia.isoformat()) or {}).get("dia_md")
                if not pct_dia and dia_md:
                    try:
                        cur.execute("""select distancia_m, hsr_m, sprint_m, acc_n, dcc_n from carga_externa_planeada
                                       where team_id = %s and microciclo_nr = %s and dia_md = %s""", (team_id, numero, dia_md))
                        p = cur.fetchone()
                        if p:
                            plano_equipa = dict(zip(VOLUME, p))
                    except Exception:
                        conn.rollback()
    refs = refs_por_jogador(df, jogadores) if pct_dia else {}
    alvos, fonte = alvos_do_dia(jogadores, refs, fatores, pct_dia, plano_equipa)
    periodos = carregar_periodos(team_id)
    ex_equipa = _exercicios_equipa(team_id) if periodos.empty or not (pd.to_datetime(periodos["Data"]).dt.date == dia).any() else None
    out = relatorio_treino(df, dia, alvos, fonte, periodos, ex_equipa)
    out["sessoes"] = sessoes
    return out


def obter_jogo(team_id: str, data: str | None = None, jogador: str | None = None) -> dict:
    from app.core.db import get_conn

    df = _df_equipa(team_id)
    if df.empty:
        return {"tem_dados": False, "jogos": []}
    jogos = df[mascara_jogo(df)]
    datas = sorted(set(jogos["Data"].dt.date), reverse=True)
    if not datas:
        return {"tem_dados": False, "jogos": []}
    adversarios: dict[str, str] = {}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("select data, adversario from jogos where team_id = %s", (team_id,))
                adversarios = {d.isoformat(): a for d, a in cur.fetchall()}
    except Exception:
        pass
    dia = _escolher(datas, data)
    out = relatorio_jogo(df, dia, carregar_periodos(team_id), jogador, adversarios)
    out["jogos"] = [{"data": d.isoformat(), "adversario": adversarios.get(d.isoformat())} for d in datas]
    return out
