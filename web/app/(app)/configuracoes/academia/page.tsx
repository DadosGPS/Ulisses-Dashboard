import { PageHeader } from "@/components/layout/PageHeader";
import { GestaoAcademia } from "@/components/ui/GestaoAcademia";
import { espaco } from "@/lib/theme";

export default function AcademiaPage() {
  return (
    <div>
      <PageHeader titulo="Definições · Academia" subtitulo="Cada escalão em cada época é uma equipa; os atletas mantêm a sua ficha ao longo dos anos" />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px`, maxWidth: 1100 }}>
        <GestaoAcademia />
      </div>
    </div>
  );
}
