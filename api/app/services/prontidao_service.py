"""Prontidão do jogador — junta três sinais num só estado diário:

  1. CMJ (altura de salto) do último teste face à média dos testes anteriores
     do PRÓPRIO jogador — queda = fadiga neuromuscular;
  2. Hooper (0–16, alto = pior) mais recente face à média do próprio jogador
     nos 28 dias anteriores — subida = pior bem-estar;
  3. Carga interna dos últimos 7 dias face ao NORMAL do jogador (média das
     4–6 semanas anteriores) — substitui o ACWR (ver utils.calculos).

Cada sinal dá severidade 0/1/2 pelos limiares configuráveis
(limites_service). Soma ≥ 3 → «reduzir»; ≥ 1 → «vigiar»; 0 → «pronto».
Comparar o jogador consigo próprio (e não com o plantel) é o padrão em
monitorização: a variabilidade entre atletas é muito maior do que dentro de
cada atleta.
"""
from __future__ import annotations

import pandas as pd

from app.services.alertas_service import classificar_semana
from app.services.limites_service import DEFAULTS
from utils.calculos import semana_vs_normal_global

N_TESTES_BASE = 6          # testes anteriores usados como baseline do CMJ
CMJ_VALIDADE_DIAS = 21     # um teste mais antigo do que isto não conta para hoje
HOOPER_BASE_DIAS = 28
HOOPER_VALIDADE_DIAS = 3   # o Hooper tem de ser dos últimos 3 dias
TENDENCIA_DIAS = 7
SERIE_DIAS = 28
TENDENCIA_LIMIAR = 0.10


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


# Regra por item do bem-estar: um item (sono, fadiga, dor, stress, humor; 1 mau
# … 5 ótimo) ≥ ITEM_QUEDA pontos abaixo do normal DELE (mediana dos últimos
# HOOPER_BASE_DIAS dias, pelo menos ITEM_MIN_REGISTOS respostas). Apanha o dia em
# que só um item cai muito e o Hooper total quase não mexe.
ITENS_WELLNESS = (("Sono (1-5)", "Sono"), ("Fadiga (1-5)", "Fadiga"), ("Dor Musc. (1-5)", "Dor muscular"),
                  ("Stress (1-5)", "Stress"), ("Humor (1-5)", "Humor"))
ITEM_QUEDA = 2
ITEM_MIN_REGISTOS = 4


def itens_abaixo_do_normal(df: pd.DataFrame, hoje: pd.Timestamp) -> dict[str, list[dict]]:
    """{jogador: [{item, valor, normal, diferenca}]} — só itens da resposta mais
    recente (≤ HOOPER_VALIDADE_DIAS) que estão ≥ ITEM_QUEDA abaixo do normal dele."""
    out: dict[str, list[dict]] = {}
    cols = [(c, nome) for c, nome in ITENS_WELLNESS if c in df.columns]
    if not cols or not {"Jogador", "Data"}.issubset(df.columns):
        return out
    base = df.dropna(subset=["Jogador", "Data"]).copy()
    base["Data"] = pd.to_datetime(base["Data"], errors="coerce")
    for jog, g in base.groupby("Jogador"):
        itens = []
        for col, nome in cols:
            s = g.dropna(subset=[col]).sort_values("Data")
            if s.empty:
                continue
            ult = s.iloc[-1]
            if (hoje - ult["Data"]).days > HOOPER_VALIDADE_DIAS:
                continue
            ant = s[(s["Data"] < ult["Data"]) & (s["Data"] >= ult["Data"] - pd.Timedelta(days=HOOPER_BASE_DIAS))][col]
            if len(ant) < ITEM_MIN_REGISTOS:
                continue
            normal = float(ant.median())
            valor = float(ult[col])
            if normal - valor >= ITEM_QUEDA:
                itens.append({"item": nome, "valor": round(valor), "normal": round(normal, 1),
                              "diferenca": round(valor - normal, 1)})
        if itens:
            out[jog] = sorted(itens, key=lambda i: i["diferenca"])
    return out


# Resposta do wellness tal como o jogador a deu no questionário. Na BD a dor
# muscular e o stress estão na escala da app (5 = ótimo) porque a importação
# os inverte (6 − x); aqui voltam à escala do formulário (5 = muita dor /
# muito stress), para o staff ver exatamente o número que o jogador escolheu.
#
# Cada item é comparado com o habitual DO PRÓPRIO jogador no MESMO dia MD
# (as mesmas MD-2 das últimas WELLNESS_BASE_DIAS): o wellness segue o
# microciclo (MD+1 tem mais dor muscular por natureza), por isso comparar uma
# MD+1 com a média de todos os dias dá falsos alarmes. Com poucas respostas
# nesse dia MD usa-se o habitual de todos os dias. O z usa um desvio-padrão
# mínimo (WELLNESS_DP_MIN): numa escala 1–5 um jogador que responde sempre 4
# tem DP ≈ 0 e um único 3 daria z = −5.
ESCALA_INVERTIDA_NO_FORMULARIO = ("dor_musc", "stress")
WELLNESS_COLUNAS = (
    ("Sono (1-5)", "sono"),
    ("Fadiga (1-5)", "energia"),
    ("Dor Musc. (1-5)", "dor_musc"),
    ("Stress (1-5)", "stress"),
    ("Humor (1-5)", "humor"),
    ("Prontidão para treinar (1-5)", "prontidao"),
    ("Dor (1-5)", "dor"),
)
# Na escala do formulário, em que ponta é mau: "alto" = 5 é mau.
WELLNESS_MAU_ALTO = ("dor_musc", "stress", "dor")
WELLNESS_BASE_DIAS = 42
WELLNESS_MIN_MD = 3        # respostas no mesmo dia MD para usar essa base
WELLNESS_MIN_TODOS = 4     # senão, respostas em qualquer dia
WELLNESS_DP_MIN = 0.5
Z_VIGIAR, Z_ATENCAO = 1.0, 1.5


def _valor(v):
    """NaN/None → None; números inteiros sem casas decimais."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (int, float)):
        return int(v) if float(v).is_integer() else round(float(v), 1)
    return v


def _md_do_dia(df: pd.DataFrame, md_planeado: dict[str, str] | None) -> dict[str, str]:
    """{AAAA-MM-DD: dia MD} — o registado nas sessões da equipa nesse dia
    (o mais frequente); sem sessões, o do plano do microciclo."""
    out = dict(md_planeado or {})
    if "Dia MD" in df.columns:
        x = df.dropna(subset=["Data", "Dia MD"])
        x = x[x["Dia MD"].astype(str).str.strip() != ""]
        for d, g in x.groupby(x["Data"].dt.strftime("%Y-%m-%d")):
            out[d] = str(g["Dia MD"].mode().iloc[0])
    return out


def _comparar_item(serie: pd.Series, dia: pd.Timestamp, md: str | None, mds: dict[str, str], chave: str) -> dict:
    """serie: valores do item (escala do formulário) indexados por data."""
    valor = float(serie.loc[dia])
    ant = serie[(serie.index < dia) & (serie.index >= dia - pd.Timedelta(days=WELLNESS_BASE_DIAS))]
    mesmo_md = ant[[mds.get(d.strftime("%Y-%m-%d")) == md for d in ant.index]] if md else ant.iloc[0:0]
    if len(mesmo_md) >= WELLNESS_MIN_MD:
        base, ref = "md", mesmo_md
    elif len(ant) >= WELLNESS_MIN_TODOS:
        base, ref = "todos", ant
    else:
        base, ref = None, None
    mau_alto = chave in WELLNESS_MAU_ALTO
    out = {"valor": _valor(valor), "base": base, "n": int(len(ref)) if ref is not None else 0,
           "habitual": None, "diferenca": None, "z_pior": None, "semana_passada": None,
           "extremo": valor == (5 if mau_alto else 1)}
    if ref is not None:
        media = float(ref.mean())
        dp = max(float(ref.std(ddof=1)) if len(ref) > 1 else 0.0, WELLNESS_DP_MIN)
        z = (valor - media) / dp
        out.update({"habitual": round(media, 1), "diferenca": round(valor - media, 1),
                    "z_pior": round(z if mau_alto else -z, 2)})
    if md:
        sp = mesmo_md[(mesmo_md.index >= dia - pd.Timedelta(days=10)) & (mesmo_md.index <= dia - pd.Timedelta(days=4))]
        if not sp.empty:
            out["semana_passada"] = _valor(float(sp.iloc[-1]))
    return out


def _estado_wellness(itens: dict[str, dict], pode_treinar: bool | None) -> str:
    zs = [i["z_pior"] for i in itens.values() if i.get("z_pior") is not None]
    if pode_treinar is False or any(i.get("extremo") for i in itens.values()) or any(z >= Z_ATENCAO for z in zs):
        return "atencao"
    if any(z >= Z_VIGIAR for z in zs):
        return "vigiar"
    return "ok"


def wellness_ultimo(df: pd.DataFrame, hoje: pd.Timestamp, md_planeado: dict[str, str] | None = None) -> dict[str, dict]:
    """{jogador: {data, dias_desde, dia_md, estado, itens{chave: {valor,
    habitual, diferenca, z_pior, base, n, semana_passada, extremo}},
    pode_treinar, local_dor}} — a resposta mais recente de cada jogador."""
    out: dict[str, dict] = {}
    cols = [(c, k) for c, k in WELLNESS_COLUNAS if c in df.columns]
    if not cols or not {"Jogador", "Data"}.issubset(df.columns):
        return out
    base = df.dropna(subset=["Jogador", "Data"]).copy()
    base["Data"] = pd.to_datetime(base["Data"], errors="coerce").dt.normalize()
    mds = _md_do_dia(base, md_planeado)
    base = base.dropna(subset=[c for c, _ in cols], how="all").sort_values("Data")
    for jog, g in base.groupby("Jogador"):
        dia = g["Data"].max()
        md = mds.get(dia.strftime("%Y-%m-%d"))
        itens: dict = {}
        for col, chave in cols:
            s = pd.to_numeric(g[col], errors="coerce")
            s = pd.Series(s.values, index=g["Data"]).dropna()
            s = s[~s.index.duplicated(keep="last")]
            if chave in ESCALA_INVERTIDA_NO_FORMULARIO:
                s = 6 - s
            if dia in s.index:
                itens[chave] = _comparar_item(s, dia, md, mds, chave)
        linhas = g[g["Data"] == dia]
        extra: dict = {}
        for col, chave in (("Pode treinar hoje", "pode_treinar"), ("Local da dor", "local_dor")):
            if col in linhas.columns:
                v = linhas[col].dropna()
                if not v.empty:
                    extra[chave] = bool(v.iloc[-1]) if chave == "pode_treinar" else str(v.iloc[-1])
        dias = max(0, int((hoje.normalize() - dia).days))
        out[jog] = {
            "data": dia.strftime("%Y-%m-%d"),
            "dias_desde": dias,
            "dia_md": md,
            "estado": _estado_wellness(itens, extra.get("pode_treinar")) if dias == 0 else "antiga",
            "itens": itens,
            "pode_treinar": extra.get("pode_treinar"),
            "local_dor": extra.get("local_dor"),
        }
    return out


def texto_itens(itens: list[dict]) -> str:
    return " · ".join(f"{i['item']} {i['valor']}/5 (normal {_pt(i['normal'], 0)})" for i in itens)


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
    md_planeado: dict[str, str] | None = None,
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

    cmj, hooper = _cmj(testes, hoje), _hooper(df, hoje)
    itens = itens_abaixo_do_normal(df, hoje)
    wellness = wellness_ultimo(df, hoje, md_planeado)
    semanas = semana_vs_normal_global(df, ate=hoje)
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
        it = itens.get(jog)
        if it:
            sev_it = 2 if len(it) >= 2 or it[0]["diferenca"] <= -3 else 1
            sinais.append({"componente": "item", "severidade": sev_it, "texto": texto_itens(it)})
        a = semanas.get(jog)
        if a:
            a = {k: v for k, v in a.items() if k not in ("data", "posicao")}
            sev, _ = classificar_semana(a, lim)
            if sev:
                sinais.append({"componente": "semana", "severidade": sev,
                               "texto": f"Semana {_pt(a['variacao_pct'], 0, sinal=True)} % vs o normal ({a['semana']} vs {a['normal']} UA)"})

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
            "semana": a,
            "itens_wellness": it or [],
            "wellness": wellness.get(jog),
        })

    ordem = {"reduzir": 0, "vigiar": 1, "pronto": 2, "indisponivel": 3}
    jogadores.sort(key=lambda j: (ordem[j["estado"]], -j["pontuacao"], str(j["jogador"]).lower()))
    resumo = {k: sum(1 for j in jogadores if j["estado"] == k) for k in ordem}
    return {
        "tem_dados": bool(jogadores),
        "motivo": None,
        "data_referencia": hoje.strftime("%Y-%m-%d"),
        "dia_md_hoje": _md_do_dia(df, md_planeado).get(hoje.strftime("%Y-%m-%d")),
        "data_ultimos_dados": ultimo_dado.strftime("%Y-%m-%d"),
        "dias_sem_dados": max(0, int((hoje - ultimo_dado.normalize()).days)),
        "cobertura": {
            "cmj": sum(1 for j in jogadores if j["cmj"] and j["cmj"]["valido"]),
            "hooper": sum(1 for j in jogadores if j["hooper"] and j["hooper"]["valido"]),
            "wellness_hoje": sum(1 for j in jogadores if j["wellness"] and j["wellness"]["dias_desde"] == 0),
            "wellness_atencao": sum(1 for j in jogadores if j["wellness"] and j["wellness"]["estado"] == "atencao"),
            "wellness_vigiar": sum(1 for j in jogadores if j["wellness"] and j["wellness"]["estado"] == "vigiar"),
            "total": len(jogadores),
        },
        "limites": {k: lim[k] for k in ("cmj_queda_alto", "cmj_queda_muito_alto", "hooper_subida_alto",
                                        "hooper_subida_muito_alto", "hooper_alto", "carga_change_alto", "carga_change_muito_alto")},
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


def _md_planeado(team_id: str, hoje: pd.Timestamp) -> dict[str, str]:
    """{AAAA-MM-DD: dia MD} do plano dos microciclos — para o dia de hoje,
    quando o wellness chega de manhã antes de o GPS ser importado."""
    import json
    from app.core.db import get_conn
    ini = (hoje - pd.Timedelta(days=WELLNESS_BASE_DIAS + 7)).date()
    out: dict[str, str] = {}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("select dias from microciclos where team_id = %s and data_fim >= %s and data_inicio <= %s",
                            (team_id, ini, hoje.date()))
                for (dias,) in cur.fetchall():
                    dias = dias if isinstance(dias, dict) else json.loads(dias or "{}")
                    for d, v in dias.items():
                        if isinstance(v, dict) and v.get("dia_md"):
                            out[d] = "MD" if v.get("tipo") == "Jogo" else str(v["dia_md"])
    except Exception:
        return {}
    return out


def alinhar_com_avisos(resultado: dict, avisos: list[dict]) -> dict:
    """A Prontidão é a vista em TABELA dos mesmos sinais de Hoje · Para agir
    (motor único: alertas_service.construir_avisos_dashboard). As colunas CMJ,
    Hooper e semana ficam como contexto; o estado e o «porquê» vêm dos avisos —
    assim o mesmo jogador nunca está «Vigiar» numa página e «Pronto» na outra.
      agir   = atenção alta em Para agir (status high-attention)
      vigiar = atenção
      pronto = sem sinais · indisponivel = lesionado/ausente/em recuperação."""
    por_nome = {a["player_name"]: a for a in avisos}
    for j in resultado.get("jogadores", []):
        if j["estado"] == "indisponivel":
            continue
        a = por_nome.get(str(j["jogador"]))
        sinais = (a or {}).get("sinais") or []
        j["sinais"] = [{"componente": s["chave"], "severidade": int(s.get("severidade") or 1),
                        "texto": f"{s['texto']} · {s['resumo']}" if s.get("resumo") else s["texto"]} for s in sinais]
        j["pontuacao"] = sum(s["severidade"] for s in j["sinais"])
        status = (a or {}).get("status", "normal")
        j["estado"] = "reduzir" if status == "high-attention" else "vigiar" if status == "attention" else "pronto"
    ordem = {"reduzir": 0, "vigiar": 1, "pronto": 2, "indisponivel": 3}
    resultado["jogadores"].sort(key=lambda j: (ordem[j["estado"]], -j["pontuacao"], str(j["jogador"]).lower()))
    resultado["resumo"] = {k: sum(1 for j in resultado["jogadores"] if j["estado"] == k) for k in ordem}
    return resultado


def obter_prontidao(team_id: str, limites: dict | None = None) -> dict:
    from app.services.dados_equipa import carregar_df_equipa
    from app.services.estado_service import listar_estados
    try:
        estados = {e["nome"]: e["estado"] for e in listar_estados(team_id)}
    except Exception:
        estados = {}
    from datetime import date
    hoje = pd.Timestamp(date.today())
    resultado = calcular_prontidao(carregar_df_equipa(team_id), _carregar_testes(team_id), estados, limites,
                                   hoje=hoje, md_planeado=_md_planeado(team_id, hoje))
    if resultado.get("jogadores"):
        from app.routers.dashboard import _build_alerts
        resultado = alinhar_com_avisos(resultado, _build_alerts(team_id, limites))
    return resultado
