-- Uma folha do Google Sheets por equipa E por tipo de dado: além da PSE
-- (0028), o wellness — as respostas do formulário diário dos jogadores
-- (ex.: «Cópia de AMS - MFF P15 - Wellbeing (respostas)»).
alter table public.fontes_google_sheets
  add column if not exists tipo text not null default 'pse';

do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'fontes_google_sheets_tipo_check') then
    alter table public.fontes_google_sheets
      add constraint fontes_google_sheets_tipo_check check (tipo in ('pse', 'wellness'));
  end if;
end $$;

alter table public.fontes_google_sheets drop constraint if exists fontes_google_sheets_pkey;
alter table public.fontes_google_sheets add primary key (team_id, tipo);
