"""
LoadMonitor — Módulo de Autenticação e Base de Dados Multi-Utilizador
Usa SQLite local (gratuito) ou pode ser migrado para PostgreSQL no futuro
"""

import sqlite3
import hashlib
import secrets
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# ── Configuração ──────────────────────────────────────────────────────────────
DB_PATH = Path("loadmonitor.db")

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
        "max_equipas": -1,   # ilimitado
        "max_atletas": -1,   # ilimitado
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
    """Cria as tabelas se não existirem."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Utilizadores
    c.execute("""
        CREATE TABLE IF NOT EXISTS utilizadores (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            email        TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nome         TEXT NOT NULL,
            clube        TEXT,
            plano        TEXT DEFAULT 'free',
            ativo        INTEGER DEFAULT 1,
            trial_fim    TEXT,
            criado_em    TEXT DEFAULT (datetime('now')),
            ultimo_login TEXT,
            token        TEXT
        )
    """)

    # Sessões de login
    c.execute("""
        CREATE TABLE IF NOT EXISTS sessoes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            utilizador_id INTEGER NOT NULL,
            token        TEXT NOT NULL,
            criado_em    TEXT DEFAULT (datetime('now')),
            expira_em    TEXT NOT NULL,
            FOREIGN KEY (utilizador_id) REFERENCES utilizadores(id)
        )
    """)

    # Equipas por utilizador
    c.execute("""
        CREATE TABLE IF NOT EXISTS equipas (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            utilizador_id  INTEGER NOT NULL,
            nome           TEXT NOT NULL,
            desporto       TEXT DEFAULT 'Futebol',
            criado_em      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (utilizador_id) REFERENCES utilizadores(id)
        )
    """)

    # Log de acessos (analytics simples)
    c.execute("""
        CREATE TABLE IF NOT EXISTS log_acessos (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            utilizador_id INTEGER,
            pagina        TEXT,
            timestamp     TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()


# ── Funções de password ───────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    """Hash seguro com salt usando SHA-256."""
    salt = secrets.token_hex(32)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 260000
    ).hex()
    return f"{salt}:{pwd_hash}"


def verificar_password(password: str, stored_hash: str) -> bool:
    """Verifica password contra hash armazenado."""
    try:
        salt, pwd_hash = stored_hash.split(":", 1)
        new_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), 260000
        ).hex()
        return secrets.compare_digest(new_hash, pwd_hash)
    except Exception:
        return False


# ── Registo de utilizadores ───────────────────────────────────────────────────
def registar_utilizador(email: str, password: str, nome: str, clube: str = "") -> dict:
    """
    Regista um novo utilizador.
    Retorna {"sucesso": True, "id": ...} ou {"sucesso": False, "erro": ...}
    """
    if len(password) < 8:
        return {"sucesso": False, "erro": "A password deve ter pelo menos 8 caracteres."}
    if "@" not in email or "." not in email:
        return {"sucesso": False, "erro": "Email inválido."}
    if not nome.strip():
        return {"sucesso": False, "erro": "O nome é obrigatório."}

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        pwd_hash = hash_password(password)
        # Trial de 14 dias gratuito no plano Pro
        trial_fim = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
        c.execute("""
            INSERT INTO utilizadores (email, password_hash, nome, clube, plano, trial_fim)
            VALUES (?, ?, ?, ?, 'pro', ?)
        """, (email.lower().strip(), pwd_hash, nome.strip(), clube.strip(), trial_fim))
        user_id = c.lastrowid
        # Criar equipa padrão
        c.execute("""
            INSERT INTO equipas (utilizador_id, nome) VALUES (?, ?)
        """, (user_id, clube.strip() or "A Minha Equipa"))
        conn.commit()
        return {"sucesso": True, "id": user_id, "trial_fim": trial_fim}
    except sqlite3.IntegrityError:
        return {"sucesso": False, "erro": "Este email já está registado."}
    finally:
        conn.close()


# ── Login ─────────────────────────────────────────────────────────────────────
def fazer_login(email: str, password: str) -> dict:
    """
    Autentica utilizador.
    Retorna {"sucesso": True, "token": ..., "utilizador": {...}} ou erro.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("""
            SELECT id, password_hash, nome, clube, plano, ativo, trial_fim
            FROM utilizadores WHERE email = ?
        """, (email.lower().strip(),))
        row = c.fetchone()

        if not row:
            return {"sucesso": False, "erro": "Email ou password incorretos."}

        user_id, pwd_hash, nome, clube, plano, ativo, trial_fim = row

        if not ativo:
            return {"sucesso": False, "erro": "Conta desativada. Contacta o suporte."}

        if not verificar_password(password, pwd_hash):
            return {"sucesso": False, "erro": "Email ou password incorretos."}

        # Verificar se trial expirou
        plano_efetivo = plano
        if plano == "pro" and trial_fim:
            if datetime.strptime(trial_fim, "%Y-%m-%d") < datetime.now():
                plano_efetivo = "free"
                c.execute("UPDATE utilizadores SET plano='free' WHERE id=?", (user_id,))

        # Gerar token de sessão
        token = secrets.token_urlsafe(32)
        expira_em = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""
            INSERT INTO sessoes (utilizador_id, token, expira_em) VALUES (?, ?, ?)
        """, (user_id, token, expira_em))
        c.execute("""
            UPDATE utilizadores SET ultimo_login=datetime('now'), token=? WHERE id=?
        """, (token, user_id))
        conn.commit()

        dias_trial = None
        if trial_fim and plano == "pro":
            dias_trial = (datetime.strptime(trial_fim, "%Y-%m-%d") - datetime.now()).days

        return {
            "sucesso": True,
            "token": token,
            "utilizador": {
                "id": user_id,
                "nome": nome,
                "clube": clube or "",
                "plano": plano_efetivo,
                "trial_fim": trial_fim,
                "dias_trial": max(0, dias_trial) if dias_trial is not None else None,
            }
        }
    finally:
        conn.close()


# ── Verificar sessão ─────────────────────────────────────────────────────────
def verificar_sessao(token: str) -> dict | None:
    """Verifica se o token de sessão é válido. Retorna dados do utilizador ou None."""
    if not token:
        return None
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("""
            SELECT u.id, u.nome, u.clube, u.plano, u.trial_fim, s.expira_em
            FROM sessoes s
            JOIN utilizadores u ON s.utilizador_id = u.id
            WHERE s.token = ? AND u.ativo = 1
        """, (token,))
        row = c.fetchone()
        if not row:
            return None
        user_id, nome, clube, plano, trial_fim, expira_em = row
        if datetime.strptime(expira_em, "%Y-%m-%d %H:%M:%S") < datetime.now():
            return None

        dias_trial = None
        if trial_fim and plano == "pro":
            dias_trial = (datetime.strptime(trial_fim, "%Y-%m-%d") - datetime.now()).days
            if dias_trial < 0:
                plano = "free"

        return {
            "id": user_id,
            "nome": nome,
            "clube": clube or "",
            "plano": plano,
            "trial_fim": trial_fim,
            "dias_trial": max(0, dias_trial) if dias_trial is not None else None,
        }
    finally:
        conn.close()


# ── Logout ────────────────────────────────────────────────────────────────────
def fazer_logout(token: str):
    """Remove o token de sessão."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM sessoes WHERE token=?", (token,))
    conn.commit()
    conn.close()


# ── Verificar acesso a funcionalidade ────────────────────────────────────────
def tem_acesso(utilizador: dict, funcionalidade: str) -> bool:
    """Verifica se o utilizador tem acesso a uma funcionalidade."""
    plano = utilizador.get("plano", "free")
    return funcionalidade in PLANOS.get(plano, PLANOS["free"])["funcionalidades"]


# ── Alterar password ──────────────────────────────────────────────────────────
def alterar_password(user_id: int, password_atual: str, nova_password: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("SELECT password_hash FROM utilizadores WHERE id=?", (user_id,))
        row = c.fetchone()
        if not row or not verificar_password(password_atual, row[0]):
            return {"sucesso": False, "erro": "Password atual incorreta."}
        if len(nova_password) < 8:
            return {"sucesso": False, "erro": "A nova password deve ter pelo menos 8 caracteres."}
        novo_hash = hash_password(nova_password)
        c.execute("UPDATE utilizadores SET password_hash=? WHERE id=?", (novo_hash, user_id))
        conn.commit()
        return {"sucesso": True}
    finally:
        conn.close()


# ── Atualizar perfil ─────────────────────────────────────────────────────────
def atualizar_perfil(user_id: int, nome: str = None, clube: str = None) -> dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        if nome:
            c.execute("UPDATE utilizadores SET nome=? WHERE id=?", (nome, user_id))
        if clube is not None:
            c.execute("UPDATE utilizadores SET clube=? WHERE id=?", (clube, user_id))
        conn.commit()
        return {"sucesso": True}
    finally:
        conn.close()


# ── Admin: listar utilizadores ────────────────────────────────────────────────
def listar_utilizadores_admin(admin_email: str, admin_password: str) -> list:
    """Apenas para administração interna."""
    result = fazer_login(admin_email, admin_password)
    if not result["sucesso"]:
        return []
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("""
            SELECT id, email, nome, clube, plano, ativo, trial_fim,
                   criado_em, ultimo_login
            FROM utilizadores ORDER BY criado_em DESC
        """)
        cols = ["id","email","nome","clube","plano","ativo","trial_fim",
                "criado_em","ultimo_login"]
        return [dict(zip(cols, row)) for row in c.fetchall()]
    finally:
        conn.close()


# ── Inicializar ao importar ───────────────────────────────────────────────────
init_db()
