import { PageHeader } from "@/components/layout/PageHeader";
import { GestaoAcademia } from "@/components/ui/GestaoAcademia";
import { EquipaTecnica } from "@/components/ui/EquipaTecnica";
import { ProtocoloAcademia } from "@/components/ui/ProtocoloAcademia";
import { espaco } from "@/lib/theme";
import { obterTr } from "@/lib/i18n/servidor";

export default async function AcademiaPage() {
  const tr = await obterTr();
  return (
    <div>
      <PageHeader titulo={tr("Definições · Academia")} subtitulo={tr("Cada escalão em cada época é uma equipa; os atletas mantêm a sua ficha ao longo dos anos")} />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px`, maxWidth: 1100 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: espaco.xxl }}>
          <EquipaTecnica />
          <ProtocoloAcademia />
          <GestaoAcademia />
        </div>
      </div>
    </div>
  );
}
