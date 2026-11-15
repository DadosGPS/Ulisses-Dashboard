"""Mapa de calor da época — jogadores × microciclos.

Três famílias de métricas, cada uma com uma pergunta clara:

  · Volume da semana (quanto fez?): carga interna, distância, HSR, sprint e
    acelerações + desacelerações — SOMA da semana (treinos + jogo);
  · Exposição vs jogo (o treino preparou para o jogo?): HSR e sprint dos
    TREINOS da semana ÷ referência de jogo do jogador — exatamente o mesmo
    cálculo e as mesmas zonas da página Semana (antes era a média por sessão,
    um número diferente do resto da app);
  · Risco de pico (mudou depressa demais?): ACWR da carga interna (semana ÷
    média das 4 anteriores) e a variação face à semana anterior.

Cada métrica traz o seu `tipo` de escala: sequential (mais = mais), zonas
(com limites ok/abaixo/acima) ou diverging (à volta de 0). O frontend pode
ainda colorir cada linha face ao próprio jogador (para ver a semana atípica
de cada um em vez de quem faz sempre mais).
"""
import pandas as pd

from app.services.dados_equipa import carregar_df_equipa
from app.services.referencia_jogo import mascara_jogo, referencias_jogo, valores_referencia

# grupo, chave, label, unidade, tipo, casas, descrição (uma linha: o que responde)
METRICAS_MAPA = [
    {"grupo": "volume", "chave": "carga_interna", "label": "Carga interna", "unidade": "UA", "tipo": "sequential", "casas": 0,
     "descricao": "Soma da carga interna da semana (PSE × minutos), treinos e jogo."},
    {"grupo": "volume", "chave": "distancia", "label": "Distância", "unidade": "m", "tipo": "sequential", "casas": 0,
     "descricao": "Distância total da semana, treinos e jogo."},
    {"grupo": "volume", "chave": "hsr", "label": "HSR", "unidade": "m", "tipo": "sequential", "casas": 0,
     "descricao": "Metros em alta velocidade na semana, treinos e jogo."},
    {"grupo": "volume", "chave": "sprint", "label": "Sprint", "unidade": "m", "tipo": "sequential", "casas": 0,
     "descricao": "Metros em sprint na semana, treinos e jogo."},
    {"grupo": "volume", "chave": "acc_dcc", "label": "Acc + Dcc", "unidade": "n", "tipo": "sequential", "casas": 0,
     "descricao": "Acelerações + desacelerações na semana, treinos e jogo."},
    {"grupo": "exposicao", "chave": "exp_hsr", "label": "HSR vs jogo", "unidade": "×", "tipo": "zonas", "casas": 2,
     "descricao": "HSR dos treinos da semana ÷ HSR de um jogo completo do jogador (o mesmo da página Semana)."},
    {"grupo": "exposicao", "chave": "exp_sprint", "label": "Sprint vs jogo", "unidade": "×", "tipo": "zonas", "casas": 2,
     "descricao": "Sprint dos treinos da semana ÷ sprint de um jogo completo do jogador."},
    {"grupo": "risco", "chave": "acwr", "label": "ACWR", "unidade": "", "tipo": "zonas", "casas": 2,
     "descricao": "Carga interna da semana ÷ média das 4 semanas anteriores (precisa de 4 semanas de histórico)."},
    {"grupo": "risco", "chave": "delta_carga_pct", "label": "Variação semanal", "unidade": "%", "tipo": "diverging", "casas": 0,
     "descricao": "Carga interna face à semana anterior do próprio jogador."},
]
GRUPOS = [
    {"chave": "volume", "label": "Volume da semana", "pergunta": "Quanto fez cada jogador?"},
    {"chave": "exposicao", "label": "Exposição vs jogo", "pergunta": "Os treinos prepararam para as exigências do jogo?"},
    {"chave": "risco", "label": "Picos de carga", "pergunta": "A carga subiu depressa demais?"},
]
SOMAS = {"carga_interna": ["Carga Interna"], "distancia": ["Distância Total (m)"], "hsr": ["HSR (m)"],
         "sprint": ["Sprint (m)"], "acc_dcc": ["Acc (n)", "Dcc (n)"]}
SEMANAS_CRONICA = 4


def _zonas(lim: dict) -> dict:
    return {
        "exp_hsr": {"ok": [lim.get("hsr_semana_baixo", 0.6), lim.get("hsr_semana_alto", 1.2)]},
        "exp_sprint": {"ok": [lim.get("sprint_semana_baixo", 0.5), lim.get("sprint_semana_alto", 1.2)]},
        "acwr": {"ok": [0.8, lim.get("acwr_alto", 1.3)], "agir": lim.get("acwr_muito_alto", 1.5)},
    }


def calcular(df: pd.DataFrame, lim: dict | None = None) -> dict:
    """Puro (sem BD): DataFrame canónico da equipa → mapa de calor."""
    lim = lim or {}
    vazio = {"tem_dados": False, "microciclos": [], "jogadores": [], "metricas": METRICAS_MAPA, "grupos": GRUPOS, "dados": {}}
    if df.empty or "Jogador" not in df.columns or "Microciclo (Nr)" not in df.columns or not df["Microciclo (Nr)"].notna().any():
        return vazio
    df = df.dropna(subset=["Microciclo (Nr)", "Jogador"]).copy()
    df["Microciclo (Nr)"] = df["Microciclo (Nr)"].astype(int)
    microciclos = sorted(df["Microciclo (Nr)"].unique().tolist())
    posicoes = (df.dropna(subset=["Posição"]).groupby("Jogador")["Posição"].last().to_dict() if "Posição" in df.columns else {})
    jogadores = sorted(df["Jogador"].unique().tolist(), key=lambda j: (str(posicoes.get(j, "~")), str(j).lower()))

    e_jogo = mascara_jogo(df)
    jogos, treinos = df[e_jogo], df[~e_jogo]

    def soma(base: pd.DataFrame, cols: list[str]) -> pd.Series:
        cols = [c for c in cols if c in base.columns]
        if not cols:
            return pd.Series(dtype=float)
        b = base.copy()
        b["_v"] = sum(pd.to_numeric(b[c], errors="coerce") for c in cols)
        b = b.dropna(subset=["_v"])
        return b.groupby(["Jogador", "Microciclo (Nr)"])["_v"].sum()

    def refs(col: str) -> dict:
        if col not in jogos.columns or jogos.empty:
            return {}
        r = referencias_jogo(jogos, col, jogadores={j: posicoes.get(j, "") for j in jogadores})
        return {j: v for j, v in valores_referencia(r).items() if v and v > 0}

    series = {k: soma(df, cols) for k, cols in SOMAS.items()}
    treino_hsr, treino_sprint = soma(treinos, ["HSR (m)"]), soma(treinos, ["Sprint (m)"])
    ref_hsr, ref_sprint = refs("HSR (m)"), refs("Sprint (m)")

    def ler(s: pd.Series, j, mc):
        try:
            v = s.loc[(j, mc)]
            return None if pd.isna(v) else float(v)
        except KeyError:
            return None

    dados: dict[str, list] = {m["chave"]: [] for m in METRICAS_MAPA}
    for j in jogadores:
        linhas = {k: {} for k in dados}
        ci = [ler(series["carga_interna"], j, mc) for mc in microciclos]
        for i, mc in enumerate(microciclos):
            k = str(mc)
            for chave in SOMAS:
                v = ler(series[chave], j, mc)
                linhas[chave][k] = round(v) if v is not None else None
            for chave, s, ref in (("exp_hsr", treino_hsr, ref_hsr), ("exp_sprint", treino_sprint, ref_sprint)):
                v, r = ler(s, j, mc), ref.get(j)
                linhas[chave][k] = round(v / r, 2) if v is not None and r else None
            atual = ci[i]
            anteriores = [x for x in ci[max(0, i - SEMANAS_CRONICA):i] if x is not None]
            linhas["acwr"][k] = (round(atual / (sum(anteriores) / len(anteriores)), 2)
                                 if atual is not None and len(anteriores) == SEMANAS_CRONICA and sum(anteriores) > 0 else None)
            ant = ci[i - 1] if i else None
            linhas["delta_carga_pct"][k] = round((atual - ant) / ant * 100) if atual is not None and ant else None
        for chave in dados:
            dados[chave].append({"jogador": j, "posicao": posicoes.get(j) or "—", "valores": linhas[chave]})

    # Linha da equipa: média dos jogadores com valor em cada semana.
    equipa = {}
    for chave, linhas in dados.items():
        casas = next(m["casas"] for m in METRICAS_MAPA if m["chave"] == chave)
        equipa[chave] = {}
        for mc in microciclos:
            vs = [l["valores"][str(mc)] for l in linhas if l["valores"][str(mc)] is not None]
            equipa[chave][str(mc)] = round(sum(vs) / len(vs), casas) if vs else None

    datas = {}
    if "Data" in df.columns:
        d = pd.to_datetime(df["Data"], errors="coerce")
        for mc, g in d.groupby(df["Microciclo (Nr)"]):
            if g.notna().any():
                datas[str(mc)] = g.min().date().isoformat()

    return {"tem_dados": True, "microciclos": microciclos, "datas": datas, "jogadores": jogadores,
            "metricas": METRICAS_MAPA, "grupos": GRUPOS, "zonas": _zonas(lim), "dados": dados, "equipa": equipa}


def obter_mapa_calor(team_id: str, user_id: str | None = None) -> dict:
    lim = {}
    if user_id:
        try:
            from app.services.limites_service import obter_limites_equipa
            lim = obter_limites_equipa(team_id, user_id)
        except Exception:
            lim = {}
    return calcular(carregar_df_equipa(team_id), lim)
