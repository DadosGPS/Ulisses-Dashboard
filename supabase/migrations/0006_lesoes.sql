-- Histórico de lesões — base do body map e do calendário de disponibilidade.
-- Uma linha por episódio de lesão; data_fim a null = lesão ainda em curso.
create table public.lesoes (
  id          uuid primary key default gen_random_uuid(),
  team_id     uuid not null references public.teams(id) on delete cascade,
  player_id   uuid not null references public.players(id) on delete cascade,
  zona        text not null,                 -- chave da zona do corpo (ver frontend)
  lado        text,                          -- 'esquerdo' | 'direito' | 'central' | null
  tipo        text,                          -- muscular | articular | ligamentar | ossea | tendao | outro
  gravidade   text,                          -- leve | moderada | grave
  data_inicio date not null,
  data_fim    date,                          -- null = ainda lesionado
  notas       text,
  criado_em   timestamptz not null default now(),
  atualizado_em timestamptz not null default now()
);
create index on public.lesoes (team_id);
create index on public.lesoes (player_id, data_inicio);
