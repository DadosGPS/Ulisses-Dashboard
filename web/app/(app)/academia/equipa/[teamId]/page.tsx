import { RelatoriosEquipa } from "@/components/academia/RelatoriosEquipa";

/** Página da equipa: abre nos resultados (relatório T1–T4); registar testes
 * e jogos ficam nos outros separadores. */
export default async function EquipaAcademiaPage({ params }: { params: Promise<{ teamId: string }> }) {
  const { teamId } = await params;
  return <RelatoriosEquipa teamId={teamId} />;
}
