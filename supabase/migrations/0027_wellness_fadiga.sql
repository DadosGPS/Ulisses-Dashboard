-- Item de fadiga no questionário de bem-estar (1 = muito cansado … 5 = fresco),
-- como os outros quatro itens. O Hooper Index continua a ser a soma dos quatro
-- itens originais (para não mudar a escala nem o histórico); a fadiga entra na
-- regra por item (≥ 2 pontos abaixo do normal do próprio jogador).
alter table gps_sessions add column if not exists fadiga numeric;
