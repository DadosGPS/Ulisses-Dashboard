import { PageHeader } from "@/components/layout/PageHeader";
import { ListaAtletas } from "@/components/academia/ListaAtletas";
import { espaco } from "@/lib/theme";

export default function AcademiaPage() {
  return (
    <div>
      <PageHeader titulo="Academia" subtitulo="A ficha de cada atleta ao longo de todas as épocas e escalões" />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px`, maxWidth: 1200 }}>
        <ListaAtletas />
      </div>
    </div>
  );
}
