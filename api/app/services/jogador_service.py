"""Jogadores — Fase 7 do plano de migração (perfil individual).

Reutiliza utils/calculos.py::calcular_acwr (histórico ACWR por jogador,
mantida no código Python original exatamente para este tipo de uso).
"""
from decimal import Decimal

import pandas as pd

from utils.calculos import calcular_acwr

from app.services.carga_externa_service import METRICAS as METRICAS_EXTERNAS
from app.services.dados_equipa import carregar_df_equipa

# (coluna canónica, chave JSON) — mapa explícito em vez de derivar a chave por
# substituição de caracteres, que partia em colunas como "Vel. Máx (km/h)"
# (o "/" sobrevivia ao replace e ia parar a uma chave JSON inválida).
COLUNAS_SESSAO = [
    ("Tipo", "tipo"),
    ("Dia MD", "dia_md"),
    ("Microciclo (Nr)", "microciclo_nr"),
    ("Carga Interna", "carga_interna"),
    ("Distância Total (m)", "distancia_total_m"),
    ("HSR (m)", "hsr_m"),
    ("Sprint (m)", "sprint_m"),
    ("Vel. Máx (km/h)", "vel_max_kmh"),
    ("Hooper Index", "hooper_index"),
]


def _numero(v):
    """Postgres `numeric` chega via psycopg2 como Decimal, não float — sem
    esta conversão, o valor passava para o JSON com o tipo errado."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (int, float)):
        return round(float(v), 1)
    return v


def listar_jogadores(team_id: str) -> list[dict]:
    df = carregar_df_equipa(team_id)
    if df.empty or "Jogador" not in df.columns:
        return []
    posicoes = df.groupby("Jogador")["Posição"].last() if "Posição" in df.columns else {}
    nomes = sorted(df["Jogador"].dropna().unique().tolist())
    return [{"nome": n, "posicao": posicoes.get(n, "—") if not isinstance(posicoes, dict) else "—"} for n in nomes]


def obter_jogador(team_id: str, nome: str) -> dict | None:
    df = carregar_df_equipa(team_id)
    if df.empty or "Jogador" not in df.columns:
        return None

    jogadores_disponiveis = sorted(df["Jogador"].dropna().unique().tolist())
    if nome not in jogadores_disponiveis:
        return None

    sub = df[df["Jogador"] == nome].sort_values("Data")
    posicao = sub["Posição"].dropna().iloc[-1] if "Posição" in sub.columns and sub["Posição"].notna().any() else "—"

    acwr_hist = calcular_acwr(df, nome)
    evolucao_acwr = [
        {"data": row["Data"].date().isoformat(), "acwr": round(float(row["ACWR"]), 2)}
        for _, row in acwr_hist.dropna(subset=["ACWR"]).iterrows()
    ]

    evolucao_carga = []
    if "Carga Interna" in sub.columns:
        for _, row in sub.dropna(subset=["Carga Interna"]).iterrows():
            evolucao_carga.append({
                "data": row["Data"].date().isoformat(),
                "carga_interna": round(float(row["Carga Interna"]), 0),
            })

    # Tendência de velocidade máxima — recorde da época vs média das últimas
    # 3 sessões com valor registado. Uma queda sustentada (ver LIMITE_QUEDA_
    # VELOCIDADE em analise_service.py) é um sinal clássico de fadiga
    # acumulada ou lesão a instalar-se, mesmo sem dor referida pelo atleta.
    vel_max_recorde = vel_max_recente = vel_max_pct_recorde = None
    if "Vel. Máx (km/h)" in sub.columns and sub["Vel. Máx (km/h)"].notna().any():
        vel_max_recorde = round(float(sub["Vel. Máx (km/h)"].max()), 1)
        ultimas_3 = sub.dropna(subset=["Vel. Máx (km/h)"]).tail(3)["Vel. Máx (km/h)"]
        if not ultimas_3.empty:
            vel_max_recente = round(float(ultimas_3.mean()), 1)
            vel_max_pct_recorde = round(vel_max_recente / vel_max_recorde * 100, 0) if vel_max_recorde else None

    kpis = {
        "sessoes_total": int(len(sub)),
        "carga_interna_media": round(float(sub["Carga Interna"].mean()), 0) if "Carga Interna" in sub.columns and sub["Carga Interna"].notna().any() else None,
        "acwr_atual": evolucao_acwr[-1]["acwr"] if evolucao_acwr else None,
        "hooper_medio": round(float(sub["Hooper Index"].mean()), 1) if "Hooper Index" in sub.columns and sub["Hooper Index"].notna().any() else None,
        "vel_max_recorde": vel_max_recorde,
        "vel_max_recente": vel_max_recente,
        "vel_max_pct_recorde": vel_max_pct_recorde,
    }

    colunas_disp = [(col, chave) for col, chave in COLUNAS_SESSAO if col in sub.columns]
    sessoes_recentes = []
    for _, row in sub.sort_values("Data", ascending=False).head(10).iterrows():
        data_val = row["Data"]
        item = {"data": data_val.date().isoformat() if pd.notna(data_val) else None}
        for col, chave in colunas_disp:
            v = row[col]
            item[chave] = _numero(v) if pd.notna(v) else None
        sessoes_recentes.append(item)

    # Carga externa do jogador ao longo das últimas sessões — para gráficos de
    # barras no perfil (mesmas métricas e cores da secção Carga Externa).
    sub_recentes = sub.tail(20)
    metricas_externas = [
        {"chave": m["chave"], "label": m["label"], "unidade": m["unidade"], "cor": m["cor"], "casas": m["casas"]}
        for m in METRICAS_EXTERNAS if m["col"] in sub.columns and sub[m["col"]].notna().any()
    ]
    evolucao_externa: dict[str, list[dict]] = {}
    for m in METRICAS_EXTERNAS:
        if m["col"] not in sub_recentes.columns:
            continue
        pontos = [
            {"data": row["Data"].date().isoformat(), "valor": round(float(row[m["col"]]), m["casas"])}
            for _, row in sub_recentes.dropna(subset=[m["col"]]).iterrows()
            if pd.notna(row["Data"])
        ]
        if pontos:
            evolucao_externa[m["chave"]] = pontos

    return {
        "jogadores_disponiveis": jogadores_disponiveis,
        "jogador": nome,
        "posicao": posicao,
        "kpis": kpis,
        "evolucao_carga": evolucao_carga,
        "evolucao_acwr": evolucao_acwr,
        "metricas_externas": metricas_externas,
        "evolucao_externa": evolucao_externa,
        "sessoes_recentes": sessoes_recentes,
    }
