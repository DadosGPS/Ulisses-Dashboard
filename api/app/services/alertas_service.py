from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
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


@dataclass
class PlayerAlert:
    player_id: str
    player_name: str
    status: str
    primary_reason: str
    reason_text: str
    metric_value: str


def classificar_acwr(valor: Any, limites: dict[str, float] | None = None) -> tuple[int, str]:
    """Classifica um ACWR usando os limiares configuráveis (limites_service).

    Fonte única de verdade da classificação de ACWR, partilhada pelo motor de
    alertas do dashboard (evaluate_player_alert) e pela página Análise
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


def evaluate_player_alert(metrics: dict[str, Any], limites: dict[str, float] | None = None) -> PlayerAlert:
    from app.services.limites_service import DEFAULTS
    lim = {**DEFAULTS, **(limites or {})}

    player_id = str(metrics.get("player_id", "unknown"))
    player_name = str(metrics.get("player_name", "Jogador"))

    acwr = float(metrics.get("acwr") or 0.0)
    weekly_load_change = float(metrics.get("weekly_load_change") or 0.0)
    wellness_change = float(metrics.get("wellness_change") or 0.0)
    hsr_change = float(metrics.get("hsr_change") or 0.0)
    velocity_drop = float(metrics.get("velocity_drop") or 0.0)
    is_absent = bool(metrics.get("is_absent"))
    freshness_hours = float(metrics.get("freshness_hours") or 0.0)

    reasons: list[str] = []
    severity = 0

    sev_acwr, _ = classificar_acwr(acwr, lim)
    if sev_acwr >= 2 or weekly_load_change >= lim["carga_change_muito_alto"]:
        reasons.append("high-load-change")
        severity += 2
    elif sev_acwr >= 1 or weekly_load_change >= lim["carga_change_alto"]:
        reasons.append("high-load-change")
        severity += 1

    if wellness_change >= lim["wellness_change_muito_alto"]:
        reasons.append("poor-wellness")
        severity += 2
    elif wellness_change >= lim["wellness_change_alto"]:
        reasons.append("poor-wellness")
        severity += 1

    if hsr_change >= lim["hsr_change_muito_alto"]:
        reasons.append("high-hsr-exposure")
        severity += 2
    elif hsr_change >= lim["hsr_change_alto"]:
        reasons.append("high-hsr-exposure")
        severity += 1

    if velocity_drop >= lim["velocidade_queda_muito_alto"]:
        reasons.append("velocity-drop")
        severity += 2
    elif velocity_drop >= lim["velocidade_queda_alto"]:
        reasons.append("velocity-drop")
        severity += 1

    if is_absent:
        reasons.append("absence")
        severity = max(severity, 1)

    if freshness_hours > lim["dados_horas"]:
        reasons.append("data-missing")
        severity = max(severity, 1)

    if severity >= 3:
        status = ALERT_STATUS_HIGH_ATTENTION
    elif severity >= 1:
        status = ALERT_STATUS_ATTENTION
    else:
        status = ALERT_STATUS_NORMAL

    primary_reason = reasons[0] if reasons else "data-missing"
    reason_text = {
        "high-load-change": "Carga semanal elevada",
        "poor-wellness": "Bem-estar reduzido",
        "high-hsr-exposure": "Exposição HSR elevada",
        "velocity-drop": "Queda de velocidade",
        "absence": "Jogador indisponível",
        "data-missing": "Sem dados recentes",
    }.get(primary_reason, "Atenção ao jogador")

    metric_value = ""
    if primary_reason == "high-load-change":
        metric_value = f"ACWR {acwr:.2f} • +{weekly_load_change:.0f}% vs semana anterior"
    elif primary_reason == "poor-wellness":
        metric_value = f"Wellness {metrics.get('wellness_score', 0):.1f} • -{wellness_change:.0f}% vs baseline"
    elif primary_reason == "high-hsr-exposure":
        metric_value = f"HSR {metrics.get('hsr_value', 0):.0f}m • +{hsr_change:.0f}% vs baseline"
    elif primary_reason == "velocity-drop":
        metric_value = f"Vel. máx {metrics.get('velocity_value', 0):.1f} km/h • -{velocity_drop:.0f}%"
    elif primary_reason == "absence":
        metric_value = f"Estado: {metrics.get('player_state', 'indisponível')}"
    else:
        metric_value = f"Dados há {freshness_hours:.0f}h"

    return PlayerAlert(
        player_id=player_id,
        player_name=player_name,
        status=status,
        primary_reason=primary_reason,
        reason_text=reason_text,
        metric_value=metric_value,
    )


def build_alerts_for_team(rows: list[dict[str, Any]], team_state: dict[str, dict[str, Any]], limites: dict[str, float] | None = None) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        player_id = str(row.get("player_id") or row.get("Jogador") or "unknown")
        grouped.setdefault(player_id, []).append(row)

    alerts: list[dict[str, str]] = []
    for player_id, player_rows in grouped.items():
        player_rows = sorted(player_rows, key=lambda item: item.get("Data") or datetime.now(timezone.utc))
        latest = player_rows[-1]
        player_name = str(latest.get("Jogador") or "Jogador")
        player_state = str(team_state.get(player_id, {}).get("estado", "")).lower()
        is_absent = player_state in {"lesionado", "em_recuperacao", "ausente"}

        load_values = []
        for row in player_rows:
            value = row.get("Carga Interna")
            try:
                load_values.append(float(value))
            except (TypeError, ValueError):
                pass

        if len(load_values) >= 8:
            recent_load = sum(load_values[-7:])
            prior_load = sum(load_values[-14:-7]) if len(load_values) > 7 else 0.0
        else:
            recent_load = sum(load_values)
            prior_load = 0.0

        weekly_load_change = ((recent_load - prior_load) / prior_load * 100.0) if prior_load else 0.0

        acute_load = recent_load
        chronic_load = sum(load_values[-28:-7]) / max(len(load_values[-28:-7]), 1) if len(load_values) > 7 else acute_load
        acwr = acute_load / chronic_load if chronic_load else 0.0

        wellness_values = []
        for row in player_rows:
            value = row.get("Hooper Index")
            try:
                wellness_values.append(float(value))
            except (TypeError, ValueError):
                pass
        latest_wellness = wellness_values[-1] if wellness_values else 0.0
        baseline_wellness = sum(wellness_values) / len(wellness_values) if wellness_values else latest_wellness
        wellness_change = ((baseline_wellness - latest_wellness) / baseline_wellness * 100.0) if baseline_wellness else 0.0

        hsr_values = []
        for row in player_rows:
            value = row.get("HSR (m)")
            try:
                hsr_values.append(float(value))
            except (TypeError, ValueError):
                pass
        latest_hsr = hsr_values[-1] if hsr_values else 0.0
        baseline_hsr = sum(hsr_values) / len(hsr_values) if hsr_values else latest_hsr
        hsr_change = ((latest_hsr - baseline_hsr) / baseline_hsr * 100.0) if baseline_hsr else 0.0

        velocity_values = []
        for row in player_rows:
            value = row.get("Vel. Máx (km/h)")
            try:
                velocity_values.append(float(value))
            except (TypeError, ValueError):
                pass
        velocity_value = velocity_values[-1] if velocity_values else 0.0
        previous_velocity = velocity_values[-2] if len(velocity_values) > 1 else velocity_value
        velocity_drop = ((previous_velocity - velocity_value) / previous_velocity * 100.0) if previous_velocity else 0.0

        last_data = player_rows[-1].get("Data")
        freshness_hours = 0.0
        if last_data is not None:
            try:
                if isinstance(last_data, str):
                    last_date = datetime.fromisoformat(last_data)
                else:
                    last_date = last_data
                freshness_hours = (datetime.now(timezone.utc) - last_date.replace(tzinfo=timezone.utc) if last_date.tzinfo else last_date).total_seconds() / 3600.0
            except Exception:
                freshness_hours = 0.0

        alert = evaluate_player_alert({
            "player_id": player_id,
            "player_name": player_name,
            "acwr": acwr,
            "weekly_load_change": weekly_load_change,
            "wellness_change": wellness_change,
            "wellness_score": latest_wellness,
            "hsr_change": hsr_change,
            "hsr_value": latest_hsr,
            "velocity_drop": velocity_drop,
            "velocity_value": velocity_value,
            "is_absent": is_absent,
            "freshness_hours": freshness_hours,
            "player_state": player_state or "indisponível",
        }, limites)

        alerts.append({
            "player_id": alert.player_id,
            "player_name": alert.player_name,
            "status": alert.status,
            "primary_reason": alert.primary_reason,
            "reason_text": alert.reason_text,
            "metric_value": alert.metric_value,
        })

    return sorted(
        alerts,
        key=lambda item: (0 if item["status"] == ALERT_STATUS_HIGH_ATTENTION else 1 if item["status"] == ALERT_STATUS_ATTENTION else 2),
    )


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
