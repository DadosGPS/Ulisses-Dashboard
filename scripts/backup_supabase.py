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

TABELAS = ["teams", "team_members", "players", "gps_sessions", "exercises", "uploads"]


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

    conn = psycopg2.connect(database_url, sslmode="require", connect_timeout=15)
    try:
        cur = conn.cursor()
        resumo = {}
        for tabela in TABELAS:
            cur.execute(f"select * from {tabela}")
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
