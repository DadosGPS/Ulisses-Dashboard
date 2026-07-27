# Supabase — esquema LoadMonitorSystem

Migração Next.js + Supabase + FastAPI (ver `C:\Users\Asus\.claude\plans\wild-churning-aurora.md`).

## Aplicar a migration

**Opção A — Supabase CLI** (recomendado se já a tens instalada):
```
supabase link --project-ref <o-teu-project-ref>
supabase db push
```

**Opção B — SQL Editor no painel Supabase** (mais simples, sem instalar nada):
1. Abre o projeto em https://supabase.com/dashboard
2. `SQL Editor` → `New query`
3. Cola o conteúdo de `migrations/0001_init.sql` → `Run`

## O que a migration cria

- Tabelas: `profiles`, `teams`, `team_members`, `players`, `uploads`, `gps_sessions`, `exercises`.
- RLS ativo em todas — um utilizador só vê dados da(s) equipa(s) a que pertence.
- Trigger `on_auth_user_created`: ao registar um novo utilizador (`auth.users`), cria automaticamente `profiles` + `teams` + `team_members` — equivalente ao que `auth.py`/`registar_utilizador()` fazia na app Streamlit.

## Testar RLS (critério "pronto" da Fase 1)

Não é possível inserir diretamente em `auth.users` por SQL simples — usa o fluxo real de signup:

1. Cria dois utilizadores de teste via `Authentication` → `Add user` no painel Supabase (ou via signup real assim que a Fase 3 estiver feita).
2. Confirma no `Table Editor` que cada um ganhou automaticamente uma linha em `profiles`, `teams` e `team_members` (efeito do trigger).
3. No `SQL Editor`, testa como cada utilizador (usa `Authentication` → gera um JWT de teste, ou testa via a API REST com o `Authorization: Bearer <jwt>` de cada um):
   ```sql
   -- autenticado como utilizador A, inserir uma sessão na equipa de A:
   insert into gps_sessions (team_id, player_id, data, distancia_total_m)
   values ('<team_id_de_A>', '<player_id_qualquer>', '2026-07-01', 5000);

   -- autenticado como utilizador B, tentar ler a sessão de A:
   select * from gps_sessions where team_id = '<team_id_de_A>';
   -- deve devolver 0 linhas (RLS bloqueia)
   ```

## Variáveis de ambiente necessárias

No `api/.env` (FastAPI) e `web/.env.local` (Next.js) — ver `.env.example` em cada pasta.
Nunca colar as chaves `service_role`/`SUPABASE_SERVICE_ROLE_KEY` em código versionado ou no chat — só em `.env` local / secrets do serviço de deploy.
