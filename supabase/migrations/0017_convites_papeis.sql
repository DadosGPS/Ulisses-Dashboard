-- ═══════════════════════════════════════════════════════════════════════════
-- 0017 — Convites para a equipa técnica e papéis
-- ═══════════════════════════════════════════════════════════════════════════
-- Papéis:
--   academia_membros.papel: 'head' (responsável: vê e gere a academia toda),
--                           'staff' (PF: edita as suas equipas),
--                           'leitura' (treinador: só consulta)
--   team_members.role:      'owner' / 'pf' (editam), 'treinador' (só consulta)
alter table public.academia_membros drop constraint if exists academia_membros_papel_check;
alter table public.academia_membros
  add constraint academia_membros_papel_check check (papel in ('head', 'staff', 'leitura'));

create table if not exists public.convites (
  id           uuid primary key default gen_random_uuid(),
  academia_id  uuid not null references public.academias(id) on delete cascade,
  papel        text not null check (papel in ('head', 'pf', 'treinador')),
  team_ids     uuid[] not null default '{}',
  email        text,
  nome         text,
  token        text not null unique,
  criado_por   uuid references auth.users(id) on delete set null,
  criado_em    timestamptz not null default now(),
  expira_em    timestamptz not null default (now() + interval '14 days'),
  aceite_por   uuid references auth.users(id) on delete set null,
  aceite_em    timestamptz,
  revogado     boolean not null default false
);
create index if not exists convites_academia on public.convites (academia_id);
alter table public.convites enable row level security;

-- Quem se regista a partir de um convite não ganha uma equipa vazia "A Minha
-- Equipa": entra só nas equipas do convite (ao aceitá-lo na app).
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  novo_team_id uuid;
begin
  insert into public.profiles (id, nome, clube)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'nome', split_part(new.email, '@', 1)),
    new.raw_user_meta_data->>'clube'
  );

  if coalesce(new.raw_user_meta_data->>'convite', '') <> '' then
    return new;
  end if;

  insert into public.teams (nome, desporto, criado_por)
  values (
    coalesce(nullif(new.raw_user_meta_data->>'clube', ''), 'A Minha Equipa'),
    'Futebol',
    new.id
  )
  returning id into novo_team_id;

  insert into public.team_members (team_id, user_id, role)
  values (novo_team_id, new.id, 'owner');

  return new;
end;
$$;
