-- Registo de decisões do staff face aos sinais da app.
-- Cada linha = o que o preparador físico decidiu fazer com um sinal de um
-- jogador num dia (reduzir carga, ajustar o plano, manter, ignorar). Serve
-- para duas coisas: memória do que foi feito, e verificar mais tarde se os
-- alertas acertam (o que aconteceu ao jogador nos dias seguintes).
create table if not exists public.decisoes (
  id          uuid primary key default gen_random_uuid(),
  team_id     uuid not null references public.teams(id) on delete cascade,
  player_id   uuid references public.players(id) on delete set null,
  jogador     text not null,                  -- nome no momento da decisão
  data        date not null,                  -- dia a que a decisão se refere
  sinal       text not null,                  -- chave do sinal (acwr, hsr_baixo, hooper…)
  detalhe     jsonb not null default '{}'::jsonb, -- o sinal tal como foi mostrado
  decisao     text not null check (decisao in ('reduzir', 'ajustar', 'manter', 'ignorar')),
  nota        text,
  criado_por  uuid references auth.users(id) on delete set null,
  criado_em   timestamptz not null default now(),
  unique (team_id, jogador, data, sinal)
);
create index if not exists decisoes_team_data on public.decisoes (team_id, data);
alter table public.decisoes enable row level security;
