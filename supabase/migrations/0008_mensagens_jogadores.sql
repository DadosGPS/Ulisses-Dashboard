-- Questionário de bem-estar e PSE no telemóvel do jogador, por WhatsApp.
--
-- players.telefone: número em formato internacional (+351…).
-- players.consentimento_mensagens_em: data em que o clube registou a
--   autorização (do jogador e, se for menor, do encarregado de educação) para
--   receber mensagens e recolher estes dados. Sem esta data a app não envia.
alter table public.players
  add column if not exists telefone text,
  add column if not exists consentimento_mensagens_em date;

-- Um pedido = uma mensagem enviada a um jogador (bem-estar ou PSE de um dia),
-- com um token secreto no link. O link expira em `expira_em`.
create table if not exists public.pedidos_resposta (
  id            uuid primary key default gen_random_uuid(),
  team_id       uuid not null references public.teams(id) on delete cascade,
  player_id     uuid not null references public.players(id) on delete cascade,
  tipo          text not null check (tipo in ('wellness', 'pse')),
  data          date not null,
  token         text not null unique,
  duracao_min   numeric,                 -- PSE: duração da sessão definida por quem pediu
  estado_envio  text not null default 'pendente', -- pendente | enviado | simulado | erro
  erro          text,
  enviado_em    timestamptz,
  respondido_em timestamptz,
  expira_em     timestamptz not null,
  criado_em     timestamptz not null default now(),
  unique (team_id, player_id, tipo, data)
);
create index if not exists pedidos_resposta_team_data on public.pedidos_resposta (team_id, data);

-- Configuração do envio automático por equipa.
create table if not exists public.config_mensagens (
  team_id         uuid primary key references public.teams(id) on delete cascade,
  wellness_auto   boolean not null default false,
  wellness_hora   text not null default '08:00',      -- hora de Lisboa, HH:MM
  wellness_dias   int[] not null default '{1,2,3,4,5}', -- 1 = segunda … 7 = domingo
  atualizado_em   timestamptz not null default now()
);
