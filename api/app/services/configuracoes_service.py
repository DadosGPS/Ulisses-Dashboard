"""Definições (CRUD) — gestão da equipa e do plantel.

Escrita direta na base de dados via ligação service-role (o router valida
sempre a pertença à equipa antes de chamar). Ativar/desativar e estado de
disponibilidade vivem em estado_service; aqui trata-se de nome/desporto da
equipa e de criar/editar jogadores.
"""
import psycopg2

from app.core.db import get_conn
from app.services.estado_service import listar_estados


def obter_configuracoes(team_id: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select nome, desporto from teams where id = %s", (team_id,))
            row = cur.fetchone()
    equipa = {"nome": row[0], "desporto": row[1]} if row else {"nome": "", "desporto": ""}
    return {"equipa": equipa, "jogadores": listar_estados(team_id)}


def atualizar_equipa(team_id: str, nome: str, desporto: str | None) -> dict:
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("O nome da equipa não pode ficar vazio.")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "update teams set nome = %s, desporto = coalesce(nullif(%s, ''), desporto) where id = %s returning nome, desporto",
                (nome, (desporto or "").strip(), team_id),
            )
            row = cur.fetchone()
    if row is None:
        raise ValueError("Equipa não encontrada.")
    return {"nome": row[0], "desporto": row[1]}


def criar_jogador(team_id: str, nome: str, posicao: str | None) -> dict:
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("O nome do jogador não pode ficar vazio.")
    posicao = (posicao or "").strip() or None
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into players (team_id, nome, posicao)
                    values (%s, %s, %s)
                    returning id, nome, posicao, estado, estado_motivo, estado_desde, ativo
                    """,
                    (team_id, nome, posicao),
                )
                row = cur.fetchone()
    except psycopg2.errors.UniqueViolation:
        raise ValueError(f"Já existe um jogador chamado “{nome}” nesta equipa.")
    return _linha_jogador(row)


def atualizar_jogador(team_id: str, player_id: str, nome: str, posicao: str | None) -> dict | None:
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("O nome do jogador não pode ficar vazio.")
    posicao = (posicao or "").strip() or None
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update players set nome = %s, posicao = %s
                    where team_id = %s and id = %s
                    returning id, nome, posicao, estado, estado_motivo, estado_desde, ativo
                    """,
                    (nome, posicao, team_id, player_id),
                )
                row = cur.fetchone()
    except psycopg2.errors.UniqueViolation:
        raise ValueError(f"Já existe um jogador chamado “{nome}” nesta equipa.")
    return _linha_jogador(row) if row else None


def _linha_jogador(row) -> dict:
    return {
        "player_id": str(row[0]),
        "nome": row[1],
        "posicao": row[2],
        "estado": row[3],
        "estado_motivo": row[4],
        "estado_desde": row[5].isoformat() if row[5] else None,
        "ativo": row[6],
    }
