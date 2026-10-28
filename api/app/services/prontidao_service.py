"""Prontidão do jogador — junta três sinais num só estado diário:

  1. CMJ (altura de salto) do último teste face à média dos testes anteriores
     do PRÓPRIO jogador — queda = fadiga neuromuscular;
  2. Hooper (0–16, alto = pior) mais recente face à média do próprio jogador
     nos 28 dias anteriores — subida = pior bem-estar;
  3. ACWR diário (EWMA, descanso = 0) e a sua tendência na última semana.

Cada sinal dá severidade 0/1/2 pelos limiares configuráveis
(limites_service). Soma ≥ 3 → «reduzir»; ≥ 1 → «vigiar»; 0 → «pronto».
Comparar o jogador consigo próprio (e não com o plantel) é o padrão em
monitorização: a variabilidade entre atletas é muito maior do que dentro de
cada atleta.
"""
from __future__ import annotations

import pandas as pd

from app.services.alertas_service import classificar_acwr
from app.services.limites_service import DEFAULTS
from utils.calculos import serie_acwr_diaria

N_TESTES_BASE = 6          # testes anteriores usados como baseline do CMJ
CMJ_VALIDADE_DIAS = 21     # um teste mais antigo do que isto não conta para hoje
HOOPER_BASE_DIAS = 28
HOOPER_VALIDADE_DIAS = 3   # o Hooper tem de ser dos últimos 3 dias
TENDENCIA_DIAS = 7
SERIE_DIAS = 28
TENDENCIA_LIMIAR = 0.10    # variação do ACWR em 7 dias considerada subida/descida


def sev_cmj(c: dict | None, lim: dict) -> int:
    """Severidade da queda do CMJ (0/1/2), partilhada pela Prontidão e pelos
    avisos. A queda tem de passar o limiar em % E, quando o atleta já tem
    testes suficientes, estar fora da SUA variação habitual (ver variacao):
    num atleta que varia ±6 % entre testes, −5 % é ruído, não fadiga."""
    if not c or not c.get("valido") or c.get("variacao_pct") is None:
        return 0
    sev = _sev(-c["variacao_pct"], lim["cmj_queda_alto"], lim["cmj_queda_muito_alto"])
    if sev and c.get("metodo") == "variacao" and c.get("estado_habitual") != "baixo":
        return 0
    return sev


def _cmj(testes: pd.DataFrame, hoje: pd.Timestamp) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if testes is None or testes.empty or "altura_salto_cm" not in testes.columns:
        return out
    t = testes.dropna(subset=["nome", "data", "altura_salto_cm"]).copy()
    t["data"] = pd.to_datetime(t["data"])
    t["altura_salto_cm"] = pd.to_numeric(t["altura_salto_cm"], errors="coerce")
    t = t.dropna(subset=["altura_salto_cm"]).sort_values("data")
    for jog, g in t.groupby("nome"):
        ultimo = g.iloc[-1]
        base = g.iloc[:-1].tail(N_TESTES_BASE)["altura_salto_cm"]
        media = float(base.mean()) if not base.empty else None
        var = round((float(ultimo["altura_salto_cm"]) - media) / media * 100, 1) if media else None
        dias = int((hoje - ultimo["data"]).days)
        from app.services.variacao import classificar
        hab = classificar(float(ultimo["altura_salto_cm"]), [float(v) for v in base])
        out[jog] = {
            "ultimo": round(float(ultimo["altura_salto_cm"]), 1),
            "metodo": hab["metodo"], "estado_habitual": hab["estado"], "tipico_pct": hab["tipico_pct"],
            "data": ultimo["data"].strftime("%Y-%m-%d"),
            "media_base": round(media, 1) if media else None,
            "n_base": int(len(base)),
            "variacao_pct": var,
            "dias_desde": dias,
            "valido": dias <= CMJ_VALIDADE_DIAS and var is not None,
        }
    return out


def _hooper(df: pd.DataFrame, hoje: pd.Timestamp) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if "Hooper Index" not in df.columns:
        return out
    h = df.dropna(subset=["Jogador", "Data", "Hooper Index"]).sort_values("Data")
    for jog, g in h.groupby("Jogador"):
        ultimo = g.iloc[-1]
        data = ultimo["Data"]
        base = g[(g["Data"] < data) & (g["Data"] >= data - pd.Timedelta(days=HOOPER_BASE_DIAS))]["Hooper Index"]
        media = float(base.mean()) if not base.empty else None
        dif = round(float(ultimo["Hooper Index"]) - media, 1) if media is not None else None
        dias = int((hoje - data).days)
        out[jog] = {
            "ultimo": round(float(ultimo["Hooper Index"]), 1),
            "data": data.strftime("%Y-%m-%d"),
            "media_base": round(media, 1) if media is not None else None,
            "diferenca": dif,
            "dias_desde": dias,
            "valido": dias <= HOOPER_VALIDADE_DIAS,
        }
    return out


def _acwr(df: pd.DataFrame) -> dict[str, dict]:
    out: dict[str, dict] = {}
    serie = serie_acwr_diaria(df)
    if serie.empty:
        return out
    for jog, g in serie.dropna(subset=["ACWR"]).groupby("Jogador"):
        g = g.sort_values("Data")
        atual = float(g.iloc[-1]["ACWR"])
        ref_data = g.iloc[-1]["Data"] - pd.Timedelta(days=TENDENCIA_DIAS)
        antes = g[g["Data"] <= ref_data]
        ha7 = float(antes.iloc[-1]["ACWR"]) if not antes.empty else None
        if ha7 is None:
            tendencia = None
        elif atual - ha7 > TENDENCIA_LIMIAR:
            tendencia = "a_subir"
        elif ha7 - atual > TENDENCIA_LIMIAR:
            tendencia = "a_descer"
        else:
            tendencia = "estavel"
        recente = g.tail(SERIE_DIAS)
        out[jog] = {
            "atual": round(atual, 2),
            "ha_7_dias": round(ha7, 2) if ha7 is not None else None,
            "tendencia": tendencia,
            "serie": [round(float(v), 2) for v in recente["ACWR"]],
        }
    return out


def _pt(v: float, casas: int = 1, sinal: bool = False) -> str:
    """Número com vírgula decimal (pt-PT) para os textos mostrados ao staff."""
    txt = f"{v:+.{casas}f}" if sinal else f"{v:.{casas}f}"
    return txt.replace(".", ",")


def _sev(valor: float | None, alto: float, muito: float) -> int:
    if valor is None:
        return 0
    if valor >= muito:
        return 2
    if valor >= alto:
        return 1
    return 0


def calcular_prontidao(
    df: pd.DataFrame,
    testes: pd.DataFrame | None,
    estados: dict[str, str] | None = None,
    limites: dict[str, float] | None = None,
    hoje: pd.Timestamp | None = None,
) -> dict:
    """Parte pura (testável). `estados` = {jogador: estado} (apto, lesionado,
    em_recuperacao, ausente); `testes` = colunas nome, data, altura_salto_cm.

    `hoje` = o dia real (obter_prontidao passa a data de hoje). A validade do
    CMJ (21 dias) e do Hooper (3 dias) conta a partir daqui: antes contava a
    partir do último dia com dados, e se ninguém importasse nada durante uma
    semana o Hooper de há uma semana ainda aparecia como «de hoje». Sem
    `hoje` usa o último dia com dados (comportamento antigo, para os testes)."""
    lim = {**DEFAULTS, **(limites or {})}
    vazio = {"tem_dados": False, "motivo": "Ainda não há sessões.", "jogadores": [], "resumo": {}}
    if df is None or df.empty or "Jogador" not in df.columns or "Data" not in df.columns:
        return vazio
    df = df.copy()
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    ultimo_dado = df["Data"].max()
    hoje = pd.Timestamp(hoje).normalize() if hoje is not None else ultimo_dado
    estados = estados or {}

    cmj, hooper, acwr = _cmj(testes, hoje), _hooper(df, hoje), _acwr(df)
    posicoes = df.dropna(subset=["Jogador", "Posição"]).groupby("Jogador")["Posição"].last().to_dict() if "Posição" in df.columns else {}

    jogadores = []
    for jog in sorted(df["Jogador"].dropna().unique().tolist(), key=lambda s: str(s).lower()):
        sinais = []
        c = cmj.get(jog)
        if c and c["valido"]:
            sev = sev_cmj(c, lim)
            if sev:
                sinais.append({"componente": "cmj", "severidade": sev,
                               "texto": f"CMJ {_pt(c['variacao_pct'], sinal=True)}% vs média própria ({_pt(c['ultimo'])} vs {_pt(c['media_base'])} cm)"})
        h = hooper.get(jog)
        if h and h["valido"]:
            sev = _sev(h["diferenca"], lim["hooper_subida_alto"], lim["hooper_subida_muito_alto"])
            if h["ultimo"] >= lim["hooper_alto"]:
                sev = 2
            if sev:
                dif = f" ({_pt(h['diferenca'], sinal=True)} vs média)" if h["diferenca"] is not None and h["diferenca"] > 0 else ""
                sinais.append({"componente": "hooper", "severidade": sev, "texto": f"Hooper {_pt(h['ultimo'], 0)}{dif}"})
        a = acwr.get(jog)
        if a:
            sev, _ = classificar_acwr(a["atual"], lim)
            if sev:
                seta = {"a_subir": " e a subir", "a_descer": " e a descer"}.get(a["tendencia"] or "", "")
                sinais.append({"componente": "acwr", "severidade": sev, "texto": f"ACWR {_pt(a['atual'], 2)}{seta}"})

        estado_jog = estados.get(jog, "apto")
        total = sum(s["severidade"] for s in sinais)
        if estado_jog != "apto":
            estado = "indisponivel"
        elif total >= 3:
            estado = "reduzir"
        elif total >= 1:
            estado = "vigiar"
        else:
            estado = "pronto"
        jogadores.append({
            "jogador": jog,
            "posicao": posicoes.get(jog) if isinstance(posicoes.get(jog), str) else "—",
            "estado": estado,
            "estado_jogador": estado_jog,
            "pontuacao": total,
            "sinais": sorted(sinais, key=lambda s: -s["severidade"]),
            "cmj": c,
            "hooper": h,
            "acwr": a,
        })

    ordem = {"reduzir": 0, "vigiar": 1, "pronto": 2, "indisponivel": 3}
    jogadores.sort(key=lambda j: (ordem[j["estado"]], -j["pontuacao"], str(j["jogador"]).lower()))
    resumo = {k: sum(1 for j in jogadores if j["estado"] == k) for k in ordem}
    return {
        "tem_dados": bool(jogadores),
        "motivo": None,
        "data_referencia": hoje.strftime("%Y-%m-%d"),
        "data_ultimos_dados": ultimo_dado.strftime("%Y-%m-%d"),
        "dias_sem_dados": max(0, int((hoje - ultimo_dado.normalize()).days)),
        "cobertura": {
            "cmj": sum(1 for j in jogadores if j["cmj"] and j["cmj"]["valido"]),
            "hooper": sum(1 for j in jogadores if j["hooper"] and j["hooper"]["valido"]),
            "total": len(jogadores),
        },
        "limites": {k: lim[k] for k in ("cmj_queda_alto", "cmj_queda_muito_alto", "hooper_subida_alto",
                                        "hooper_subida_muito_alto", "hooper_alto", "acwr_alto", "acwr_muito_alto")},
        "resumo": resumo,
        "jogadores": jogadores,
    }


def _carregar_testes(team_id: str) -> pd.DataFrame:
    from app.core.db import get_conn
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select p.nome, t.data, t.altura_salto_cm
                    from testes_neuromusculares t join players p on p.id = t.player_id
                    where t.team_id = %s and t.altura_salto_cm is not null
                    """,
                    (team_id,),
                )
                return pd.DataFrame(cur.fetchall(), columns=["nome", "data", "altura_salto_cm"])
    except Exception:
        return pd.DataFrame(columns=["nome", "data", "altura_salto_cm"])


def obter_prontidao(team_id: str, limites: dict | None = None) -> dict:
    from app.services.dados_equipa import carregar_df_equipa
    from app.services.estado_service import listar_estados
    try:
        estados = {e["nome"]: e["estado"] for e in listar_estados(team_id)}
    except Exception:
        estados = {}
    from datetime import date
    return calcular_prontidao(carregar_df_equipa(team_id), _carregar_testes(team_id), estados, limites,
                              hoje=pd.Timestamp(date.today()))
