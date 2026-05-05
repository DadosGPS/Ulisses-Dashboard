"""
LoadMonitor — Módulo de Autenticação e Base de Dados Multi-Utilizador
Usa Postgres (Supabase). Mantém a mesma API pública que a versão SQLite.

Configuração: a connection string deve estar em st.secrets["DB_URL"] ou
              na variável de ambiente DB_URL.

NOTA SOBRE A FASE BETA/DEMO:
  Durante a fase de demonstração, todos os utilizadores são criados com
  plano 'pro' permanente (trial_fim=NULL). Não há despromoção automática.
  Quando o Pro pago abrir, será feita uma transição gerida com aviso.
"""

import hashlib
import secrets
import json
import os
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

# ── Configuração ──────────────────────────────────────────────────────────────
def _get_db_url() -> str:
    """Obtém connection string do Streamlit Secrets ou env var."""
    # Tentar primeiro Streamlit Secrets
    try:
        import streamlit as st
        url = st.secrets.get("DB_URL", None)
        if url:
            return url
    except Exception:
        pass
    # Fallback para variável de ambiente
    url = os.environ.get("DB_URL", "")
    if not url:
        raise RuntimeError(
            "DB_URL não está configurada. Adiciona a connection string do Postgres "
            "em Streamlit Secrets como DB_URL ou na variável de ambiente DB_URL."
        )
    return url


@contextmanager
def get_conn():
    """Context manager para conexão Postgres. Faz commit/rollback automático."""
    conn = psycopg2.connect(_get_db_url())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


PLANOS = {
    "free": {
        "nome": "Free",
        "preco": 0,
        "max_equipas": 1,
        "max_atletas": 15,
        "funcionalidades": ["dashboard_base", "acwr", "wellness"],
        "gps": False,
        "rhie": False,
    },
    "pro": {
        "nome": "Pro",
        "preco": 19,
        "max_equipas": -1,
        "max_atletas": -1,
        "funcionalidades": ["dashboard_base", "acwr", "wellness", "zscore",
                            "vmax", "monotonia", "lesoes", "comparacao",
                            "testes_neuromusculares", "gps_viz", "rhie",
                            "notificacoes", "exportar_pdf"],
        "gps": True,
        "rhie": True,
    },
}


# ── Inicialização da base de dados ────────────────────────────────────────────
def init_db():
    """
    Verifica se as tabelas existem. Se não, cria-as.
    Para uso em produção, é preferível correr o `migrations/001_initial_schema.sql`
    manualmente no SQL Editor do Supabase. Esta função é fallback.
    """
    schema_sql = """
    CREATE TABLE IF NOT EXISTS utilizadores (
        id                  SERIAL PRIMARY KEY,
        email               TEXT UNIQUE NOT NULL,
        password_hash       TEXT NOT NULL,
        nome                TEXT NOT NULL,
        clube               TEXT,
        plano               TEXT DEFAULT 'free',
        ativo               BOOLEAN DEFAULT TRUE,
        trial_fim           TIMESTAMPTZ,
        criado_em           TIMESTAMPTZ DEFAULT NOW(),
        ultimo_login        TIMESTAMPTZ,
        token               TEXT,
        tentativas_falhadas INTEGER DEFAULT 0,
        bloqueado_ate       TIMESTAMPTZ,
        stripe_customer_id     TEXT,
        stripe_subscription_id TEXT
    );
    CREATE TABLE IF NOT EXISTS sessoes (
        id              SERIAL PRIMARY KEY,
        utilizador_id   INTEGER NOT NULL REFERENCES utilizadores(id) ON DELETE CASCADE,
        token           TEXT NOT NULL UNIQUE,
        criado_em       TIMESTAMPTZ DEFAULT NOW(),
        expira_em       TIMESTAMPTZ NOT NULL
    );
    CREATE TABLE IF NOT EXISTS equipas (
        id              SERIAL PRIMARY KEY,
        utilizador_id   INTEGER NOT NULL REFERENCES utilizadores(id) ON DELETE CASCADE,
        nome            TEXT NOT NULL,
        desporto        TEXT DEFAULT 'Futebol',
        criado_em       TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS log_acessos (
        id              SERIAL PRIMARY KEY,
        utilizador_id   INTEGER REFERENCES utilizadores(id) ON DELETE SET NULL,
        pagina          TEXT,
        timestamp       TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS preferencias (
        utilizador_id   INTEGER NOT NULL REFERENCES utilizadores(id) ON DELETE CASCADE,
        chave           TEXT NOT NULL,
        valor           TEXT,
        atualizado_em   TIMESTAMPTZ DEFAULT NOW(),
        PRIMARY KEY (utilizador_id, chave)
    );
    CREATE TABLE IF NOT EXISTS password_resets (
        id              SERIAL PRIMARY KEY,
        utilizador_id   INTEGER NOT NULL REFERENCES utilizadores(id) ON DELETE CASCADE,
        token           TEXT NOT NULL UNIQUE,
        expira_em       TIMESTAMPTZ NOT NULL,
        usado           BOOLEAN DEFAULT FALSE,
        criado_em       TIMESTAMPTZ DEFAULT NOW()
    );

    -- Índices para performance (lookups frequentes)
    CREATE INDEX IF NOT EXISTS idx_sessoes_token         ON sessoes(token);
    CREATE INDEX IF NOT EXISTS idx_sessoes_utilizador    ON sessoes(utilizador_id);
    CREATE INDEX IF NOT EXISTS idx_pwdreset_token        ON password_resets(token);
    CREATE INDEX IF NOT EXISTS idx_pwdreset_utilizador   ON password_resets(utilizador_id);
    CREATE INDEX IF NOT EXISTS idx_pwdreset_criado       ON password_resets(criado_em);
    CREATE INDEX IF NOT EXISTS idx_preferencias_user     ON preferencias(utilizador_id);
    CREATE INDEX IF NOT EXISTS idx_utilizadores_stripe   ON utilizadores(stripe_customer_id);
    """
    try:
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute(schema_sql)
    except Exception as e:
        # Não rebenta a app se a BD não estiver acessível na altura do import
        print(f"[auth.init_db] Aviso: não foi possível inicializar BD: {e}")


# ── Funções de password ───────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    """Hash seguro com salt usando PBKDF2-HMAC-SHA256 (260k iterações)."""
    salt = secrets.token_hex(32)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 260000
    ).hex()
    return f"{salt}:{pwd_hash}"


def verificar_password(password: str, stored_hash: str) -> bool:
    """Verifica se a password corresponde ao hash guardado."""
    try:
        salt, expected_hash = stored_hash.split(":")
    except ValueError:
        return False
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 260000
    ).hex()
    return secrets.compare_digest(pwd_hash, expected_hash)


# ── Registo ───────────────────────────────────────────────────────────────────
def registar_utilizador(email: str, password: str, nome: str, clube: str = "") -> dict:
    """
    Regista um novo utilizador.

    DURANTE A FASE BETA/DEMO: cria com plano 'pro' permanente (trial_fim=NULL).
    Não há despromoção automática. Esta política é revista quando o Pro pago abrir.

    Retorna {"sucesso": True, "id": ...} ou {"sucesso": False, "erro": ...}
    """
    if len(password) < 8:
        return {"sucesso": False, "erro": "A password deve ter pelo menos 8 caracteres."}
    if "@" not in email or "." not in email:
        return {"sucesso": False, "erro": "Email inválido."}
    if not nome.strip():
        return {"sucesso": False, "erro": "O nome é obrigatório."}

    try:
        with get_conn() as conn:
            with conn.cursor() as c:
                pwd_hash = hash_password(password)
                # FASE BETA: plano='pro', trial_fim=NULL (sem expiração)
                try:
                    c.execute("""
                        INSERT INTO utilizadores (email, password_hash, nome, clube, plano, trial_fim)
                        VALUES (%s, %s, %s, %s, 'pro', NULL)
                        RETURNING id
                    """, (email.lower().strip(), pwd_hash, nome.strip(), clube.strip()))
                    user_id = c.fetchone()[0]
                except psycopg2.errors.UniqueViolation:
                    return {"sucesso": False, "erro": "Este email já está registado."}

                # Criar equipa padrão
                c.execute("""
                    INSERT INTO equipas (utilizador_id, nome) VALUES (%s, %s)
                """, (user_id, clube.strip() or "A Minha Equipa"))

                # Enviar email de boas-vindas (não bloqueia se falhar)
                try:
                    from utils.email import enviar_email_boas_vindas
                    enviar_email_boas_vindas(email.lower().strip(), nome.strip())
                except Exception as _e:
                    print(f"[auth.registar_utilizador] Aviso: falhou envio email boas-vindas: {_e}")

                return {
                    "sucesso": True,
                    "id": user_id,
                    "trial_fim": None,
                }
    except Exception as e:
        return {"sucesso": False, "erro": f"Erro ao criar conta: {e}"}


# ── Login ─────────────────────────────────────────────────────────────────────
def fazer_login(email: str, password: str) -> dict:
    """
    Autentica utilizador.
    Retorna {"sucesso": True, "token": ..., "utilizador": {...}} ou erro.
    Inclui rate limiting: 5 tentativas falhadas → bloqueio de 15 min.

    NOTA BETA: Não faz downgrade automático de Pro → Free. Durante a fase
    de demonstração, todos os utilizadores mantêm acesso completo.
    """
    try:
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute("""
                    SELECT id, password_hash, nome, clube, plano, ativo, trial_fim,
                           tentativas_falhadas, bloqueado_ate
                    FROM utilizadores WHERE email = %s
                """, (email.lower().strip(),))
                row = c.fetchone()

                if not row:
                    return {"sucesso": False, "erro": "Email ou password incorretos."}

                (user_id, pwd_hash, nome, clube, plano, ativo,
                 trial_fim, tent_falhadas, bloqueado_ate) = row

                if not ativo:
                    return {"sucesso": False, "erro": "Conta desativada. Contacta o suporte."}

                # Rate limiting
                now_utc = datetime.now(timezone.utc)
                if bloqueado_ate and bloqueado_ate > now_utc:
                    minutos = int((bloqueado_ate - now_utc).total_seconds() // 60) + 1
                    return {
                        "sucesso": False,
                        "erro": f"Conta bloqueada por demasiadas tentativas. Tenta novamente em {minutos} min."
                    }

                if not verificar_password(password, pwd_hash):
                    # Incrementar contador
                    novas_tent = (tent_falhadas or 0) + 1
                    if novas_tent >= 5:
                        c.execute("""
                            UPDATE utilizadores
                            SET tentativas_falhadas = %s,
                                bloqueado_ate = %s
                            WHERE id = %s
                        """, (novas_tent, now_utc + timedelta(minutes=15), user_id))
                        return {
                            "sucesso": False,
                            "erro": "Demasiadas tentativas falhadas. Conta bloqueada 15 min."
                        }
                    else:
                        c.execute("""
                            UPDATE utilizadores SET tentativas_falhadas = %s WHERE id = %s
                        """, (novas_tent, user_id))
                        return {"sucesso": False, "erro": "Email ou password incorretos."}

                # Login bem-sucedido — limpar contadores
                c.execute("""
                    UPDATE utilizadores
                    SET tentativas_falhadas = 0, bloqueado_ate = NULL
                    WHERE id = %s
                """, (user_id,))

                # FASE BETA: Não fazer downgrade automático.
                # O plano guardado na BD é a fonte de verdade.
                plano_efetivo = plano

                # Gerar token de sessão
                token = secrets.token_urlsafe(32)
                expira_em = now_utc + timedelta(days=30)
                c.execute("""
                    INSERT INTO sessoes (utilizador_id, token, expira_em) VALUES (%s, %s, %s)
                """, (user_id, token, expira_em))
                c.execute("""
                    UPDATE utilizadores SET ultimo_login=NOW(), token=%s WHERE id=%s
                """, (token, user_id))

                # trial_fim só é mostrado se realmente existir (não vai existir durante a beta)
                trial_fim_str = trial_fim.strftime("%Y-%m-%d") if trial_fim else None
                dias_trial = None
                if trial_fim and plano_efetivo == "pro":
                    dias_trial = max(0, (trial_fim - now_utc).days)

                return {
                    "sucesso": True,
                    "token": token,
                    "utilizador": {
                        "id": user_id,
                        "nome": nome,
                        "clube": clube or "",
                        "plano": plano_efetivo,
                        "trial_fim": trial_fim_str,
                        "dias_trial": dias_trial,
                    }
                }
    except Exception as e:
        return {"sucesso": False, "erro": f"Erro de ligação à base de dados: {e}"}


# ── Verificar sessão ──────────────────────────────────────────────────────────
def verificar_sessao(token: str):
    """
    Verifica se o token de sessão é válido. Retorna dados do utilizador ou None.

    NOTA BETA: Não faz downgrade automático de Pro → Free.
    """
    if not token:
        return None
    try:
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute("""
                    SELECT u.id, u.nome, u.clube, u.plano, u.trial_fim, s.expira_em
                    FROM sessoes s
                    JOIN utilizadores u ON s.utilizador_id = u.id
                    WHERE s.token = %s AND u.ativo = TRUE
                """, (token,))
                row = c.fetchone()
                if not row:
                    return None
                user_id, nome, clube, plano, trial_fim, expira_em = row

                now_utc = datetime.now(timezone.utc)
                if expira_em < now_utc:
                    return None

                # FASE BETA: Não fazer downgrade automático.
                trial_fim_str = trial_fim.strftime("%Y-%m-%d") if trial_fim else None
                dias_trial = None
                if trial_fim and plano == "pro":
                    dias_trial = max(0, (trial_fim - now_utc).days)

                return {
                    "id": user_id,
                    "nome": nome,
                    "clube": clube or "",
                    "plano": plano,
                    "trial_fim": trial_fim_str,
                    "dias_trial": dias_trial,
                }
    except Exception as e:
        print(f"[auth.verificar_sessao] Erro: {e}")
        return None


# ── Logout ────────────────────────────────────────────────────────────────────
def fazer_logout(token: str):
    """Remove o token de sessão."""
    if not token:
        return
    try:
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute("DELETE FROM sessoes WHERE token=%s", (token,))
    except Exception as e:
        print(f"[auth.fazer_logout] Erro: {e}")


# ── Verificar acesso a funcionalidade ─────────────────────────────────────────
def tem_acesso(utilizador: dict, funcionalidade: str) -> bool:
    """Verifica se o utilizador tem acesso a uma funcionalidade."""
    plano = utilizador.get("plano", "free")
    return funcionalidade in PLANOS.get(plano, PLANOS["free"])["funcionalidades"]


# ── Alterar password ──────────────────────────────────────────────────────────
def alterar_password(user_id: int, password_atual: str, nova_password: str) -> dict:
    if len(nova_password) < 8:
        return {"sucesso": False, "erro": "A nova password deve ter pelo menos 8 caracteres."}
    try:
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute("SELECT password_hash FROM utilizadores WHERE id=%s", (user_id,))
                row = c.fetchone()
                if not row or not verificar_password(password_atual, row[0]):
                    return {"sucesso": False, "erro": "Password atual incorreta."}
                novo_hash = hash_password(nova_password)
                c.execute("UPDATE utilizadores SET password_hash=%s WHERE id=%s",
                          (novo_hash, user_id))
                return {"sucesso": True}
    except Exception as e:
        return {"sucesso": False, "erro": f"Erro: {e}"}


# ── Atualizar perfil ──────────────────────────────────────────────────────────
def atualizar_perfil(user_id: int, nome: str = None, clube: str = None) -> dict:
    try:
        with get_conn() as conn:
            with conn.cursor() as c:
                if nome:
                    c.execute("UPDATE utilizadores SET nome=%s WHERE id=%s", (nome, user_id))
                if clube is not None:
                    c.execute("UPDATE utilizadores SET clube=%s WHERE id=%s", (clube, user_id))
                return {"sucesso": True}
    except Exception as e:
        return {"sucesso": False, "erro": f"Erro: {e}"}


# ── Reset de password (geração de token) ──────────────────────────────────────
def gerar_token_reset(email: str) -> dict:
    """
    Gera um token de reset para o email indicado e envia email com link.
    Retorna {"sucesso": True} sempre (mesmo se email não existir, para evitar
    enumeração de emails registados). O email só é enviado se a conta existir.

    RATE LIMITING:
      - Máximo 1 pedido por email por minuto
      - Máximo 5 pedidos por email por hora
    Pedidos acima dos limites devolvem sucesso silenciosamente (não enviam email).
    """
    try:
        with get_conn() as conn:
            with conn.cursor() as c:
                email_clean = email.lower().strip()
                c.execute("SELECT id, nome FROM utilizadores WHERE email=%s AND ativo=TRUE",
                          (email_clean,))
                row = c.fetchone()
                # Por segurança, retornamos sucesso mesmo se email não existir
                # (evita enumeração de emails registados)
                if not row:
                    return {"sucesso": True}

                user_id, nome = row
                now_utc = datetime.now(timezone.utc)

                # ── Rate limit 1: 1 pedido por minuto ─────────────────────────
                c.execute("""
                    SELECT COUNT(*) FROM password_resets
                    WHERE utilizador_id=%s AND criado_em > %s
                """, (user_id, now_utc - timedelta(minutes=1)))
                if c.fetchone()[0] >= 1:
                    print(f"[auth.gerar_token_reset] Rate limit 1min para user {user_id}")
                    return {"sucesso": True}  # silencioso

                # ── Rate limit 2: 5 pedidos por hora ──────────────────────────
                c.execute("""
                    SELECT COUNT(*) FROM password_resets
                    WHERE utilizador_id=%s AND criado_em > %s
                """, (user_id, now_utc - timedelta(hours=1)))
                if c.fetchone()[0] >= 5:
                    print(f"[auth.gerar_token_reset] Rate limit 1h para user {user_id}")
                    return {"sucesso": True}  # silencioso

                # Gerar e guardar token
                token = secrets.token_urlsafe(32)
                expira_em = now_utc + timedelta(hours=1)
                c.execute("""
                    INSERT INTO password_resets (utilizador_id, token, expira_em)
                    VALUES (%s, %s, %s)
                """, (user_id, token, expira_em))

                # Enviar email com link de reset
                try:
                    from utils.email import enviar_email_reset_password
                    enviar_email_reset_password(email_clean, nome, token)
                except Exception as _e:
                    print(f"[auth.gerar_token_reset] Aviso: falhou envio email reset: {_e}")

                return {"sucesso": True}
    except Exception as e:
        return {"sucesso": False, "erro": f"Erro: {e}"}


def aplicar_reset_password(token: str, nova_password: str) -> dict:
    """Valida token e atualiza a password."""
    if len(nova_password) < 8:
        return {"sucesso": False, "erro": "A password deve ter pelo menos 8 caracteres."}
    try:
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute("""
                    SELECT id, utilizador_id, expira_em, usado FROM password_resets
                    WHERE token=%s
                """, (token,))
                row = c.fetchone()
                if not row:
                    return {"sucesso": False, "erro": "Token inválido."}
                rid, user_id, expira_em, usado = row
                if usado:
                    return {"sucesso": False, "erro": "Este link já foi utilizado."}
                if expira_em < datetime.now(timezone.utc):
                    return {"sucesso": False, "erro": "Este link expirou. Pede um novo."}

                novo_hash = hash_password(nova_password)
                c.execute("UPDATE utilizadores SET password_hash=%s WHERE id=%s",
                          (novo_hash, user_id))
                c.execute("UPDATE password_resets SET usado=TRUE WHERE id=%s", (rid,))
                # Remover sessões existentes (forçar re-login)
                c.execute("DELETE FROM sessoes WHERE utilizador_id=%s", (user_id,))
                return {"sucesso": True}
    except Exception as e:
        return {"sucesso": False, "erro": f"Erro: {e}"}


# ── Admin: listar utilizadores ────────────────────────────────────────────────
def listar_utilizadores_admin(admin_email: str, admin_password: str) -> list:
    """Apenas para administração interna."""
    result = fazer_login(admin_email, admin_password)
    if not result["sucesso"]:
        return []
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as c:
                c.execute("""
                    SELECT id, email, nome, clube, plano, ativo, trial_fim,
                           criado_em, ultimo_login
                    FROM utilizadores ORDER BY criado_em DESC
                """)
                return [dict(row) for row in c.fetchall()]
    except Exception as e:
        print(f"[auth.listar_utilizadores_admin] Erro: {e}")
        return []


# ── Inicializar ao importar (lazy — não rebenta se BD off) ────────────────────
# Não chamamos init_db() automaticamente porque pode falhar à boa se a BD ainda
# não estiver acessível. As tabelas devem ser criadas manualmente via SQL Editor
# do Supabase com o ficheiro `migrations/001_initial_schema.sql`.
