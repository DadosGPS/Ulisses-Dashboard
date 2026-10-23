-- Biblioteca de exercícios da academia (rondos, jogos reduzidos, finalização…).
-- A carga GPS típica de cada exercício vem da folha de exercícios importada
-- (tabela exercises, ligada pelo nome); os valores "manual" (por minuto) servem
-- para exercícios ainda sem GPS. O plano de exercícios de cada dia fica no
-- campo dias do microciclo (dias.<data>.exercicios).
create table if not exists public.exercicios_biblioteca (
  id            uuid primary key default gen_random_uuid(),
  academia_id   uuid not null references public.academias(id) on delete cascade,
  nome          text not null,
  categoria     text,
  descricao     text,
  formato       text,          -- ex.: 4v4+2
  espaco        text,          -- ex.: 30×20 m
  duracao_min   int check (duracao_min between 1 and 180),
  manual        jsonb not null default '{}'::jsonb,
  criado_por    uuid references auth.users(id) on delete set null,
  criado_em     timestamptz not null default now(),
  atualizado_em timestamptz not null default now()
);
create unique index if not exists exercicios_biblioteca_nome on public.exercicios_biblioteca (academia_id, lower(nome));
alter table public.exercicios_biblioteca enable row level security;
