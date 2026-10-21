import { PageHeader } from "@/components/layout/PageHeader";
import { ListaAtletas } from "@/components/academia/ListaAtletas";
import { espaco } from "@/lib/theme";

export default function AcademiaPage() {
  return (
    <div>
      <PageHeader titulo="Academia · Jogadores" subtitulo="Adiciona cada jogador e as equipas em que treina. Os testes de cada equipa estão no seu separador." />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px`, maxWidth: 1200 }}>
        <ListaAtletas />
      </div>
    </div>
  );
}
