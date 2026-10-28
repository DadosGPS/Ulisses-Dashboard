-- Força e ginásio.
-- Uma sessão de ginásio da equipa (ou de um grupo) num dia, com a prescrição
-- de exercícios, e o registo do que cada jogador fez (séries × repetições ×
-- carga). A PSE e a duração de cada jogador entram em gps_sessions como uma
-- sessão de tipo 'Ginásio' — assim a carga do ginásio conta na carga interna,
-- no ACWR e na monotonia, ao lado do treino de campo do mesmo dia.
create table if not exists public.forca_sessoes (
  id           uuid primary key default gen_random_uuid(),
  team_id      uuid not null references public.teams(id) on delete cascade,
  data         date not null,
  nome         text not null,
  duracao_min  int check (duracao_min is null or duracao_min between 5 and 240),
  prescricao   jsonb not null default '[]'::jsonb,  -- [{exercicio, series, repeticoes, carga_kg}]
  notas        text,
  criado_por   uuid references auth.users(id) on delete set null,
  criado_em    timestamptz not null default now(),
  atualizado_em timestamptz not null default now()
);
create index if not exists forca_sessoes_team_data on public.forca_sessoes (team_id, data);

create table if not exists public.forca_registos (
  id          uuid primary key default gen_random_uuid(),
  sessao_id   uuid not null references public.forca_sessoes(id) on delete cascade,
  team_id     uuid not null references public.teams(id) on delete cascade,
  player_id   uuid not null references public.players(id) on delete cascade,
  ordem       smallint not null default 0,
  exercicio   text not null,
  series      smallint check (series is null or series between 1 and 20),
  repeticoes  smallint check (repeticoes is null or repeticoes between 1 and 100),
  carga_kg    numeric check (carga_kg is null or carga_kg between 0 and 500),
  feito       boolean not null default true,
  unique (sessao_id, player_id, ordem)
);
create index if not exists forca_registos_player on public.forca_registos (player_id);

alter table public.forca_sessoes enable row level security;
alter table public.forca_registos enable row level security;
