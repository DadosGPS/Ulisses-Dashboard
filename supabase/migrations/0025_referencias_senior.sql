-- Referências do plantel sénior (valores do primeiro plantel, introduzidos
-- pelo responsável da academia), para cada atleta ver a distância que falta
-- nos testes físicos. Forma: {metrica: {"valor": 1.72, "posicoes": {"DC": 1.75}}}
alter table public.academias add column if not exists referencias_senior jsonb not null default '{}'::jsonb;
