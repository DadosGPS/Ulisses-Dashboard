import { JogosEquipa } from "@/components/academia/JogosEquipa";

export default async function JogosEquipaPage({ params }: { params: Promise<{ teamId: string }> }) {
  const { teamId } = await params;
  return <JogosEquipa teamId={teamId} />;
}
