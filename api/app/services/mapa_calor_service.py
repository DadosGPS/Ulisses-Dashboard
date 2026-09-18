"""Mapa de calor da época — jogadores × microciclos.

Para cada jogador e microciclo calcula várias métricas, para o frontend poder
alternar a "lente" (a dúvida sobre qual o melhor indicador resolve-se dando
várias): carga interna semanal, %HSR e %Sprint vs o jogo mais exigente do
jogador (exposição), e a variação semana-a-semana da carga interna (picos).

Todas as métricas vêm calculadas de uma vez — o seletor no frontend troca sem
novo pedido à API.
"""
import pandas as pd

from app.services.dados_equipa import carregar_df_equipa

# tipo: "sequential" (mais = mais intenso) | "diverging" (à volta de 0/100)
METRICAS_MAPA = [
    {"chave": "carga_interna", "label": "Carga Interna (semanal)", "unidade": "UA", "tipo": "sequential", "casas": 0},
    {"chave": "hsr_pct_jogo", "label": "% HSR vs jogo", "unidade": "%", "tipo": "ratio", "casas": 0},
    {"chave": "sprint_pct_jogo", "label": "% Sprint vs jogo", "unidade": "%", "tipo": "ratio", "casas": 0},
    {"chave": "delta_carga_pct", "label": "Variação semanal (carga)", "unidade": "%", "tipo": "diverging", "casas": 0},
]


def obter_mapa_calor(team_id: str) -> dict:
    vazio = {"tem_dados": False, "microciclos": [], "jogadores": [], "metricas": METRICAS_MAPA, "dados": {}}
    df = carregar_df_equipa(team_id)
    if df.empty or "Microciclo (Nr)" not in df.columns or not df["Microciclo (Nr)"].notna().any():
        return vazio
    if "Jogador" not in df.columns:
        return vazio

    df = df.copy()
    df = df.dropna(subset=["Microciclo (Nr)", "Jogador"])
    df["Microciclo (Nr)"] = df["Microciclo (Nr)"].astype(int)

    microciclos = sorted(df["Microciclo (Nr)"].unique().tolist())
    jogadores = sorted(df["Jogador"].dropna().unique().tolist(), key=lambda s: str(s).lower())

    tem_tipo = "Tipo" in df.columns
    jogos = df[df["Tipo"] == "Jogo"] if tem_tipo else df.iloc[0:0]
    # % vs jogo mede a EXPOSIÇÃO do treino face à exigência do jogo — por isso a
    # média semanal de HSR/Sprint é só dos treinos (não conta o próprio jogo).
    treinos = df[df["Tipo"] != "Jogo"] if tem_tipo else df

    def pico_jogo(col: str) -> dict:
        """Pico de `col` em jogo, por jogador (referência de exigência)."""
        if col not in jogos.columns or jogos.empty:
            return {}
        s = jogos.dropna(subset=[col, "Jogador"]).groupby("Jogador")[col].max()
        return {j: float(v) for j, v in s.items() if v and v > 0}

    pico_hsr = pico_jogo("HSR (m)")
    pico_sprint = pico_jogo("Sprint (m)")

    # Agregações por (jogador, microciclo)
    def soma(col):
        return df.dropna(subset=[col]).groupby(["Jogador", "Microciclo (Nr)"])[col].sum() if col in df.columns else pd.Series(dtype=float)

    def media_treino(col):
        return treinos.dropna(subset=[col]).groupby(["Jogador", "Microciclo (Nr)"])[col].mean() if col in treinos.columns else pd.Series(dtype=float)

    carga_sum = soma("Carga Interna")  # carga total da semana (inclui jogo)
    hsr_media = media_treino("HSR (m)")
    sprint_media = media_treino("Sprint (m)")

    def linhas_por_valor(fn):
        """Constrói [{jogador, valores:{mc: valor|None}}] aplicando fn(jog, mc)."""
        out = []
        for jog in jogadores:
            valores = {}
            for mc in microciclos:
                valores[str(mc)] = fn(jog, mc)
            out.append({"jogador": jog, "valores": valores})
        return out

    def v_carga(jog, mc):
        try:
            return round(float(carga_sum.loc[(jog, mc)]), 0)
        except KeyError:
            return None

    def v_pct(media_serie, picos, jog, mc):
        pico = picos.get(jog)
        if not pico:
            return None
        try:
            m = float(media_serie.loc[(jog, mc)])
        except KeyError:
            return None
        return round(m / pico * 100, 0)

    def v_delta(jog, mc):
        idx = microciclos.index(mc)
        if idx == 0:
            return None
        atual = v_carga(jog, mc)
        anterior = v_carga(jog, microciclos[idx - 1])
        if atual is None or not anterior:
            return None
        return round((atual - anterior) / anterior * 100, 0)

    dados = {
        "carga_interna": linhas_por_valor(v_carga),
        "hsr_pct_jogo": linhas_por_valor(lambda j, m: v_pct(hsr_media, pico_hsr, j, m)),
        "sprint_pct_jogo": linhas_por_valor(lambda j, m: v_pct(sprint_media, pico_sprint, j, m)),
        "delta_carga_pct": linhas_por_valor(v_delta),
    }

    return {
        "tem_dados": True,
        "microciclos": microciclos,
        "jogadores": jogadores,
        "metricas": METRICAS_MAPA,
        "dados": dados,
    }
