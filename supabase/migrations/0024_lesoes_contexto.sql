-- Contexto da lesão (treino, jogo ou fora do futebol), para separar a
-- incidência em treino e em jogo por 1000 h de exposição.
alter table public.lesoes add column if not exists contexto text
  check (contexto is null or contexto in ('treino', 'jogo', 'outro'));
