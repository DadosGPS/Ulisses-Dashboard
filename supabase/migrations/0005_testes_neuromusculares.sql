-- Testes neuromusculares (CMJ, etc.) — base do perfil individual do jogador
-- (velocidade/força/potência/conditioning) e dos STEN scores. Importados da
-- folha "Testes_Neuromusculares" do template, a par de BD_Carga.
create table public.testes_neuromusculares (
  id                uuid primary key default gen_random_uuid(),
  team_id           uuid not null references public.teams(id) on delete cascade,
  player_id         uuid not null references public.players(id) on delete cascade,
  upload_id         uuid references public.uploads(id) on delete set null,
  data              date,
  tipo_teste        text,
  altura_salto_cm   numeric,
  potencia_rel_wkg  numeric,
  rsi               numeric,
  tempo_contacto_ms numeric,
  assimetria_pct    numeric,
  rfd               numeric,
  extra_metrics     jsonb not null default '{}'::jsonb,
  criado_em         timestamptz not null default now()
);
create index on public.testes_neuromusculares (team_id, data);
create index on public.testes_neuromusculares (player_id, data);
