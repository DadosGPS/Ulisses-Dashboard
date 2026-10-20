-- ═══════════════════════════════════════════════════════════════════════════
-- 0009 — Academia (escalões × épocas) + correção de segurança (RLS)
-- ═══════════════════════════════════════════════════════════════════════════
--
-- 1) SEGURANÇA. As tabelas das migrações 0003–0008 foram criadas sem RLS, o
--    que no Supabase as deixa legíveis pela API pública (chave anon). A app
--    web não lê estas tabelas diretamente — só a API, cuja ligação
--    (DATABASE_URL, dono das tabelas) ignora o RLS — por isso ligar o RLS sem
--    políticas fecha o acesso público sem afetar nada.
alter table public.pse_planeado           enable row level security;
alter table public.carga_externa_planeada enable row level security;
alter table public.testes_neuromusculares enable row level security;
alter table public.lesoes                 enable row level security;
alter table public.planos_rtp             enable row level security;
alter table public.pedidos_resposta       enable row level security;
alter table public.config_mensagens       enable row level security;

-- 2) ACADEMIA. Uma camada POR CIMA do que existe: cada escalão numa época
--    continua a ser uma equipa (teams) — todas as páginas atuais funcionam
--    igual, cada uma com os dados da sua época. O que é novo:
--      • academias: o clube;
--      • teams.academia_id / escalao / epoca: onde cada equipa se arruma;
--      • atletas: a ficha PERMANENTE de cada jogador na academia, que liga
--        as suas linhas em players (uma por equipa/época) ao longo dos anos.
create table if not exists public.academias (
  id         uuid primary key default gen_random_uuid(),
  nome       text not null,
  criado_em  timestamptz not null default now()
);

create table if not exists public.academia_membros (
  academia_id uuid not null references public.academias(id) on delete cascade,
  user_id     uuid not null references auth.users(id) on delete cascade,
  papel       text not null default 'staff' check (papel in ('head', 'staff')),
  criado_em   timestamptz not null default now(),
  primary key (academia_id, user_id)
);

alter table public.teams
  add column if not exists academia_id uuid references public.academias(id) on delete set null,
  add column if not exists escalao     text,   -- ex.: 'Sub-15', 'Sub-19', 'Equipa B', 'Seniores'
  add column if not exists epoca       text;   -- ex.: '2026/27'
create index if not exists teams_academia on public.teams (academia_id);

create table if not exists public.atletas (
  id               uuid primary key default gen_random_uuid(),
  academia_id      uuid not null references public.academias(id) on delete cascade,
  nome             text not null,
  data_nascimento  date,
  criado_em        timestamptz not null default now()
);
-- Mesmo nome + mesma data de nascimento = mesmo atleta (sem data, só o nome).
create unique index if not exists atletas_identidade
  on public.atletas (academia_id, lower(nome), coalesce(data_nascimento, '1900-01-01'::date));

alter table public.players
  add column if not exists atleta_id       uuid references public.atletas(id) on delete set null,
  add column if not exists data_nascimento date;
create index if not exists players_atleta on public.players (atleta_id);

alter table public.academias        enable row level security;
alter table public.academia_membros enable row level security;
alter table public.atletas          enable row level security;

-- 3) EQUIPAS EXISTENTES. Cada equipa sem academia ganha uma academia com o
--    mesmo nome e os membros da equipa ficam como 'head'. NÃO se criam fichas
--    de atleta: a academia começa vazia e cada jogador é adicionado um a um
--    pelo preparador físico (página Academia). Pode correr-se mais do que uma vez.
do $$
declare
  t record;
  nova uuid;
begin
  for t in select id, nome from public.teams where academia_id is null loop
    insert into public.academias (nome) values (coalesce(t.nome, 'Academia')) returning id into nova;
    update public.teams set academia_id = nova where id = t.id;
    insert into public.academia_membros (academia_id, user_id, papel)
      select nova, tm.user_id, 'head' from public.team_members tm where tm.team_id = t.id
      on conflict do nothing;
  end loop;
end $$;
