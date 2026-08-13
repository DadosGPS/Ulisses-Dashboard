"""Carregamento partilhado: gps_sessions (Postgres) → DataFrame com nomes de
colunas canónicos, reutilizado por todos os serviços (dashboard, equipa, ...).
"""
import json

import pandas as pd

from app.core.db import get_conn

DB_TO_CANONICAL = {
    "tipo": "Tipo",
    "dia_md": "Dia MD",
    "microciclo_nr": "Microciclo (Nr)",
    "distancia_total_m": "Distância Total (m)",
    "hsr_m": "HSR (m)",
    "sprint_m": "Sprint (m)",
    "acc_n": "Acc (n)",
    "dcc_n": "Dcc (n)",
    "vel_max_kmh": "Vel. Máx (km/h)",
    "pse_sessao": "PSE Sessão",
    "duracao_min": "Duração (min)",
    "carga_interna": "Carga Interna",
    "hooper_index": "Hooper Index",
    "sono": "Sono (1-5)",
    "dor_musc": "Dor Musc. (1-5)",
    "stress": "Stress (1-5)",
    "humor": "Humor (1-5)",
}


def carregar_df_equipa(team_id: str) -> pd.DataFrame:
    """Carrega todas as sessões da equipa, excluindo jogadores marcados como
    inativos (`players.ativo = false`, ex: saíram do clube) — para os
    incluir de volta, usar estado_service.atualizar_ativo()."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select gs.*, p.nome as jogador_nome, p.posicao as jogador_posicao
                from gps_sessions gs
                join players p on p.id = gs.player_id
                where gs.team_id = %s and p.ativo
                order by gs.data
                """,
                (team_id,),
            )
            colunas = [c.name for c in cur.description]
            linhas = cur.fetchall()

    if not linhas:
        return pd.DataFrame()

    df = pd.DataFrame(linhas, columns=colunas)
    df = df.rename(columns=DB_TO_CANONICAL)
    df["Jogador"] = df["jogador_nome"]
    df["Posição"] = df["jogador_posicao"]
    df["Data"] = pd.to_datetime(df["data"])

    # Colunas `numeric` do Postgres chegam via psycopg2 como Decimal, não
    # float — ficam guardadas como dtype "object" no DataFrame. A maioria das
    # operações (mean/sum/max) tolera isso, mas .std() não (mistura Decimal
    # com float internamente e rebenta com TypeError) — por isso converte-se
    # aqui, uma vez, em vez de em cada função que eventualmente use .std().
    COLUNAS_NUMERICAS = [c for c in DB_TO_CANONICAL.values() if c != "Tipo" and c != "Dia MD"]
    for col in COLUNAS_NUMERICAS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # extra_metrics (jsonb) → colunas adicionais, para preservar a deteção
    # dinâmica de métricas que get_mets_gps() já suportava na app Streamlit.
    extras = df["extra_metrics"].apply(lambda v: v if isinstance(v, dict) else (json.loads(v) if v else {}))
    if extras.apply(len).sum() > 0:
        df_extras = pd.json_normalize(extras)
        df = pd.concat([df.reset_index(drop=True), df_extras.reset_index(drop=True)], axis=1)

    return df
