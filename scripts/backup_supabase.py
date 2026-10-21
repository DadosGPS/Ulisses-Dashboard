"""Exporta as tabelas de dados da app (não a auth/perfis) para ficheiros JSON
timestamped — corre diariamente via .github/workflows/backup-db.yml.

Não faz backup de `profiles`/`auth.users`: essas contas podem ser recriadas
via Supabase Auth se necessário. O que é irrecuperável — e por isso o alvo
deste backup — são os dados de GPS/planeamento que só existem aqui.
"""
import json
import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal

import psycopg2
from urllib.parse import urlparse

# Todas as tabelas do esquema public (inclui as que as migrações forem
# acrescentando: lesões, testes, planos, mensagens, academia…). `profiles` fica
# de fora pela razão acima.
EXCLUIR = {"profiles"}


def _json_default(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return str(v)


def _erro(texto: str) -> None:
    """Mensagem de erro que aparece no resumo da execução do GitHub Actions."""
    print(f"::error title=Backup::{texto}")
    print(texto, file=sys.stderr)


def main():
    database_url = (os.environ.get("DATABASE_URL") or "").strip()
    if not database_url:
        _erro("O segredo DATABASE_URL está vazio ou não existe no GitHub (Settings → Secrets and variables → Actions).")
        sys.exit(1)

    destino = sys.argv[1] if len(sys.argv) > 1 else "backup_saida"
    os.makedirs(destino, exist_ok=True)

    # Diagnóstico sem expor a palavra-passe: só o tipo de ligação e o host.
    try:
        partes = urlparse(database_url)
        host, porta, utilizador = partes.hostname or "?", partes.port, partes.username or "?"
    except ValueError:
        _erro("O DATABASE_URL não é um URI válido (deve começar por postgresql://).")
        sys.exit(1)
    print(f"Host: {host} · porta: {porta} · utilizador: {utilizador.split('.')[0]}…")
    if host.startswith("db.") and host.endswith(".supabase.co"):
        _erro("O DATABASE_URL usa a ligação DIRETA (db.<ref>.supabase.co), que só funciona por IPv6 — o GitHub Actions não tem IPv6. "
              "Usa o URI do «Session pooler» (Supabase → Connect → Session pooler: host aws-…pooler.supabase.com, porta 5432).")
        sys.exit(1)

    try:
        conn = psycopg2.connect(database_url, sslmode="require", connect_timeout=15)
    except psycopg2.OperationalError as e:
        msg = str(e).strip().splitlines()[0] if str(e).strip() else repr(e)
        if "password authentication failed" in msg:
            dica = "A palavra-passe da base de dados está errada (repõe-na em Supabase → Database → Settings e atualiza o segredo)."
        elif "Tenant or user not found" in msg:
            dica = "O utilizador do pooler está errado: no Session pooler é postgres.<ref-do-projeto>, não só postgres."
        elif "could not translate host name" in msg or "Name or service not known" in msg:
            dica = "O host não existe — confirma que copiaste o URI completo."
        elif "Network is unreachable" in msg or "timeout" in msg.lower():
            dica = "Sem ligação ao host (provavelmente IPv6/ligação direta). Usa o URI do Session pooler."
        else:
            dica = "Confirma o segredo DATABASE_URL (URI do Session pooler do Supabase)."
        _erro(f"Não foi possível ligar à base de dados: {msg} — {dica}")
        sys.exit(1)
    try:
        cur = conn.cursor()
        cur.execute(
            "select table_name from information_schema.tables "
            "where table_schema = 'public' and table_type = 'BASE TABLE' order by table_name"
        )
        tabelas = [t for (t,) in cur.fetchall() if t not in EXCLUIR]
        resumo = {}
        for tabela in tabelas:
            cur.execute(f'select * from public."{tabela}"')
            colunas = [c.name for c in cur.description]
            linhas = [dict(zip(colunas, linha)) for linha in cur.fetchall()]
            with open(os.path.join(destino, f"{tabela}.json"), "w", encoding="utf-8") as f:
                json.dump(linhas, f, default=_json_default, ensure_ascii=False, indent=None)
            resumo[tabela] = len(linhas)
            print(f"{tabela}: {len(linhas)} linhas")
    finally:
        conn.close()

    with open(os.path.join(destino, "_resumo.json"), "w", encoding="utf-8") as f:
        json.dump({"gerado_em": datetime.now(timezone.utc).isoformat(), "tabelas": resumo}, f, indent=2)


if __name__ == "__main__":
    main()
