"""Aplica as migrações de supabase/migrations/ que ainda faltam na base de dados.

- Regista cada migração aplicada em public._migracoes (nome, quando, como).
- Cada ficheiro corre numa transação: ou entra todo, ou nada.
- Migrações aplicadas antes à mão (sem registo) são reconhecidas: se o ficheiro
  falhar por «já existe», fica registado como «já existia» e segue-se.
- Pára na primeira falha a sério e diz qual o ficheiro e o erro.

Uso: python scripts/aplicar_migracoes.py [--simular]
Corre sozinho no GitHub Actions (.github/workflows/migracoes.yml) a cada
alteração em supabase/migrations/.
"""
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import psycopg2

PASTA = Path(__file__).resolve().parent.parent / "supabase" / "migrations"
# duplicate_table, duplicate_object, duplicate_function, duplicate_schema, duplicate_column
JA_EXISTE = {"42P07", "42710", "42723", "42P06", "42701"}


def _erro(texto: str) -> None:
    print(f"::error title=Migrações::{texto}")
    print(texto, file=sys.stderr)


def ligar():
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if not url:
        _erro("O segredo DATABASE_URL está vazio ou não existe no GitHub (Settings → Secrets and variables → Actions).")
        sys.exit(1)
    host = urlparse(url).hostname or ""
    if host.startswith("db.") and host.endswith(".supabase.co"):
        _erro("O DATABASE_URL usa a ligação direta (só IPv6). Usa o URI do «Session pooler» do Supabase.")
        sys.exit(1)
    kwargs = {} if host in ("", "localhost", "127.0.0.1") or host.startswith("/") else {"sslmode": "require"}
    try:
        return psycopg2.connect(url, connect_timeout=15, **kwargs)
    except psycopg2.OperationalError as e:
        _erro(f"Não foi possível ligar à base de dados: {str(e).strip().splitlines()[0]}")
        sys.exit(1)


def main() -> None:
    simular = "--simular" in sys.argv
    conn = ligar()
    conn.autocommit = False
    with conn.cursor() as cur:
        cur.execute(
            """
            create table if not exists public._migracoes (
              nome text primary key,
              aplicada_em timestamptz not null default now(),
              modo text not null
            );
            alter table public._migracoes enable row level security;
            """
        )
        cur.execute("select nome from public._migracoes")
        feitas = {r[0] for r in cur.fetchall()}
    conn.commit()

    ficheiros = sorted(PASTA.glob("*.sql"))
    pendentes = [f for f in ficheiros if f.name not in feitas]
    print(f"{len(ficheiros)} migrações no repositório · {len(feitas)} registadas · {len(pendentes)} por aplicar")
    if simular:
        for f in pendentes:
            print(f"  por aplicar: {f.name}")
        return

    for f in pendentes:
        sql = f.read_text(encoding="utf-8")
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                cur.execute("insert into public._migracoes (nome, modo) values (%s, 'aplicada')", (f.name,))
            conn.commit()
            print(f"✓ {f.name} aplicada")
        except psycopg2.Error as e:
            conn.rollback()
            if e.pgcode in JA_EXISTE:
                with conn.cursor() as cur:
                    cur.execute("insert into public._migracoes (nome, modo) values (%s, 'já existia')", (f.name,))
                conn.commit()
                print(f"= {f.name} já estava aplicada ({(e.pgerror or '').strip().splitlines()[0] if e.pgerror else e.pgcode})")
                continue
            detalhe = (e.pgerror or str(e)).strip().splitlines()[0]
            _erro(f"A migração {f.name} falhou e não foi aplicada (nada ficou a meio): {detalhe}")
            sys.exit(1)
    print("Base de dados em dia.")


if __name__ == "__main__":
    main()
