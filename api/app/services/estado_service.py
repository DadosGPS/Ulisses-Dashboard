"""Estado de disponibilidade dos jogadores (apto/lesionado/em recuperação/
ausente) — sem isto, a app media carga mas não sabia dizer quem estava
indisponível, nem conseguia distinguir "ACWR alto = alerta novo" de
"ACWR alto = jogador já lesionado, motivo conhecido"."""
from app.core.db import get_conn

ESTADOS_VALIDOS = {"apto", "lesionado", "em_recuperacao", "ausente"}


def listar_estados(team_id: str) -> list[dict]:
    """Devolve TODOS os jogadores (incluindo inativos) — ao contrário de
    carregar_df_equipa(), que só usa os ativos. É preciso ver os inativos
    aqui para poder reativá-los (ex: jogador volta de empréstimo)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, nome, posicao, estado, estado_motivo, estado_desde, ativo
                from players
                where team_id = %s
                order by ativo desc, nome
                """,
                (team_id,),
            )
            linhas = cur.fetchall()

    return [
        {
            "player_id": str(row[0]),
            "nome": row[1],
            "posicao": row[2],
            "estado": row[3],
            "estado_motivo": row[4],
            "estado_desde": row[5].isoformat() if row[5] else None,
            "ativo": row[6],
        }
        for row in linhas
    ]


def atualizar_ativo(team_id: str, player_id: str, ativo: bool) -> dict | None:
    """Marca um jogador como inativo (saiu do clube) ou reativa-o — não
    apaga histórico, só deixa de entrar nas listas/cálculos correntes."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update players set ativo = %s
                where team_id = %s and id = %s
                returning id, nome, posicao, estado, estado_motivo, estado_desde, ativo
                """,
                (ativo, team_id, player_id),
            )
            row = cur.fetchone()

    if row is None:
        return None
    return {
        "player_id": str(row[0]),
        "nome": row[1],
        "posicao": row[2],
        "estado": row[3],
        "estado_motivo": row[4],
        "estado_desde": row[5].isoformat() if row[5] else None,
        "ativo": row[6],
    }


def atualizar_estado(team_id: str, player_id: str, estado: str, motivo: str | None) -> dict | None:
    if estado not in ESTADOS_VALIDOS:
        raise ValueError(f"Estado inválido: {estado}")

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update players
                set estado = %s,
                    estado_motivo = %s,
                    -- só reinicia a data quando o estado muda de facto —
                    -- voltar a gravar "lesionado" não deve apagar há quanto
                    -- tempo o jogador está fora.
                    estado_desde = case when estado != %s then current_date else estado_desde end
                where team_id = %s and id = %s
                returning id, nome, posicao, estado, estado_motivo, estado_desde, ativo
                """,
                (estado, motivo, estado, team_id, player_id),
            )
            row = cur.fetchone()

    if row is None:
        return None
    return {
        "player_id": str(row[0]),
        "nome": row[1],
        "posicao": row[2],
        "estado": row[3],
        "estado_motivo": row[4],
        "estado_desde": row[5].isoformat() if row[5] else None,
        "ativo": row[6],
    }
