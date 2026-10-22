"""Ligação Postgres com privilégios de escrita (service-role).

Mesmo padrão de retry/keepalive que auth.py usava na app Streamlit, mas sem
depender de st.secrets — lê de Settings (variáveis de ambiente).

IMPORTANTE: esta ligação ignora RLS (é a mesma que o Supabase usa
internamente para operações de administração). Qualquer endpoint que a use
é responsável por validar primeiro, em código, que o utilizador autenticado
(ver core/security.py) pertence à equipa cujos dados vai ler/escrever — a
base de dados não faz essa verificação por si nesta ligação.
"""
import os
import threading
import time
from contextlib import contextmanager

import psycopg2
import psycopg2.extensions
import psycopg2.extras
import psycopg2.pool

from app.core.config import get_settings

# ── Pool de ligações ─────────────────────────────────────────────────────────
# Abrir uma ligação nova ao Supabase custa TLS + autenticação (~100–300 ms) e
# acontecia em cada pedido (às vezes duas: uma para verificar a equipa e outra
# para os dados). O pool mantém até DB_POOL_MAX ligações abertas e reutiliza-as;
# se estiverem todas ocupadas, o pedido espera pela próxima livre (não falha).
# Com o Session pooler do Supabase (plano gratuito) não convém passar de ~10.
_POOL_MAX = int(os.environ.get("DB_POOL_MAX", "6"))
_IDLE_TESTE_S = 60  # ligação parada há mais tempo → testa antes de usar
_pool: psycopg2.pool.ThreadedConnectionPool | None = None
_pool_lock = threading.Lock()
_vagas = threading.BoundedSemaphore(_POOL_MAX)
_ultimo_uso: dict[int, float] = {}

# `numeric` do Postgres chega como float em vez de Decimal: menos conversões
# no pandas e JSON direto (os serviços já convertiam para float à mão).
_DEC2FLOAT = psycopg2.extensions.new_type(
    psycopg2.extensions.DECIMAL.values, "DEC2FLOAT",
    lambda v, cur: float(v) if v is not None else None,
)


def _nova_pool() -> psycopg2.pool.ThreadedConnectionPool:
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL não configurado no servidor.")
    return psycopg2.pool.ThreadedConnectionPool(
        1, _POOL_MAX, settings.database_url,
        # SSL obrigatório no Supabase; DB_SSLMODE=disable só para o Postgres
        # local dos testes das páginas (CI).
        sslmode=os.environ.get("DB_SSLMODE", "require"), connect_timeout=10,
        keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=5,
        application_name="loadmonitor-api",
    )


def _obter_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = _nova_pool()
    return _pool


def _ligacao_valida(conn) -> bool:
    if conn.closed:
        return False
    if time.monotonic() - _ultimo_uso.get(id(conn), 0) < _IDLE_TESTE_S:
        return True
    try:  # parada há algum tempo: o pooler pode tê-la fechado do lado dele
        with conn.cursor() as cur:
            cur.execute("select 1")
        conn.rollback()
        return True
    except psycopg2.Error:
        return False


def _adquirir(max_retries: int):
    tentativa = 0
    while True:
        try:
            pool = _obter_pool()
            conn = pool.getconn()
            if not _ligacao_valida(conn):
                pool.putconn(conn, close=True)
                conn = pool.getconn()
            psycopg2.extensions.register_type(_DEC2FLOAT, conn)
            return pool, conn
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            tentativa += 1
            if tentativa > max_retries:
                raise
            time.sleep(0.5 * tentativa)


@contextmanager
def get_conn(max_retries: int = 2):
    """Ligação do pool, numa transação: commit no fim, rollback se houver erro."""
    _vagas.acquire()
    try:
        pool, conn = _adquirir(max_retries)
        partida = False
        try:
            yield conn
            conn.commit()
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            partida = True
            raise
        except Exception:
            try:
                conn.rollback()
            except psycopg2.Error:
                partida = True
            raise
        finally:
            _ultimo_uso[id(conn)] = time.monotonic()
            pool.putconn(conn, close=partida or conn.closed != 0)
    finally:
        _vagas.release()


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
