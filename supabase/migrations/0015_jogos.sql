-- ═══════════════════════════════════════════════════════════════════════════
-- 0015 — Jogos da equipa: minutos, contexto, golos e assistências
-- ═══════════════════════════════════════════════════════════════════════════
-- Um jogo pertence a uma equipa (escalão × época). Cada atleta convocado tem
-- uma linha de participação (minutos, titular, posição, golos, assistências) —
-- ligada à FICHA do atleta, por isso um sub-15 que joga pelos sub-16 conta
-- também no seu resumo da época.
create table if not exists public.jogos (
  id               uuid primary key default gen_random_uuid(),
  academia_id      uuid not null references public.academias(id) on delete cascade,
  team_id          uuid not null references public.teams(id) on delete cascade,
  data             date not null,
  competicao       text not null default 'Campeonato'
                   check (competicao in ('Campeonato', 'Taça', 'Torneio', 'Amigável')),
  adversario       text not null,
  numero           int,
  duracao_min      int not null default 80 check (duracao_min between 10 and 150),
  golos_marcados   int check (golos_marcados >= 0),
  golos_sofridos   int check (golos_sofridos >= 0),
  notas            text,
  criado_por       uuid references auth.users(id) on delete set null,
  criado_em        timestamptz not null default now(),
  unique (team_id, data, adversario)
);
create index if not exists jogos_team_data on public.jogos (team_id, data);

create table if not exists public.jogo_participacoes (
  jogo_id       uuid not null references public.jogos(id) on delete cascade,
  atleta_id     uuid not null references public.atletas(id) on delete cascade,
  posicao       text,
  minutos       int not null default 0 check (minutos between 0 and 150),
  titular       boolean not null default false,
  golos         int not null default 0 check (golos >= 0),
  assistencias  int not null default 0 check (assistencias >= 0),
  primary key (jogo_id, atleta_id)
);
create index if not exists jogo_participacoes_atleta on public.jogo_participacoes (atleta_id);

alter table public.jogos              enable row level security;
alter table public.jogo_participacoes enable row level security;
