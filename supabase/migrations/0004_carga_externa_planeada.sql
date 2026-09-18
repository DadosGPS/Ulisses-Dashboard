-- Carga externa planeada por dia de microciclo — permite ao preparador físico
-- planear distância / HSR / sprint de cada dia ANTES do treino, e depois
-- comparar com a média real registada (via upload) no mesmo gráfico.
-- Mesma lógica da tabela pse_planeado (0003), agora para a carga externa.
create table public.carga_externa_planeada (
  id uuid primary key default gen_random_uuid(),
  team_id uuid not null references public.teams(id) on delete cascade,
  microciclo_nr int not null,
  dia_md text not null,
  distancia_m numeric,
  hsr_m numeric,
  sprint_m numeric,
  criado_em timestamptz not null default now(),
  atualizado_em timestamptz not null default now(),
  unique (team_id, microciclo_nr, dia_md)
);
create index on public.carga_externa_planeada (team_id, microciclo_nr);
