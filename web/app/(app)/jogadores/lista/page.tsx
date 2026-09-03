import { redirect } from "next/navigation";

/** A lista de jogadores mostrava dados inventados. O perfil real de jogador
 * (com seletor) vive em /jogadores — redireciona para lá. */
export default function JogadoresListaPage() {
  redirect("/jogadores");
}
