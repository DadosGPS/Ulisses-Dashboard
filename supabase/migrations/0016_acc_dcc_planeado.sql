-- 0016 — Acelerações e desacelerações planeadas por dia (o plano do dia passa
-- a ser feito em % do objetivo semanal de cada variável; o valor absoluto
-- calculado guarda-se aqui, ao lado da distância, HSR e sprint).
alter table public.carga_externa_planeada
  add column if not exists acc_n numeric,
  add column if not exists dcc_n numeric;
