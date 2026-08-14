-- PSE esperada por dia de microciclo — permite ao preparador físico planear
-- a intensidade de cada dia ANTES do treino acontecer, e depois comparar
-- com a PSE média real (já registada via upload) no mesmo gráfico.
create table public.pse_planeado (
  id uuid primary key default gen_random_uuid(),
  team_id uuid not null references public.teams(id) on delete cascade,
  microciclo_nr int not null,
  dia_md text not null,
  pse_esperada numeric not null,
  criado_em timestamptz not null default now(),
  atualizado_em timestamptz not null default now(),
  unique (team_id, microciclo_nr, dia_md)
);
create index on public.pse_planeado (team_id, microciclo_nr);
