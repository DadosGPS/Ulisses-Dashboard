import { RelatoriosEquipa } from "@/components/academia/RelatoriosEquipa";

export default async function RelatorioEquipaPage({ params }: { params: Promise<{ teamId: string }> }) {
  const { teamId } = await params;
  return <RelatoriosEquipa teamId={teamId} />;
}
