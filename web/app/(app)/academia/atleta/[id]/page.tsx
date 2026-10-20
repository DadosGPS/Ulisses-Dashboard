import { FichaAtletaView } from "@/components/academia/FichaAtleta";
import { espaco } from "@/lib/theme";

export default async function FichaAtletaPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <div style={{ maxWidth: 1300 }}>
      <FichaAtletaView atletaId={id} />
      <div style={{ height: espaco.xxl }} />
    </div>
  );
}
