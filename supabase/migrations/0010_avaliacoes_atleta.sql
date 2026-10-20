-- ═══════════════════════════════════════════════════════════════════════════
-- 0010 — Avaliações do atleta ao longo das épocas (ficha longitudinal)
-- ═══════════════════════════════════════════════════════════════════════════
-- Formato longo: uma linha = uma métrica medida num dia (ex.: altura 162,4 cm;
-- sprint 30 m 4,62 s; Yo-Yo IR1 1 240 m). Assim novos testes entram sem mudar
-- o esquema. Ligada à FICHA do atleta (atletas), não à equipa: os valores
-- acompanham-no quando muda de escalão ou de época. team_id regista em que
-- equipa estava quando foi avaliado (contexto), e pode ficar vazio.
--
-- Requer a migração 0009 (academias/atletas).
create table if not exists public.avaliacoes (
  id           uuid primary key default gen_random_uuid(),
  academia_id  uuid not null references public.academias(id) on delete cascade,
  atleta_id    uuid not null references public.atletas(id) on delete cascade,
  team_id      uuid references public.teams(id) on delete set null,
  data         date not null,
  metrica      text not null,     -- chave do catálogo (api/app/services/ficha_atleta_service.py)
  valor        numeric not null,
  notas        text,
  criado_por   uuid references auth.users(id) on delete set null,
  criado_em    timestamptz not null default now(),
  unique (atleta_id, data, metrica)
);
create index if not exists avaliacoes_atleta_data on public.avaliacoes (atleta_id, data);
create index if not exists avaliacoes_academia_metrica on public.avaliacoes (academia_id, metrica);

alter table public.avaliacoes enable row level security;

-- Data de nascimento e posição principal na ficha (a da equipa pode mudar).
alter table public.atletas
  add column if not exists posicao_principal text,
  add column if not exists pe_dominante text check (pe_dominante in ('direito', 'esquerdo', 'ambos'));
