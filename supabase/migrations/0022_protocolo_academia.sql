-- Protocolo de limites da academia: os mesmos limiares de alerta em todas as
-- equipas, para os avisos de equipas diferentes se poderem comparar.
-- Forma: {"ativo": true, "base": {limiar: valor}, "escaloes": {"Sub-13": {limiar: valor}}}
-- Com o protocolo ativo, os limites pessoais de cada utilizador deixam de
-- contar para as equipas da academia; só o responsável ('head') o altera.
alter table public.academias add column if not exists protocolo jsonb not null default '{}'::jsonb;
