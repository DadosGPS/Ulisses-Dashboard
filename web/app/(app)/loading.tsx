import { Bloco, Carregando } from "@/components/ui/Esqueleto";
import { cores, espaco } from "@/lib/theme";

/** Mostrado pelo Next enquanto a página do servidor vai buscar os dados. */
export default function A_Carregar() {
  return (
    <div>
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.lg}px`, borderBottom: `1px solid ${cores.borda}`, display: "flex", flexDirection: "column", gap: 8 }}>
        <Bloco altura={24} largura={260} />
        <Bloco altura={12} largura={340} />
      </div>
      <Carregando cartoes={4} linhas={8} />
    </div>
  );
}
