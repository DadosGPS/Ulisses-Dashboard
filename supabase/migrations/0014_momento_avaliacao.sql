-- 0014 — Momento de avaliação (T1–T4) em cada registo de teste.
-- Uma época tem 4 momentos; os relatórios comparam a progressão T1 → T4.
-- Sem momento (registos antigos), a app deduz pela data: T1 jul–set,
-- T2 out–dez, T3 jan–mar, T4 abr–jun.
alter table public.avaliacoes
  add column if not exists momento smallint check (momento between 1 and 4);
