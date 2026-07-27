-- LoadMonitorSystem — Supabase schema (migração Next.js + Supabase + FastAPI)
-- Fase 1 do plano de migração (ver C:\Users\Asus\.claude\plans\wild-churning-aurora.md)
--
-- Como aplicar:
--   supabase db push          (via Supabase CLI, ligado ao projeto)
--   ou colar este ficheiro no SQL Editor do painel Supabase e correr.

-- ── Extensões ──────────────────────────────────────────────────────────────
create extension if not exists "pgcrypto";

-- ── profiles ──────────────────────────────────────────────────────────────
-- 1:1 com auth.users. Substitui a tabela `utilizadores` da app Streamlit.
create table public.profiles (
  id                      uuid primary key references auth.users(id) on delete cascade,
  nome                    text not null,
  clube                   text,
  plano                   text not null default 'pro',   -- todos 'pro' durante a beta, como na app atual
  ativo                   boolean not null default true,
  is_admin                boolean not null default false,
  stripe_customer_id      text,
  stripe_subscription_id  text,
  settings                jsonb not null default '{}',   -- substitui a tabela `preferencias`
  criado_em               timestamptz not null default now(),
  ultimo_login            timestamptz
);

comment on table public.profiles is 'Perfil de utilizador, 1:1 com auth.users. Substitui utilizadores.';

-- ── teams ─────────────────────────────────────────────────────────────────
create table public.teams (
  id          uuid primary key default gen_random_uuid(),
  nome        text not null,
  desporto    text not null default 'Futebol',
  criado_por  uuid not null references public.profiles(id),
  criado_em   timestamptz not null default now()
);

-- ── team_members ──────────────────────────────────────────────────────────
-- Hoje é sempre 1 owner : 1 team (criado automaticamente no registo), mas a
-- tabela de junção existe já para não obrigar a uma migração dolorosa se um
-- dia houver multi-coach por equipa.
create table public.team_members (
  team_id  uuid not null references public.teams(id) on delete cascade,
  user_id  uuid not null references public.profiles(id) on delete cascade,
  role     text not null default 'owner',
  primary key (team_id, user_id)
);

-- ── players ───────────────────────────────────────────────────────────────
-- NOVO — na app Streamlit "Jogador" era só uma coluna de texto livre por
-- ficheiro Excel, nunca uma entidade persistida. Agora que os dados ficam
-- guardados, um jogador precisa de identidade estável entre uploads.
create table public.players (
  id          uuid primary key default gen_random_uuid(),
  team_id     uuid not null references public.teams(id) on delete cascade,
  nome        text not null,
  posicao     text,
  ativo       boolean not null default true,
  criado_em   timestamptz not null default now(),
  unique (team_id, nome)
);

-- ── uploads ───────────────────────────────────────────────────────────────
-- NOVO — trilho de auditoria dos ficheiros carregados. Não existia porque os
-- dados nunca eram persistidos (eram descartados no fim da sessão Streamlit).
create table public.uploads (
  id             uuid primary key default gen_random_uuid(),
  team_id        uuid not null references public.teams(id) on delete cascade,
  uploaded_by    uuid not null references public.profiles(id),
  filename       text,
  storage_path   text,
  status         text not null default 'processing',  -- processing | done | error
  row_count      int,
  error          text,
  criado_em      timestamptz not null default now()
);

-- ── gps_sessions ──────────────────────────────────────────────────────────
-- Tabela principal: 1 linha = 1 jogador + 1 sessão/dia.
-- Colunas fixas espelham o modelo canónico de utils/dados.py (COL_ALIASES).
-- `extra_metrics` preserva a deteção dinâmica de métricas não-canónicas que
-- get_mets_gps() já suporta na app atual, sem obrigar a migração de schema
-- sempre que aparece uma métrica nova de um fornecedor GPS diferente.
create table public.gps_sessions (
  id                    uuid primary key default gen_random_uuid(),
  team_id               uuid not null references public.teams(id) on delete cascade,
  player_id             uuid not null references public.players(id) on delete cascade,
  upload_id             uuid references public.uploads(id) on delete set null,

  data                  date not null,
  tipo                  text,          -- 'Treino' | 'Jogo'
  dia_md                text,          -- ex: 'MD-1', 'MD+1'
  microciclo_nr         int,

  distancia_total_m     numeric,
  hsr_m                 numeric,
  sprint_m              numeric,
  acc_n                 numeric,
  dcc_n                 numeric,
  vel_max_kmh           numeric,
  pse_sessao            numeric,
  duracao_min           numeric,
  carga_interna         numeric,       -- = PSE × Duração se ausente na origem (mesma regra de utils/dados.py)
  hooper_index          numeric,       -- derivado dos sub-scores de wellness se ausente
  sono                  numeric,
  dor_musc              numeric,
  stress                numeric,
  humor                 numeric,

  extra_metrics         jsonb not null default '{}',
  criado_em             timestamptz not null default now(),

  unique (team_id, player_id, data, tipo)
);

create index idx_gps_sessions_team_data   on public.gps_sessions (team_id, data);
create index idx_gps_sessions_player_data on public.gps_sessions (player_id, data);

-- ── exercises ─────────────────────────────────────────────────────────────
-- Entidade separada: 1 linha = 1 exercício/drill dentro de uma sessão
-- (granularidade diferente de gps_sessions — não é por jogador).
create table public.exercises (
  id                  uuid primary key default gen_random_uuid(),
  team_id             uuid not null references public.teams(id) on delete cascade,
  upload_id           uuid references public.uploads(id) on delete set null,

  data                date,
  microciclo_nr       int,
  dia_md              text,
  exercicio           text,
  categoria           text,
  duracao_min         numeric,
  n_jogadores         int,
  pse_exercicio       numeric,        -- distinto de gps_sessions.pse_sessao

  distancia_total_m   numeric,
  hsr_m               numeric,
  sprint_m            numeric,
  acc_n               numeric,
  dcc_n               numeric,
  vel_max_kmh         numeric,

  extra_metrics       jsonb not null default '{}',
  criado_em           timestamptz not null default now()
);

create index idx_exercises_team_data on public.exercises (team_id, data);

-- ── RLS ───────────────────────────────────────────────────────────────────
alter table public.profiles     enable row level security;
alter table public.teams        enable row level security;
alter table public.team_members enable row level security;
alter table public.players      enable row level security;
alter table public.uploads      enable row level security;
alter table public.gps_sessions enable row level security;
alter table public.exercises    enable row level security;

-- profiles: cada utilizador só vê/edita o seu próprio perfil.
create policy "profiles_select_own" on public.profiles
  for select using (id = auth.uid());
create policy "profiles_update_own" on public.profiles
  for update using (id = auth.uid());

-- team_members: um utilizador vê as suas próprias linhas de pertença.
create policy "team_members_select_own" on public.team_members
  for select using (user_id = auth.uid());

-- teams: visível para quem pertence à equipa.
create policy "teams_select_member" on public.teams
  for select using (
    id in (select team_id from public.team_members where user_id = auth.uid())
  );

-- players / uploads / gps_sessions / exercises: mesma regra — visível para
-- membros da equipa dona da linha. Escrita directa do Next.js segue a mesma
-- regra (INSERT/UPDATE/DELETE); a ingestão em massa via FastAPI usa a
-- service-role key e portanto ignora RLS — nesse caso é o FastAPI que tem de
-- validar o JWT do utilizador e a pertença à equipa antes de escrever.
create policy "players_all_member" on public.players
  for all using (
    team_id in (select team_id from public.team_members where user_id = auth.uid())
  );

create policy "uploads_all_member" on public.uploads
  for all using (
    team_id in (select team_id from public.team_members where user_id = auth.uid())
  );

create policy "gps_sessions_all_member" on public.gps_sessions
  for all using (
    team_id in (select team_id from public.team_members where user_id = auth.uid())
  );

create policy "exercises_all_member" on public.exercises
  for all using (
    team_id in (select team_id from public.team_members where user_id = auth.uid())
  );

-- ── Trigger: criar profile + team + team_member ao registar utilizador ────
-- Substitui a lógica de registar_utilizador() do auth.py (que criava uma
-- linha em `equipas` a par do utilizador). Corre em qualquer via de signup
-- (email/password hoje, OAuth/magic-link no futuro), não só no formulário.
create function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  novo_team_id uuid;
begin
  insert into public.profiles (id, nome, clube)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'nome', split_part(new.email, '@', 1)),
    new.raw_user_meta_data->>'clube'
  );

  insert into public.teams (nome, desporto, criado_por)
  values (
    coalesce(nullif(new.raw_user_meta_data->>'clube', ''), 'A Minha Equipa'),
    'Futebol',
    new.id
  )
  returning id into novo_team_id;

  insert into public.team_members (team_id, user_id, role)
  values (novo_team_id, new.id, 'owner');

  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
