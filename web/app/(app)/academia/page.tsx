import { PageHeader } from "@/components/layout/PageHeader";
import { ListaAtletas } from "@/components/academia/ListaAtletas";
import { espaco } from "@/lib/theme";
import { obterTr } from "@/lib/i18n/servidor";

export default async function AcademiaPage() {
  const tr = await obterTr();
  return (
    <div>
      <PageHeader titulo={tr("Academia · Jogadores")} subtitulo={tr("Adiciona cada jogador e as equipas em que treina. Os testes de cada equipa estão no seu separador.")} />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px`, maxWidth: 1200 }}>
        <ListaAtletas />
      </div>
    </div>
  );
}
