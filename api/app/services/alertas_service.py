from __future__ import annotations

from typing import Any


ALERT_STATUS_NORMAL = "normal"
ALERT_STATUS_ATTENTION = "attention"
ALERT_STATUS_HIGH_ATTENTION = "high-attention"

# ── Avisos do dashboard (modelo de exposição) ───────────────────────────────
# O dashboard mostra APENAS três sinais, pedidos pelo preparador físico:
#   1. ACWR acima do limiar (limites.acwr_alto, por omissão 1.30);
#   2. Velocidade máxima que não atinge VMAX_PCT_MIN% do recorde nos últimos
#      VMAX_JANELA_DIAS dias (pouco estímulo de velocidade);
#   3. Rácio de exposição HSR/Sprint da SEMANA (carga acumulada do microciclo)
#      face ao jogo mais exigente (match benchmark), com zonas de referência de
#      Buchheit configuráveis (limites.hsr_semana_* / sprint_semana_*).
#
# As zonas são um modelo de risco, não valores ótimos universais: devem ser
# lidas no contexto do microciclo, posição, histórico e dias entre jogos.
VMAX_PCT_MIN = 90.0
VMAX_JANELA_DIAS = 7


def classificar_acwr(valor: Any, limites: dict[str, float] | None = None) -> tuple[int, str]:
    """Classifica um ACWR usando os limiares configuráveis (limites_service).

    Fonte única de verdade da classificação de ACWR, partilhada pelos avisos do
    dashboard (construir_avisos_dashboard) e pela página Análise
    (analise_service). Devolve (severidade, estado):
      - severidade: 0 (ok/sub-carga), 1 (atenção), 2 (risco);
      - estado: rótulo com emoji, idêntico ao de utils.calculos.cor_acwr quando
        os limiares estão nos valores por omissão (1.3 / 1.5).
    """
    from app.services.limites_service import DEFAULTS
    lim = {**DEFAULTS, **(limites or {})}
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return 0, "❓"
    if v != v:  # NaN
        return 0, "❓"
    if v >= lim["acwr_muito_alto"]:
        return 2, "🔴 RISCO"
    if v >= lim["acwr_alto"]:
        return 1, "🟡 ATENÇÃO"
    if v >= 0.8:
        return 0, "🟢 OK"
    return 0, "🔵 SUB-CARGA"


def _zona_ratio(r: float | None, ref: tuple[float, float]) -> str | None:
    """Classifica um rácio de exposição face à zona de referência (Buchheit)."""
    if r is None:
        return None
    baixo, alto = ref
    if r < baixo:
        return "baixo"
    if r > alto:
        return "alto"
    return "ok"


def construir_avisos_dashboard(df, limites: dict[str, float] | None = None) -> list[dict[str, str]]:
    """Avisos do dashboard — apenas três sinais (ver constantes no topo):

      1. ACWR > limites.acwr_alto (por omissão 1.30);
      2. Vmax que não atinge VMAX_PCT_MIN% do recorde nos últimos
         VMAX_JANELA_DIAS dias;
      3. Rácio de exposição HSR/Sprint do microciclo mais recente face ao jogo
         mais exigente do jogador, fora da zona de referência.

    Devolve um item por jogador (status "normal" quando não há sinais), na mesma
    forma que o frontend do dashboard já consome.
    """
    import pandas as pd

    from app.services.limites_service import DEFAULTS
    from utils.calculos import calcular_acwr_global

    lim = {**DEFAULTS, **(limites or {})}
    if df is None or df.empty or "Jogador" not in df.columns:
        return []

    df = df.copy()
    if "Data" in df.columns:
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")

    acwr_dict = calcular_acwr_global(df)

    # Janela recente para a exposição HSR/Sprint: microciclo mais recente se
    # existir, senão últimos 7 dias. Só treinos (o jogo é a referência).
    if "Microciclo (Nr)" in df.columns and df["Microciclo (Nr)"].notna().any():
        mc_atual = df["Microciclo (Nr)"].dropna().max()
        recente = df[df["Microciclo (Nr)"] == mc_atual]
    elif "Data" in df.columns and df["Data"].notna().any():
        ref = df["Data"].max()
        recente = df[df["Data"] >= ref - pd.Timedelta(days=VMAX_JANELA_DIAS)]
    else:
        recente = df
    treinos_recentes = recente[recente["Tipo"] != "Jogo"] if "Tipo" in recente.columns else recente
    jogos = df[df["Tipo"] == "Jogo"] if "Tipo" in df.columns else df.iloc[0:0]

    # Janela de 7 dias para o estímulo de velocidade (independente do microciclo).
    vmax_janela = df
    if "Data" in df.columns and df["Data"].notna().any():
        refv = df["Data"].max()
        vmax_janela = df[df["Data"] >= refv - pd.Timedelta(days=VMAX_JANELA_DIAS)]

    avisos: list[dict[str, str]] = []
    for jog in sorted(df["Jogador"].dropna().unique().tolist()):
        gfull = df[df["Jogador"] == jog]
        player_id = (
            str(gfull["player_id"].dropna().iloc[0])
            if "player_id" in gfull.columns and gfull["player_id"].notna().any()
            else str(jog)
        )
        # sinais: (severidade, chave, texto, valor)
        sinais: list[tuple[int, str, str, str]] = []

        # 1) ACWR
        v_acwr = acwr_dict.get(jog, {}).get("acwr")
        sev_acwr, _ = classificar_acwr(v_acwr, lim)
        if sev_acwr >= 1 and v_acwr is not None and pd.notna(v_acwr):
            sinais.append((sev_acwr, "acwr", "ACWR elevado",
                           f"ACWR {float(v_acwr):.2f} · limite {lim['acwr_alto']:.2f}"))

        # 2) Vmax < 90% do recorde nos últimos 7 dias
        if "Vel. Máx (km/h)" in gfull.columns and gfull["Vel. Máx (km/h)"].notna().any():
            recorde = float(gfull["Vel. Máx (km/h)"].max())
            g7 = vmax_janela[vmax_janela["Jogador"] == jog]
            if recorde > 0 and "Vel. Máx (km/h)" in g7.columns and g7["Vel. Máx (km/h)"].notna().any():
                pct7 = float(g7["Vel. Máx (km/h)"].max()) / recorde * 100.0
                if pct7 < VMAX_PCT_MIN:
                    sinais.append((1, "vmax", "Pouco estímulo de velocidade",
                                   f"{pct7:.0f}% do recorde em {VMAX_JANELA_DIAS} dias · mín {VMAX_PCT_MIN:.0f}%"))

        # 3) Exposição HSR / Sprint da SEMANA (carga acumulada do microciclo)
        #    vs jogo mais exigente.
        gj = jogos[jogos["Jogador"] == jog] if not jogos.empty else jogos
        gt = treinos_recentes[treinos_recentes["Jogador"] == jog]
        for col, chaves, etiqueta in (
            ("HSR (m)", ("hsr_semana_baixo", "hsr_semana_alto"), "HSR"),
            ("Sprint (m)", ("sprint_semana_baixo", "sprint_semana_alto"), "Sprint"),
        ):
            ref = (lim[chaves[0]], lim[chaves[1]])
            if ref[1] <= 0:  # zonas desligadas → sem aviso para esta métrica
                continue
            if col not in df.columns or gj.empty or gt.empty:
                continue
            if gj[col].dropna().empty or gt[col].dropna().empty:
                continue
            match_val = float(gj[col].max())  # jogo mais exigente
            if match_val <= 0:
                continue
            treino_val = float(gt[col].sum())  # carga ACUMULADA da semana (microciclo)
            r = treino_val / match_val
            zona = _zona_ratio(r, ref)
            if zona == "baixo":
                sinais.append((1, f"{etiqueta.lower()}_baixo", f"Exposição {etiqueta} baixa",
                               f"{etiqueta} semana {r:.2f}× jogo · ref {ref[0]:.2f}–{ref[1]:.2f}"))
            elif zona == "alto":
                sinais.append((1, f"{etiqueta.lower()}_alto", f"Exposição {etiqueta} elevada",
                               f"{etiqueta} semana {r:.2f}× jogo · ref {ref[0]:.2f}–{ref[1]:.2f}"))

        if not sinais:
            avisos.append({"player_id": player_id, "player_name": str(jog), "status": ALERT_STATUS_NORMAL,
                           "primary_reason": "ok", "reason_text": "Sem sinais", "metric_value": ""})
            continue

        sinais.sort(key=lambda s: -s[0])
        total_sev = sum(s[0] for s in sinais)
        topo = sinais[0]
        status = ALERT_STATUS_HIGH_ATTENTION if total_sev >= 2 else ALERT_STATUS_ATTENTION
        avisos.append({"player_id": player_id, "player_name": str(jog), "status": status,
                       "primary_reason": topo[1], "reason_text": topo[2], "metric_value": topo[3]})

    ordem = {ALERT_STATUS_HIGH_ATTENTION: 0, ALERT_STATUS_ATTENTION: 1, ALERT_STATUS_NORMAL: 2}
    avisos.sort(key=lambda a: ordem.get(a["status"], 3))
    return avisos


def obter_exposicao_semana(df, limites: dict[str, float] | None = None) -> dict:
    """Exposição HSR/Sprint da SEMANA (carga acumulada do microciclo mais
    recente) ÷ jogo mais exigente, por jogador — para um painel SEMPRE VISÍVEL
    no dashboard.

    Ao contrário dos avisos (que só surgem fora da zona de referência), isto
    mostra os rácios mesmo quando estão dentro da zona, e explica porque está
    vazio (sem jogos, sem HSR/Sprint…) em vez de simplesmente não aparecer.
    """
    import pandas as pd

    from app.services.limites_service import DEFAULTS

    lim = {**DEFAULTS, **(limites or {})}
    vazio = {"tem_dados": False, "motivo": None, "microciclo": None, "metricas": []}

    if df is None or df.empty or "Jogador" not in df.columns:
        return {**vazio, "motivo": "Ainda não há dados carregados."}
    if "Tipo" not in df.columns:
        return {**vazio, "motivo": "Os dados não têm a coluna «Tipo» (treino/jogo)."}

    df = df.copy()
    if "Data" in df.columns:
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")

    jogos = df[df["Tipo"] == "Jogo"]
    if jogos.empty:
        return {**vazio, "motivo": "Sem jogos registados — o rácio precisa de pelo menos um jogo como referência."}

    if "Microciclo (Nr)" in df.columns and df["Microciclo (Nr)"].notna().any():
        mc = df["Microciclo (Nr)"].dropna().max()
        recente = df[df["Microciclo (Nr)"] == mc]
        microciclo = int(mc)
    elif "Data" in df.columns and df["Data"].notna().any():
        ref = df["Data"].max()
        recente = df[df["Data"] >= ref - pd.Timedelta(days=VMAX_JANELA_DIAS)]
        microciclo = None
    else:
        recente = df
        microciclo = None
    treinos = recente[recente["Tipo"] != "Jogo"]
    if treinos.empty:
        return {**vazio, "motivo": "O microciclo mais recente ainda não tem treinos.", "microciclo": microciclo}

    metricas_def = [
        ("HSR (m)", ("hsr_semana_baixo", "hsr_semana_alto"), "hsr", "HSR"),
        ("Sprint (m)", ("sprint_semana_baixo", "sprint_semana_alto"), "sprint", "Sprint"),
    ]
    metricas = []
    for col, chaves, chave, label in metricas_def:
        if col not in df.columns or jogos[col].dropna().empty:
            continue
        ref = (lim[chaves[0]], lim[chaves[1]])
        jogadores = []
        for jog in sorted(treinos["Jogador"].dropna().unique().tolist()):
            gt = treinos[treinos["Jogador"] == jog]
            gj = jogos[jogos["Jogador"] == jog]
            if gt[col].dropna().empty or gj[col].dropna().empty:
                continue
            match_val = float(gj[col].max())
            if match_val <= 0:
                continue
            r = float(gt[col].sum()) / match_val
            jogadores.append({"jogador": jog, "ratio": round(r, 2), "zona": _zona_ratio(r, ref)})
        if not jogadores:
            continue
        jogadores.sort(key=lambda x: x["ratio"])
        ratios = [j["ratio"] for j in jogadores]
        ratio_equipa = round(sum(ratios) / len(ratios), 2)
        metricas.append({
            "chave": chave, "label": label, "ref": [ref[0], ref[1]],
            "ratio_equipa": ratio_equipa, "zona_equipa": _zona_ratio(ratio_equipa, ref),
            "jogadores": jogadores,
        })

    if not metricas:
        return {**vazio, "motivo": "Sem HSR/Sprint suficientes no microciclo e nos jogos.", "microciclo": microciclo}
    return {"tem_dados": True, "motivo": None, "microciclo": microciclo, "metricas": metricas}
