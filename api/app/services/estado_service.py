"""Estado de disponibilidade dos jogadores (apto/lesionado/em recuperação/
ausente) — sem isto, a app media carga mas não sabia dizer quem estava
indisponível, nem conseguia distinguir "ACWR alto = alerta novo" de
"ACWR alto = jogador já lesionado, motivo conhecido"."""
from app.core.db import get_conn

ESTADOS_VALIDOS = {"apto", "lesionado", "em_recuperacao", "ausente"}


def listar_estados(team_id: str) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, nome, posicao, estado, estado_motivo, estado_desde
                from players
                where team_id = %s
                order by nome
                """,
                (team_id,),
            )
            colunas = [c.name for c in cur.description]
            linhas = cur.fetchall()

    return [
        {
            "player_id": str(row[0]),
            "nome": row[1],
            "posicao": row[2],
            "estado": row[3],
            "estado_motivo": row[4],
            "estado_desde": row[5].isoformat() if row[5] else None,
        }
        for row in linhas
    ]


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
                returning id, nome, posicao, estado, estado_motivo, estado_desde
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
    }
