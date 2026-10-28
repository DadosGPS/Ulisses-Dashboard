import { PageHeader } from "@/components/layout/PageHeader";
import { QualidadeDados } from "@/components/academia/QualidadeDados";
import { espaco } from "@/lib/theme";
import { obterTr } from "@/lib/i18n/servidor";

export default async function QualidadeDadosPage() {
  const tr = await obterTr();
  return (
    <div>
      <PageHeader titulo={tr("Academia · Qualidade dos dados")} subtitulo={tr("Quanto do wellness, da PSE e do GPS cada equipa regista, mês a mês")} />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px`, maxWidth: 1100 }}>
        <QualidadeDados />
      </div>
    </div>
  );
}
