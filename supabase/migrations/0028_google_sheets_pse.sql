-- Ligação de uma equipa a uma folha do Google Sheets com a PSE dos jogadores
-- (ex.: «P15 - RPE» na pasta MALMÖ FF U15). A API lê a folha com uma conta de
-- serviço Google (só leitura) e grava, a partir de `data_inicio`:
--   · a PSE real de cada jogador em gps_sessions (pse_sessao, duração, sRPE);
--   · a PSE esperada de cada dia em pse_planeado (o gráfico «PSE esperada vs real»).
-- Linhas anteriores a `data_inicio` são ignoradas.
create table if not exists public.fontes_google_sheets (
  team_id               uuid primary key references public.teams(id) on delete cascade,
  spreadsheet_id        text not null,
  folha                 text not null default 'RPE',
  data_inicio           date not null,
  -- Valor da coluna TEAM a importar (ex.: 'P15'); vazio = todas as linhas.
  filtro_equipa         text,
  ativo                 boolean not null default true,
  ultima_sincronizacao  timestamptz,
  ultimo_resultado      jsonb,
  criado_por            uuid references public.profiles(id) on delete set null,
  criado_em             timestamptz not null default now(),
  atualizado_em         timestamptz not null default now()
);

alter table public.fontes_google_sheets enable row level security;

create policy "fontes_google_sheets_all_member" on public.fontes_google_sheets
  for all using (
    team_id in (select team_id from public.team_members where user_id = auth.uid())
  );
