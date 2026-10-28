"""LoadMonitorSystem — Cálculos científicos"""
import pandas as pd
import numpy as np

# Decorador de cache herdado da antiga app Streamlit: aqui não faz nada (a API
# gere a sua própria cache). Mantido para não mexer nas funções decoradas.
def cache_data(*dargs, **dkwargs):
    if len(dargs) == 1 and callable(dargs[0]) and not dkwargs:
        return dargs[0]
    def _decorator(func):
        return func
    return _decorator


# ── ACWR (EWMA sobre carga DIÁRIA) ────────────────────────────────────────────
# Williams et al. (2017): λ aguda = 2/(7+1) = 0.25 e λ crónica = 2/(28+1),
# aplicadas a uma série DIÁRIA. Os dias sem sessão contam como carga 0 e várias
# sessões no mesmo dia somam-se. Aplicar o EWMA sessão a sessão (como antes)
# ignorava os dias de descanso e inflacionava a carga aguda.
LAMBDA_AGUDA = 0.25
LAMBDA_CRONICA = 2 / 29
# Período de arranque: a carga crónica (EWMA de 28 dias) começa no valor do
# primeiro dia e só ao fim de ~4 semanas reflete o histórico real. Antes disso
# o rácio não tem significado (um jogador novo com 2 treinos "dispara"), por
# isso o ACWR fica vazio até o jogador ter MIN_DIAS_ACWR dias de série.
MIN_DIAS_ACWR = 28


def serie_acwr_diaria(df_base: pd.DataFrame, ate: pd.Timestamp | None = None) -> pd.DataFrame:
    """Série diária de ACWR por jogador, da primeira sessão de cada jogador até
    `ate` (por omissão, o último dia com dados da equipa — assim um jogador
    sem sessões recentes vê a carga aguda descer, como na realidade).

    Colunas: Data, Jogador, Carga Interna (soma do dia), Carga Aguda,
    Carga Crónica, ACWR.
    """
    cols = ["Data", "Jogador", "Carga Interna", "Carga Aguda", "Carga Crónica", "ACWR"]
    if df_base is None or df_base.empty or not {"Jogador", "Data", "Carga Interna"}.issubset(df_base.columns):
        return pd.DataFrame(columns=cols)
    sub = df_base.dropna(subset=["Carga Interna", "Data", "Jogador"]).copy()
    if sub.empty:
        return pd.DataFrame(columns=cols)
    sub["Data"] = pd.to_datetime(sub["Data"]).dt.normalize()
    fim = pd.Timestamp(ate).normalize() if ate is not None else sub["Data"].max()
    diario = sub.groupby(["Jogador", "Data"])["Carga Interna"].sum()

    partes = []
    for jog, serie in diario.groupby(level="Jogador", sort=False):
        serie = serie.droplevel("Jogador")
        inicio = serie.index.min()
        if inicio > fim:
            continue
        dias = pd.date_range(inicio, fim, freq="D")
        carga = serie.reindex(dias, fill_value=0.0).astype(float)
        aguda = carga.ewm(alpha=LAMBDA_AGUDA, adjust=False).mean()
        cronica = carga.ewm(alpha=LAMBDA_CRONICA, adjust=False).mean()
        acwr = np.where(cronica.values > 0, aguda.values / np.where(cronica.values > 0, cronica.values, 1), np.nan)
        acwr[: MIN_DIAS_ACWR - 1] = np.nan  # período de arranque (ver MIN_DIAS_ACWR)
        partes.append(pd.DataFrame({
            "Data": dias, "Jogador": jog, "Carga Interna": carga.values,
            "Carga Aguda": aguda.values, "Carga Crónica": cronica.values,
            "ACWR": acwr,
        }))
    if not partes:
        return pd.DataFrame(columns=cols)
    return pd.concat(partes, ignore_index=True)[cols]


def calcular_acwr(df: pd.DataFrame, jogador: str) -> pd.DataFrame:
    """ACWR diário (EWMA) de um jogador — ver serie_acwr_diaria. Mantida para
    as chamadas existentes; a série vai até ao último dia com dados da equipa."""
    if df.empty or "Jogador" not in df.columns or "Data" not in df.columns:
        return pd.DataFrame()
    ate = pd.to_datetime(df["Data"]).max()
    serie = serie_acwr_diaria(df[df["Jogador"] == jogador], ate=ate)
    return serie if not serie.empty else pd.DataFrame()


@cache_data(ttl=600, show_spinner=False)
def calcular_acwr_global(df_base: pd.DataFrame) -> dict:
    """ACWR mais recente de todos os jogadores (EWMA sobre carga diária — ver
    serie_acwr_diaria). Estrutura por jogador (inalterada):
        {"acwr", "posicao", "data", "ci_agudo", "ci_cronico"}
    """
    resultado: dict = {}
    serie = serie_acwr_diaria(df_base)
    validos = serie.dropna(subset=["ACWR"])
    if validos.empty:
        return resultado
    ultimos = validos.groupby("Jogador", sort=False).tail(1).set_index("Jogador")

    pos_map: dict = {}
    if "Posição" in df_base.columns:
        df_pos = df_base.dropna(subset=["Jogador", "Posição"])
        if not df_pos.empty:
            pos_map = df_pos.groupby("Jogador", sort=False)["Posição"].last().to_dict()

    for jog, last in ultimos.iterrows():
        resultado[jog] = {
            "acwr":       last["ACWR"],
            "posicao":    pos_map.get(jog, "—"),
            "data":       last["Data"],
            "ci_agudo":   last["Carga Aguda"],
            "ci_cronico": last["Carga Crónica"],
        }
    return resultado


# ── Recorde de velocidade máxima ─────────────────────────────────────────────
# Um pico isolado do GPS (perda de sinal, salto de posição) pode dar 33 km/h a
# um sub-13 que corre a 28. Usado como recorde, deixaria o jogador em «pouco
# estímulo de velocidade» para o resto da época e inflacionaria as metas de
# regresso ao jogo. Regra: o melhor valor só conta se não estiver mais de
# PICO_VMAX_PCT % acima do segundo melhor; se estiver, é tratado como pico e
# passa-se ao seguinte. Um recorde verdadeiro fica confirmado assim que outra
# sessão chega perto dele.
PICO_VMAX_PCT = 5.0


def recorde_vmax(valores) -> float | None:
    """Recorde de velocidade máxima sem picos isolados (ver PICO_VMAX_PCT)."""
    v = sorted((float(x) for x in pd.Series(valores).dropna() if float(x) > 0), reverse=True)
    if not v:
        return None
    for i in range(len(v) - 1):
        if v[i] <= v[i + 1] * (1 + PICO_VMAX_PCT / 100):
            return v[i]
    return v[-1]


def zscore_serie(serie: pd.Series) -> pd.Series:
    if serie.dropna().std() == 0:
        return pd.Series(0, index=serie.index)
    return (serie - serie.mean()) / serie.std()


def cor_acwr(v) -> str:
    """Retorna emoji + texto (e.g. '🔴 RISCO') para classificação ACWR.

    Páginas dependem do texto: usam `"RISCO" in estado` para classificar alertas.
    Não alterar o formato sem actualizar dashboard.py, equipa.py, sistema.py.
    """
    if pd.isna(v):      return "❓"
    if v >= 1.5:        return "🔴 RISCO"
    if v >= 1.3:        return "🟡 ATENÇÃO"
    if v >= 0.8:        return "🟢 OK"
    return "🔵 SUB-CARGA"


# Ordem canónica dos dias de um microciclo — mesma usada em
# app/services/resumo_5w1h.py (PERFIL_DIA_MD), duplicada aqui por
# utils/calculos.py ser um módulo puro (sem depender de app/).
DIAS_MD_ORDEM = ["MD-5", "MD-4", "MD-3", "MD-2", "MD-1", "MD", "MD+1", "MD+2"]


@cache_data(ttl=600, show_spinner=False)
def calcular_monotonia_strain(df_base: pd.DataFrame) -> pd.DataFrame:
    """Foster (1998) — Monotonia e Strain por jogador e microciclo.

    Trata cada microciclo como uma semana de 7 dias: usa os dias de "Dia MD"
    que a equipa costuma registar (ex: MD-5..MD), preenche com carga 0 os
    dias sem sessão registada (dia de folga) até perfazer 7 dias — sem isto
    a monotonia fica inflacionada, porque o dia de folga faz parte da
    variabilidade real da carga semanal, não é "ausência de dado".

    Monotonia = média das 7 cargas diárias ÷ desvio-padrão AMOSTRAL (ddof=1)
    dessas 7 cargas. Strain = carga semanal total × monotonia.
    """
    if df_base.empty or "Carga Interna" not in df_base.columns:
        return pd.DataFrame()
    obrigatorias = {"Microciclo (Nr)", "Jogador", "Dia MD"}
    if not obrigatorias.issubset(df_base.columns):
        return pd.DataFrame()

    sub = df_base.dropna(subset=["Carga Interna", "Jogador", "Microciclo (Nr)", "Dia MD"]).copy()
    if sub.empty:
        return pd.DataFrame()

    resultados = []
    for mc, g_mc in sub.groupby("Microciclo (Nr)", sort=False):
        # Dias que esta equipa registou neste microciclo, na ordem certa —
        # os que faltam até perfazer 7 são o(s) dia(s) de folga (carga 0).
        dias_semana = [d for d in DIAS_MD_ORDEM if d in set(g_mc["Dia MD"])]
        n_dias = max(7, len(dias_semana))
        n_folga = n_dias - len(dias_semana)

        for jogador, g_jog in g_mc.groupby("Jogador", sort=False):
            cargas_dia = g_jog.groupby("Dia MD")["Carga Interna"].sum().reindex(dias_semana).fillna(0.0)
            cargas_semana = np.append(cargas_dia.to_numpy(dtype=float), np.zeros(n_folga))

            soma = float(cargas_semana.sum())
            media = soma / n_dias
            dp = float(np.std(cargas_semana, ddof=1)) if n_dias > 1 else 0.0
            monotonia = media / dp if dp > 0 else 0.0
            strain = soma * monotonia

            resultados.append({
                "Jogador": jogador,
                "Microciclo (Nr)": mc,
                "Carga Semanal Total": round(soma, 0),
                "Monotonia": round(monotonia, 2),
                "Strain": round(strain, 0),
            })

    if not resultados:
        return pd.DataFrame()
    return pd.DataFrame(resultados).sort_values(["Jogador", "Microciclo (Nr)"]).reset_index(drop=True)
