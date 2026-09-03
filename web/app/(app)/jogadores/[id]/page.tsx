import { redirect } from "next/navigation";

/** Este detalhe por id mostrava dados inventados e o perfil real é indexado
 * por nome em /jogadores. Encaminha para o perfil real; quando o segmento é o
 * nome do jogador (como passa a ser a partir do dashboard), abre-o direto. */
export default async function JogadorDetalhePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const decoded = decodeURIComponent(id);
  // Ids UUID antigos não resolvem por nome — nesse caso vai para o hub.
  const pareceUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-/i.test(decoded);
  redirect(pareceUuid ? "/jogadores" : `/jogadores?nome=${encodeURIComponent(decoded)}`);
}
