-- Rotina diária do preparador físico.
-- 1) Mensagens automáticas: PSE depois das sessões, lembrete a quem não
--    respondeu e fuso horário de cada equipa (as horas são locais).
alter table public.config_mensagens add column if not exists pse_auto boolean not null default false;
alter table public.config_mensagens add column if not exists pse_hora text not null default '19:30';
alter table public.config_mensagens add column if not exists lembrete_auto boolean not null default false;
alter table public.config_mensagens add column if not exists lembrete_apos_min int not null default 120
  check (lembrete_apos_min between 15 and 720);
alter table public.config_mensagens add column if not exists fuso text not null default 'Europe/Lisbon';
alter table public.pedidos_resposta add column if not exists lembrete_em timestamptz;

-- 2) Importação de GPS: o último mapeamento de colunas confirmado em cada
--    equipa, para não ter de o rever todos os dias.
create table if not exists public.config_importacao (
  team_id       uuid primary key references public.teams(id) on delete cascade,
  mapa          jsonb not null default '{}'::jsonb,
  atualizado_em timestamptz not null default now()
);
alter table public.config_importacao enable row level security;
