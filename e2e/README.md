# Testes das páginas (e2e)

Abrem as páginas principais da app num browser a sério e falham se alguma:
voltar ao login, der um erro de JavaScript, receber 401/403/5xx da API ou
mostrar um erro no ecrã. Também testam a versão em inglês e o registo de um
jogador na Academia. Correm sozinhos no GitHub (job «Web · testes das páginas»
em `.github/workflows/ci.yml`) em cada alteração.

Peças:

- `supabase_stub.sql` — o mínimo do Supabase (esquema `auth`, papéis) para as
  migrações correrem num Postgres normal.
- `semear.py` — dados fictícios: academia, Sub-15 e Sub-16, sessões GPS,
  microciclos, testes e jogos (datas relativas a hoje).
- `auth_falso.py` — imita o Supabase Auth: gera um token válido
  (`sessao.json`), serve a chave pública à API e o utilizador à web.
- `web/e2e/paginas.spec.ts` — os testes (Playwright).

Correr no computador (com Postgres, Python e Node):

```bash
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/e2e
psql "$DATABASE_URL" -f e2e/supabase_stub.sql
python scripts/aplicar_migracoes.py && python e2e/semear.py
python e2e/auth_falso.py 54321 &
(cd api && SUPABASE_URL=http://127.0.0.1:54321 CORS_ORIGINS=http://localhost:3000 uvicorn main:app --port 8000 &)
cd web
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321 NEXT_PUBLIC_SUPABASE_ANON_KEY=e2e \
  NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 npx next dev -p 3000 &
npx playwright test
```

Ao acrescentar uma página nova ao menu, acrescenta-a também à lista `PAGINAS`
em `web/e2e/paginas.spec.ts`.
