"""Ingestão de ficheiros GPS — Fase 4 do plano de migração.

Reutiliza a lógica de carregamento/normalização de utils/dados.py quase
verbatim (o objetivo explícito do plano): o único adaptador novo é o passo
de escrita em Postgres, que não existia antes (na app Streamlit os dados
eram descartados no fim da sessão).
"""
import io
import json
import math
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd
import psycopg2.extras

from utils.dados import (
    carregar_dados_com_mapa,
    carregar_dados_safe,
    carregar_exercicios,
)

from app.core.db import get_conn

# Mapa: coluna canónica (utils/dados.py) → coluna da tabela gps_sessions.
# Jogador/Posição não entram aqui — resolvem-se via o upsert de `players`.
CANONICAL_TO_DB_SESSAO = {
    "Tipo": "tipo",
    "Dia MD": "dia_md",
    "Microciclo (Nr)": "microciclo_nr",
    "Distância Total (m)": "distancia_total_m",
    "HSR (m)": "hsr_m",
    "Sprint (m)": "sprint_m",
    "Acc (n)": "acc_n",
    "Dcc (n)": "dcc_n",
    "Vel. Máx (km/h)": "vel_max_kmh",
    "PSE Sessão": "pse_sessao",
    "Duração (min)": "duracao_min",
    "Carga Interna": "carga_interna",
    "Hooper Index": "hooper_index",
    "Sono (1-5)": "sono",
    "Dor Musc. (1-5)": "dor_musc",
    "Stress (1-5)": "stress",
    "Humor (1-5)": "humor",
}
COLUNAS_IGNORAR_SESSAO = {"Jogador", "Posição", "Data", "Observações"}

CANONICAL_TO_DB_EXERCICIO = {
    "Microciclo (Nr)": "microciclo_nr",
    "Dia MD": "dia_md",
    "Exercício": "exercicio",
    "Categoria": "categoria",
    "Duração (min)": "duracao_min",
    "Nº Jogadores": "n_jogadores",
    "PSE Exercício": "pse_exercicio",
    "Distância Total (m)": "distancia_total_m",
    "HSR (m)": "hsr_m",
    "Sprint (m)": "sprint_m",
    "Acc (n)": "acc_n",
    "Dcc (n)": "dcc_n",
    "Vel. Máx (km/h)": "vel_max_kmh",
}
COLUNAS_IGNORAR_EXERCICIO = {"Data"}


def _limpo(v: Any):
    """Converte NaN/NaT para None e tipos numpy para tipos nativos Python.

    Necessário em dois pontos: psycopg2 não sabe adaptar numpy.int64/float64
    diretamente (`can't adapt type 'numpy.int64'`), e json.dumps() também
    não serializa tipos numpy — utils/dados.py devolve estes tipos porque
    coerce para numérico é feito com pandas (pd.to_numeric).
    """
    if v is None:
        return None
    if isinstance(v, np.generic):
        v = v.item()
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, (pd.Timestamp, datetime)):
        return v.date().isoformat() if not isinstance(v, date) else v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return v


def _extra_metrics(row: pd.Series, mapa: dict, ignorar: set) -> dict:
    extra = {}
    for col, val in row.items():
        if col in mapa or col in ignorar:
            continue
        val = _limpo(val)
        if val is not None:
            extra[col] = val
    return extra


def _chave_nome(nome: str) -> str:
    """Chave de comparação insensível a maiúsculas/espaçamento — evita que
    "João Seco" e "joão seco" sejam tratados como jogadores diferentes."""
    return " ".join(str(nome).split()).lower()


def _upsert_players(cur, team_id: str, nomes_posicoes: dict[str, str | None]) -> dict[str, str]:
    """Devolve {nome: player_id}, criando jogadores novos por (team_id, nome).
    Compara nomes já existentes de forma insensível a maiúsculas/espaçamento."""
    cur.execute("select id, nome from players where team_id = %s", (team_id,))
    existentes = {_chave_nome(nome): pid for pid, nome in cur.fetchall()}

    mapa_nome_id: dict[str, str] = {}
    for nome, posicao in nomes_posicoes.items():
        nome_limpo = str(nome).strip()
        chave = _chave_nome(nome_limpo)
        if not chave:
            continue
        if chave in existentes:
            mapa_nome_id[nome] = existentes[chave]
            continue
        cur.execute(
            "insert into players (team_id, nome, posicao) values (%s, %s, %s) "
            "on conflict (team_id, nome) do update set posicao = coalesce(excluded.posicao, players.posicao) "
            "returning id",
            (team_id, nome_limpo, posicao),
        )
        player_id = cur.fetchone()[0]
        mapa_nome_id[nome] = player_id
        existentes[chave] = player_id
    return mapa_nome_id


def _ler_exercicios(filename: str, conteudo: bytes) -> pd.DataFrame | None:
    buffer_ex = io.BytesIO(conteudo)
    buffer_ex.name = filename
    return carregar_exercicios(buffer_ex)


def processar_upload(team_id: str, uploaded_by: str, filename: str, conteudo: bytes, substituir: bool = True) -> dict:
    """Fluxo automático: deteta as colunas sozinho e grava."""
    buffer = io.BytesIO(conteudo)
    buffer.name = filename

    df, erro = carregar_dados_safe(buffer)
    if erro:
        return {"status": "error", "error": erro}
    if df is None or df.empty:
        return {"status": "error", "error": "O ficheiro não contém dados válidos."}

    df_ex = _ler_exercicios(filename, conteudo)
    return _gravar(team_id, uploaded_by, filename, df, df_ex, substituir)


def processar_upload_com_mapa(
    team_id: str, uploaded_by: str, filename: str, conteudo: bytes,
    mapa: dict, substituir: bool = True,
) -> dict:
    """Fluxo de importação robusta: usa o mapeamento de colunas confirmado
    pelo utilizador (coluna_crua → nome canónico) em vez da deteção
    automática. Valida que 'Jogador' está presente antes de gravar."""
    buffer = io.BytesIO(conteudo)
    buffer.name = filename
    try:
        df = carregar_dados_com_mapa(buffer, mapa)
    except Exception:
        return {"status": "error", "error": "Não foi possível ler o ficheiro com o mapeamento indicado."}
    if df is None or df.empty:
        return {"status": "error", "error": "O ficheiro não contém dados válidos."}
    if "Jogador" not in df.columns:
        return {"status": "error", "error": "Falta mapear a coluna do nome do jogador — sem ela não é possível importar."}

    df_ex = _ler_exercicios(filename, conteudo)
    return _gravar(team_id, uploaded_by, filename, df, df_ex, substituir)


def _gravar(team_id: str, uploaded_by: str, filename: str, df: pd.DataFrame,
            df_ex: pd.DataFrame | None, substituir: bool) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            if substituir:
                # Cada upload SUBSTITUI os dados anteriores da equipa (em vez
                # de somar) — evita planteis/sessões de uploads antigos e
                # novos ficarem misturados no mesmo dashboard.
                cur.execute("delete from gps_sessions where team_id = %s", (team_id,))
                cur.execute("delete from exercises where team_id = %s", (team_id,))
                cur.execute("delete from players where team_id = %s", (team_id,))

            cur.execute(
                "insert into uploads (team_id, uploaded_by, filename, status) "
                "values (%s, %s, %s, 'processing') returning id",
                (team_id, uploaded_by, filename),
            )
            upload_id = cur.fetchone()[0]

            posicoes = df.groupby("Jogador")["Posição"].last().to_dict() if "Posição" in df.columns else {}
            jogadores = {nome: posicoes.get(nome) for nome in df["Jogador"].dropna().unique()}
            mapa_jogadores = _upsert_players(cur, team_id, jogadores)

            linhas_sessao = []
            for _, row in df.dropna(subset=["Jogador"]).iterrows():
                player_id = mapa_jogadores.get(row["Jogador"])
                if not player_id or pd.isna(row.get("Data")):
                    continue
                valores = {db_col: _limpo(row.get(col)) for col, db_col in CANONICAL_TO_DB_SESSAO.items()}
                linhas_sessao.append((
                    team_id, player_id, upload_id, _limpo(row["Data"]),
                    valores.get("tipo"), valores.get("dia_md"), valores.get("microciclo_nr"),
                    valores.get("distancia_total_m"), valores.get("hsr_m"), valores.get("sprint_m"),
                    valores.get("acc_n"), valores.get("dcc_n"), valores.get("vel_max_kmh"),
                    valores.get("pse_sessao"), valores.get("duracao_min"),
                    valores.get("carga_interna"), valores.get("hooper_index"),
                    valores.get("sono"), valores.get("dor_musc"), valores.get("stress"), valores.get("humor"),
                    json.dumps(_extra_metrics(row, CANONICAL_TO_DB_SESSAO, COLUNAS_IGNORAR_SESSAO)),
                ))

            if linhas_sessao:
                psycopg2.extras.execute_values(
                    cur,
                    """
                    insert into gps_sessions (
                        team_id, player_id, upload_id, data, tipo, dia_md, microciclo_nr,
                        distancia_total_m, hsr_m, sprint_m, acc_n, dcc_n, vel_max_kmh,
                        pse_sessao, duracao_min, carga_interna, hooper_index,
                        sono, dor_musc, stress, humor, extra_metrics
                    ) values %s
                    on conflict (team_id, player_id, data, tipo) do update set
                        distancia_total_m = excluded.distancia_total_m,
                        hsr_m = excluded.hsr_m,
                        sprint_m = excluded.sprint_m,
                        acc_n = excluded.acc_n,
                        dcc_n = excluded.dcc_n,
                        vel_max_kmh = excluded.vel_max_kmh,
                        pse_sessao = excluded.pse_sessao,
                        duracao_min = excluded.duracao_min,
                        carga_interna = excluded.carga_interna,
                        hooper_index = excluded.hooper_index,
                        sono = excluded.sono, dor_musc = excluded.dor_musc,
                        stress = excluded.stress, humor = excluded.humor,
                        extra_metrics = excluded.extra_metrics
                    """,
                    linhas_sessao,
                )

            linhas_exercicio = []
            if df_ex is not None and not df_ex.empty:
                for _, row in df_ex.iterrows():
                    valores = {db_col: _limpo(row.get(col)) for col, db_col in CANONICAL_TO_DB_EXERCICIO.items()}
                    linhas_exercicio.append((
                        team_id, upload_id, _limpo(row.get("Data")),
                        valores.get("microciclo_nr"), valores.get("dia_md"),
                        valores.get("exercicio"), valores.get("categoria"),
                        valores.get("duracao_min"), valores.get("n_jogadores"), valores.get("pse_exercicio"),
                        valores.get("distancia_total_m"), valores.get("hsr_m"), valores.get("sprint_m"),
                        valores.get("acc_n"), valores.get("dcc_n"), valores.get("vel_max_kmh"),
                        json.dumps(_extra_metrics(row, CANONICAL_TO_DB_EXERCICIO, COLUNAS_IGNORAR_EXERCICIO)),
                    ))
                if linhas_exercicio:
                    psycopg2.extras.execute_values(
                        cur,
                        """
                        insert into exercises (
                            team_id, upload_id, data, microciclo_nr, dia_md,
                            exercicio, categoria, duracao_min, n_jogadores, pse_exercicio,
                            distancia_total_m, hsr_m, sprint_m, acc_n, dcc_n, vel_max_kmh,
                            extra_metrics
                        ) values %s
                        """,
                        linhas_exercicio,
                    )

            cur.execute(
                "update uploads set status = 'done', row_count = %s where id = %s",
                (len(linhas_sessao), upload_id),
            )

    return {
        "status": "done",
        "upload_id": str(upload_id),
        "jogadores": len(mapa_jogadores),
        "sessoes_gravadas": len(linhas_sessao),
        "exercicios_gravados": len(linhas_exercicio),
    }
