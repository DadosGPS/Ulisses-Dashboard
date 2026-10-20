-- ═══════════════════════════════════════════════════════════════════════════
-- 0012 — Microciclos planeados (linha temporal da época)
-- ═══════════════════════════════════════════════════════════════════════════
-- Cada microciclo da equipa com datas, tipo, perfil, fase e o FATOR SEMANAL
-- por variável: alvo da semana de treino em múltiplos da referência de jogo
-- (ex.: HSR 2,5 = 250 % de um jogo). `dias` guarda o plano dia a dia
-- {"2026-10-05": {"dia_md": "MD-5", "tipo": "Treino", "objetivo": "…"}}; os
-- valores planeados de cada sessão continuam em pse_planeado e
-- carga_externa_planeada (por número de microciclo + dia MD), como antes.
create table if not exists public.microciclos (
  id           uuid primary key default gen_random_uuid(),
  team_id      uuid not null references public.teams(id) on delete cascade,
  numero       int not null,
  nome         text,
  tipo         text not null default 'Normal',
  perfil       text,
  fase         text,
  data_inicio  date not null,
  data_fim     date not null check (data_fim >= data_inicio),
  fatores      jsonb not null default '{}'::jsonb,
  dias         jsonb not null default '{}'::jsonb,
  notas        text,
  criado_em    timestamptz not null default now(),
  atualizado_em timestamptz not null default now(),
  unique (team_id, numero)
);
create index if not exists microciclos_team_inicio on public.microciclos (team_id, data_inicio);

alter table public.microciclos enable row level security;

-- Duração planeada da sessão (para a carga interna planeada = PSE × minutos).
alter table public.pse_planeado add column if not exists duracao_min numeric;
