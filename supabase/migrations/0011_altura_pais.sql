-- 0011 — Altura dos pais na ficha do atleta (maturação pelo método de
-- Khamis-Roche: estatura adulta prevista a partir da idade, altura e peso da
-- criança e da altura média dos pais). Requer a migração 0010.
alter table public.atletas
  add column if not exists altura_pai_cm numeric check (altura_pai_cm is null or altura_pai_cm between 130 and 230),
  add column if not exists altura_mae_cm numeric check (altura_mae_cm is null or altura_mae_cm between 120 and 215),
  add column if not exists altura_pais_medida boolean;  -- true = medida; false = indicada pelos pais
