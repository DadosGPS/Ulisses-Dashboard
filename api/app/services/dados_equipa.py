"""Carregamento partilhado: gps_sessions (Postgres) → DataFrame com nomes de
colunas canónicos, reutilizado por todos os serviços (dashboard, equipa, ...).

Tem um cache em memória com TTL curto: uma abertura do dashboard chama vários
endpoints que leem a mesma equipa quase em simultâneo — sem cache, isso eram
várias leituras completas à BD por segundo. O cache é invalidado no import
(ver invalidar_cache_equipa) e expira sozinho ao fim de _CACHE_TTL_S.
"""
import json
import time

import pandas as pd

from app.core.db import get_conn
from utils.dados import normalizar_tipo

# TTL curto: colapsa as leituras concorrentes de uma abertura de página sem
# arriscar mostrar dados desatualizados por muito tempo.
_CACHE_TTL_S = 30.0
_cache: dict[str, tuple[float, pd.DataFrame]] = {}


def invalidar_cache_equipa(team_id: str | None = None) -> None:
    """Esvazia o cache de uma equipa (ou de todas). Chamado após um import,
    para o novo dado aparecer de imediato em vez de esperar pelo TTL."""
    if team_id is None:
        _cache.clear()
    else:
        _cache.pop(team_id, None)

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


def carregar_df_equipa(team_id: str, usar_cache: bool = True) -> pd.DataFrame:
    """Carrega todas as sessões da equipa (jogadores ativos), com cache TTL.

    Devolve sempre uma cópia — os serviços a jusante filtram e alteram o
    DataFrame, e não podem corromper a entrada em cache."""
    if usar_cache:
        entrada = _cache.get(team_id)
        if entrada is not None and (time.monotonic() - entrada[0]) < _CACHE_TTL_S:
            return entrada[1].copy()
    df = _ler_df_equipa(team_id)
    _cache[team_id] = (time.monotonic(), df)
    return df.copy()


def _ler_df_equipa(team_id: str) -> pd.DataFrame:
    """Leitura real da BD: todas as sessões da equipa, excluindo jogadores
    marcados como inativos (`players.ativo = false`, ex: saíram do clube) —
    para os incluir de volta, usar estado_service.atualizar_ativo()."""
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

    # Normaliza o Tipo de sessão (Jogo vs Treino) tolerando grafias diferentes —
    # um único ponto que corrige toda a deteção de jogo a jusante (match
    # benchmark, exposição HSR/Sprint), inclusive nos dados já guardados.
    if "Tipo" in df.columns:
        df["Tipo"] = df["Tipo"].apply(normalizar_tipo)

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
