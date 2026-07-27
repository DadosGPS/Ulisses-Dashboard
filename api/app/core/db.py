"""Ligação Postgres com privilégios de escrita (service-role).

Mesmo padrão de retry/keepalive que auth.py usava na app Streamlit, mas sem
depender de st.secrets — lê de Settings (variáveis de ambiente).

IMPORTANTE: esta ligação ignora RLS (é a mesma que o Supabase usa
internamente para operações de administração). Qualquer endpoint que a use
é responsável por validar primeiro, em código, que o utilizador autenticado
(ver core/security.py) pertence à equipa cujos dados vai ler/escrever — a
base de dados não faz essa verificação por si nesta ligação.
"""
import time
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

from app.core.config import get_settings


@contextmanager
def get_conn(max_retries: int = 2):
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL não configurado no servidor.")

    tentativa = 0
    while True:
        try:
            conn = psycopg2.connect(
                settings.database_url,
                sslmode="require",
                connect_timeout=10,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5,
                application_name="loadmonitor-api",
            )
            break
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            tentativa += 1
            if tentativa > max_retries:
                raise
            time.sleep(0.5 * tentativa)

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def verificar_pertenca_equipa(user_id: str, team_id: str) -> bool:
    """Confirma que `user_id` é membro de `team_id`, antes de qualquer escrita
    feita pela API (que usa uma ligação com privilégios de service-role e
    portanto não passa pelas políticas RLS automaticamente)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select 1 from team_members where team_id = %s and user_id = %s",
                (team_id, user_id),
            )
            return cur.fetchone() is not None
