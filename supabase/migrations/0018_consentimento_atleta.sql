-- 0018 — Consentimento para o tratamento dos dados do atleta (RGPD).
-- Atletas menores: o consentimento é dado pelo encarregado de educação.
alter table public.atletas
  add column if not exists consentimento_dados_em date,
  add column if not exists consentimento_por text
    check (consentimento_por is null or consentimento_por in ('atleta', 'encarregado')),
  add column if not exists consentimento_notas text;
