-- Planos de regresso ao jogo (return-to-play). Um plano por episódio de
-- recuperação: etapas com metas em % da referência de jogo PRÉ-LESÃO do
-- jogador (HSR, sprint, distância, velocidade máxima); a API avalia o progresso
-- automaticamente a partir das sessões GPS registadas desde data_inicio.
--
-- Formato de `etapas` (lista ordenada):
--   [{"nome": "Etapa 1", "pct_distancia": 60, "pct_hsr": 40, "pct_sprint": 20,
--     "pct_vmax": null, "notas": "..."}, ...]
create table public.planos_rtp (
  id                uuid primary key default gen_random_uuid(),
  team_id           uuid not null references public.teams(id) on delete cascade,
  player_id         uuid not null references public.players(id) on delete cascade,
  lesao_id          uuid references public.lesoes(id) on delete set null,
  data_inicio       date not null,
  etapas            jsonb not null default '[]'::jsonb,
  sessoes_por_etapa integer not null default 2 check (sessoes_por_etapa between 1 and 10),
  estado            text not null default 'ativo' check (estado in ('ativo', 'concluido', 'cancelado')),
  notas             text,
  criado_em         timestamptz not null default now(),
  atualizado_em     timestamptz not null default now()
);
create index on public.planos_rtp (team_id, estado);
create index on public.planos_rtp (player_id, data_inicio);
