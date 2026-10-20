-- ═══════════════════════════════════════════════════════════════════════════
-- 0013 — Calendário: eventos livres de cada dia
-- ═══════════════════════════════════════════════════════════════════════════
-- O calendário junta o que já existe (plano dos microciclos, sessões GPS, PSE
-- e bem-estar). Esta tabela guarda o resto do que se fez num dia e que não
-- vem do GPS: viagem, treino de lesionados, prevenção, ginásio, recuperação…
create table if not exists public.calendario_eventos (
  id         uuid primary key default gen_random_uuid(),
  team_id    uuid not null references public.teams(id) on delete cascade,
  data       date not null,
  titulo     text not null,
  categoria  text not null default 'Outro',
  criado_por uuid references auth.users(id) on delete set null,
  criado_em  timestamptz not null default now()
);
create index if not exists calendario_eventos_team_data on public.calendario_eventos (team_id, data);

alter table public.calendario_eventos enable row level security;
