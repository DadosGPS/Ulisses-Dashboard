import { cores, espaco } from "@/lib/theme";

/** Cabeçalho de página consistente — título + subtítulo + zona de ações à direita. */
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
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: espaco.lg,
        padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.lg}px`,
        borderBottom: `1px solid ${cores.borda}`,
        background: cores.bgElevado,
      }}
    >
      <div>
        <h1 className="font-display" style={{ fontSize: "1.5rem", fontWeight: 700, color: "white", margin: 0, letterSpacing: "-0.01em" }}>
          {titulo}
        </h1>
        {subtitulo && (
          <p style={{ color: cores.textoSuave, fontSize: "0.85rem", margin: "4px 0 0" }}>{subtitulo}</p>
        )}
      </div>
      {acoes && <div style={{ display: "flex", alignItems: "center", gap: espaco.sm }}>{acoes}</div>}
    </div>
  );
}
