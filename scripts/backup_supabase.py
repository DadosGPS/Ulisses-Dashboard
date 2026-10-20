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


def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL não definido.", file=sys.stderr)
        sys.exit(1)

    destino = sys.argv[1] if len(sys.argv) > 1 else "backup_saida"
    os.makedirs(destino, exist_ok=True)

    # No GitHub Actions usar a ligação «Session pooler» do Supabase (IPv4): a
    # ligação direta (db.<ref>.supabase.co) só funciona por IPv6.
    try:
        conn = psycopg2.connect(database_url, sslmode="require", connect_timeout=15)
    except psycopg2.OperationalError as e:
        print(f"Não foi possível ligar à base de dados: {e}", file=sys.stderr)
        print("Confirma o segredo DATABASE_URL (usa o URI do Session pooler do Supabase).", file=sys.stderr)
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
