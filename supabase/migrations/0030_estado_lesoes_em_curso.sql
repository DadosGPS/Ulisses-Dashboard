-- O Hoje (e o relatório, a semana, o regresso ao jogo) lê players.estado; a
-- página Lesões considera lesionado quem tem uma lesão sem data de fim.
-- Registar uma lesão não mudava o estado, por isso jogadores lesionados
-- apareciam como disponíveis no Hoje. A partir de agora a API mantém os dois
-- iguais (lesoes_service.sincronizar_estado); esta migração acerta os que já
-- existem: quem tem uma lesão em curso e está «apto» passa a «lesionado».
update public.players p
set estado = 'lesionado',
    estado_motivo = coalesce(p.estado_motivo, 'Lesão: ' || l.zona),
    estado_desde = l.data_inicio
from (
  select distinct on (player_id) player_id, zona, data_inicio
  from public.lesoes
  where data_fim is null and data_inicio <= current_date
  order by player_id, data_inicio desc
) l
where p.id = l.player_id and p.estado = 'apto';
