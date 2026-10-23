import { TestesEquipa } from "@/components/academia/TestesEquipa";

export default async function TestesEquipaPage({ params }: { params: Promise<{ teamId: string }> }) {
  const { teamId } = await params;
  return <TestesEquipa teamId={teamId} />;
}
