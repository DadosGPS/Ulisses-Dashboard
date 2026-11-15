-- ═══════════════════════════════════════════════════════════════════════════
-- 0026 — Períodos das sessões (partes do jogo, exercícios por jogador) e
--        registo das verificações de dados de cada importação
-- ═══════════════════════════════════════════════════════════════════════════
-- Até aqui, um ficheiro com várias linhas por jogador no mesmo dia (1.ª e 2.ª
-- parte, ou um bloco por exercício) era somado numa só sessão e o detalhe
-- perdia-se. gps_sessions continua a ter o total do dia; gps_periodos guarda
-- cada parte/exercício tal como veio no ficheiro (coluna «Período»).
create table if not exists public.gps_periodos (
  id                 uuid primary key default gen_random_uuid(),
  team_id            uuid not null references public.teams(id) on delete cascade,
  player_id          uuid not null references public.players(id) on delete cascade,
  upload_id          uuid references public.uploads(id) on delete set null,
  data               date not null,
  tipo               text,
  periodo            text not null,                 -- nome no ficheiro (ex.: «Rondo 5v2», «1.ª parte»)
  categoria          text not null default 'exercicio' check (categoria in ('parte', 'exercicio')),
  ordem              int not null default 0,        -- ordem em que aparece na sessão
  duracao_min        numeric,
  distancia_total_m  numeric,
  hsr_m              numeric,
  sprint_m           numeric,
  acc_n              numeric,
  dcc_n              numeric,
  vel_max_kmh        numeric,
  extra_metrics      jsonb not null default '{}',
  criado_em          timestamptz not null default now()
);
create index if not exists gps_periodos_team_data on public.gps_periodos (team_id, data);
create index if not exists gps_periodos_player_data on public.gps_periodos (player_id, data);
create index if not exists gps_periodos_nome on public.gps_periodos (team_id, lower(periodo));
alter table public.gps_periodos enable row level security;

-- Resultado da verificação de cada importação (e das verificações pedidas à
-- mão sobre os dados já guardados). Erros bloqueiam a importação; avisos e
-- informações ficam registados para se corrigir a origem.
create table if not exists public.verificacoes_dados (
  id           uuid primary key default gen_random_uuid(),
  team_id      uuid not null references public.teams(id) on delete cascade,
  upload_id    uuid references public.uploads(id) on delete set null,
  ficheiro     text,
  origem       text not null default 'importacao' check (origem in ('importacao', 'equipa')),
  bloqueou     boolean not null default false,
  resumo       jsonb not null default '{}',
  problemas    jsonb not null default '[]',
  criado_por   uuid references auth.users(id) on delete set null,
  criado_em    timestamptz not null default now()
);
create index if not exists verificacoes_dados_team on public.verificacoes_dados (team_id, criado_em desc);
alter table public.verificacoes_dados enable row level security;
