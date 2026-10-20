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


def _tem_atletas(cur) -> bool:
    cur.execute(
        "select exists (select 1 from information_schema.columns where table_name = 'players' and column_name = 'atleta_id')"
    )
    return bool(cur.fetchone()[0])


# Sessões dos atletas desta equipa feitas noutras equipas da MESMA época (ex.:
# um sub-16 que treinou nos sub-17). Aparecem como se fossem do jogador local
# (player_id/nome/posição desta equipa) com "Equipa origem" preenchida — assim
# a PSE, o wellness e a carga externa ficam visíveis aos dois PF e entram no
# ACWR do jogador.
SQL_PARTILHADAS = """
    select gs.*, pl.nome as jogador_nome, pl.posicao as jogador_posicao,
           pl.id as jogador_local_id, coalesce(t.escalao, t.nome) as equipa_origem
    from players pl
    join teams tl on tl.id = pl.team_id
    join players po on po.atleta_id = pl.atleta_id and po.team_id <> pl.team_id
    join teams t on t.id = po.team_id
    join gps_sessions gs on gs.player_id = po.id
    where pl.team_id = %s and pl.ativo and pl.atleta_id is not null
      and t.epoca is not distinct from tl.epoca
"""


def _ler_df_equipa(team_id: str) -> pd.DataFrame:
    """Leitura real da BD: todas as sessões da equipa, excluindo jogadores
    marcados como inativos (`players.ativo = false`, ex: saíram do clube) —
    para os incluir de volta, usar estado_service.atualizar_ativo().
    Junta as sessões partilhadas de outras equipas (ver SQL_PARTILHADAS)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select gs.*, p.nome as jogador_nome, p.posicao as jogador_posicao,
                       p.id as jogador_local_id, null::text as equipa_origem
                from gps_sessions gs
                join players p on p.id = gs.player_id
                where gs.team_id = %s and p.ativo
                order by gs.data
                """,
                (team_id,),
            )
            colunas = [c.name for c in cur.description]
            linhas = list(cur.fetchall())
            try:
                if _tem_atletas(cur):
                    cur.execute(SQL_PARTILHADAS, (team_id,))
                    linhas += cur.fetchall()
            except Exception:  # partilha é um extra: nunca impede a equipa de carregar
                pass

    if not linhas:
        return pd.DataFrame()

    df = pd.DataFrame(linhas, columns=colunas)
    df = alinhar_partilhadas(df, team_id)
    df = df.rename(columns=DB_TO_CANONICAL)
    df["Jogador"] = df["jogador_nome"]
    df["Posição"] = df["jogador_posicao"]
    df["Data"] = pd.to_datetime(df["data"])
    df["Equipa origem"] = df["equipa_origem"]
    df = df.sort_values("Data", kind="stable").reset_index(drop=True)

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


def alinhar_partilhadas(df: pd.DataFrame, team_id: str) -> pd.DataFrame:
    """Põe as sessões vindas de outra equipa no referencial desta:
    player_id/team_id locais e microciclo/dia MD desta equipa nesse dia (o
    MD-2 dos sub-17 não é o MD-2 dos sub-16). Um jogo continua a ser "MD".
    Sem sessão local nesse dia, o microciclo é o que contém a data."""
    if df.empty or "equipa_origem" not in df.columns:
        return df
    df = df.copy()
    partilhada = df["equipa_origem"].notna()
    if not partilhada.any():
        return df
    df.loc[partilhada, "player_id"] = df.loc[partilhada, "jogador_local_id"]
    df.loc[partilhada, "team_id"] = team_id

    locais = df[~partilhada]
    por_dia: dict = {}
    intervalos: list = []
    if not locais.empty:
        for dia, g in locais.groupby("data"):
            mc = g["microciclo_nr"].dropna() if "microciclo_nr" in g else pd.Series(dtype=object)
            md = g["dia_md"].dropna() if "dia_md" in g else pd.Series(dtype=object)
            por_dia[dia] = (mc.mode().iloc[0] if not mc.empty else None, md.mode().iloc[0] if not md.empty else None)
        if "microciclo_nr" in locais:
            for mc, g in locais.dropna(subset=["microciclo_nr"]).groupby("microciclo_nr"):
                intervalos.append((g["data"].min(), g["data"].max(), mc))

    for i in df.index[partilhada]:
        dia = df.at[i, "data"]
        mc, md = por_dia.get(dia, (None, None))
        if mc is None:
            mc = next((m for ini, fim, m in intervalos if ini <= dia <= fim), None)
        if "microciclo_nr" in df:
            df.at[i, "microciclo_nr"] = mc
        if "dia_md" in df:
            jogo = str(df.at[i, "tipo"] or "").strip().lower() == "jogo" or df.at[i, "dia_md"] == "MD"
            df.at[i, "dia_md"] = "MD" if jogo else md
    return df
