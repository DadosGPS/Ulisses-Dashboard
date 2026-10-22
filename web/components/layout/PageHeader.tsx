import { cores, espaco } from "@/lib/theme";

/** Cabeçalho de página — título, subtítulo e ações à direita. Sóbrio: mesmo
 * fundo da página, um só separador por baixo. */
export function PageHeader({
  titulo,
  subtitulo,
  acoes,
}: {
  titulo: string;
  subtitulo?: string;
  acoes?: React.ReactNode;
}) {
  return (
    <header
      style={{
        display: "flex",
        alignItems: "flex-end",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: espaco.lg,
        padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.lg}px`,
        borderBottom: `1px solid ${cores.borda}`,
      }}
    >
      <div style={{ minWidth: 0 }}>
        <h1 className="font-display" style={{ fontSize: "1.55rem", fontWeight: 650, color: cores.textoForte, margin: 0, letterSpacing: "-0.02em" }}>
          {titulo}
        </h1>
        {subtitulo && <p style={{ color: cores.textoSuave, fontSize: "0.84rem", margin: "4px 0 0", lineHeight: 1.45 }}>{subtitulo}</p>}
      </div>
      {acoes && <div style={{ display: "flex", alignItems: "center", gap: espaco.sm, flexWrap: "wrap" }}>{acoes}</div>}
    </header>
  );
}
