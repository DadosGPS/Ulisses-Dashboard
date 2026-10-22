import { PageHeader } from "@/components/layout/PageHeader";
import { ListaAtletas } from "@/components/academia/ListaAtletas";
import { espaco } from "@/lib/theme";
import { obterTr } from "@/lib/i18n/servidor";

export default async function AcademiaPage() {
  const tr = await obterTr();
  return (
    <div>
      <PageHeader titulo={tr("Academia · Jogadores")} subtitulo={tr("Todos os jogadores da academia e as equipas em que treinam. Os testes e os resultados de cada equipa estão no separador do escalão.")} />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px`, maxWidth: 1200 }}>
        <ListaAtletas />
      </div>
    </div>
  );
}
