-- Estado de disponibilidade do jogador (apto/lesionado/em recuperação/ausente).
-- Necessário para: (1) o preparador físico saber quem está indisponível sem
-- ter de adivinhar a partir da ausência de sessões, (2) excluir/assinalar
-- esses jogadores nos alertas de ACWR (ACWR alto num jogador já lesionado
-- não é um alerta novo, é a razão da lesão).
alter table public.players
  add column estado text not null default 'apto',
  add column estado_motivo text,
  add column estado_desde date not null default current_date;

alter table public.players
  add constraint players_estado_check check (estado in ('apto', 'lesionado', 'em_recuperacao', 'ausente'));
