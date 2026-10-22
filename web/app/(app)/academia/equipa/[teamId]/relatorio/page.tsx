import { redirect } from "next/navigation";

// Endereço antigo do relatório — agora é a página principal da equipa.
export default async function RelatorioAntigo({ params }: { params: Promise<{ teamId: string }> }) {
  const { teamId } = await params;
  redirect(`/academia/equipa/${teamId}`);
}
