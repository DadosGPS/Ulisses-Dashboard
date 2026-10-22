/** Peças de interface partilhadas — a mesma aparência em todas as páginas.
 * Estilo sóbrio: neutros do tema, um só acento, cor apenas onde tem
 * significado (métricas e estados). */
import { cores, espaco, raio, sombra } from "@/lib/theme";
import { Ajuda } from "./Ajuda";

/** Título de secção, com subtítulo e ações opcionais à direita. */
export function SecaoTitulo({
  children,
  subtitulo,
  acoes,
  ajuda,
  margem = espaco.md,
}: {
  children: React.ReactNode;
  subtitulo?: React.ReactNode;
  acoes?: React.ReactNode;
  /** Explicação longa (como se calcula / como se lê), atrás de um ícone «i». */
  ajuda?: React.ReactNode;
  margem?: number;
}) {
  return (
    <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: espaco.md, flexWrap: "wrap", marginBottom: margem }}>
      <div style={{ minWidth: 0 }}>
        <h2 style={{ fontSize: "0.95rem", fontWeight: 600, color: cores.textoForte, margin: 0, letterSpacing: "-0.005em", display: "flex", alignItems: "center", gap: 7 }}>
          {children}{ajuda && <Ajuda>{ajuda}</Ajuda>}
        </h2>
        {subtitulo && <p style={{ fontSize: "0.78rem", color: cores.textoSuave, margin: "3px 0 0", lineHeight: 1.45 }}>{subtitulo}</p>}
      </div>
      {acoes && <div style={{ display: "flex", alignItems: "center", gap: espaco.sm }}>{acoes}</div>}
    </div>
  );
}

/** Cartão base: fundo do tema, borda fina, cantos e sombra iguais em toda a app. */
export function Cartao({
  children,
  padding = espaco.lg,
  destaque,
  style,
}: {
  children: React.ReactNode;
  padding?: number;
  /** Cor de uma linha fina à esquerda, para estados (ok, atenção…). */
  destaque?: string;
  style?: React.CSSProperties;
}) {
  return (
    <div
      style={{
        background: cores.bgCartao,
        border: `1px solid ${cores.borda}`,
        borderLeft: destaque ? `3px solid ${destaque}` : `1px solid ${cores.borda}`,
        borderRadius: raio.md,
        boxShadow: sombra.cartao,
        padding,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

/** Etiqueta pequena (estado, zona, contagem). */
export function Etiqueta({ cor, children, title }: { cor: string; children: React.ReactNode; title?: string }) {
  return (
    <span
      title={title}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        fontSize: "0.7rem",
        fontWeight: 600,
        color: cor,
        background: `color-mix(in srgb, ${cor} 12%, transparent)`,
        padding: "2px 8px",
        borderRadius: 999,
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </span>
  );
}

export const estiloBotao = {
  primario: {
    background: cores.acento,
    color: cores.sobreAcento,
    border: "none",
    borderRadius: raio.sm,
    padding: "7px 14px",
    fontSize: "0.82rem",
    fontWeight: 600,
    cursor: "pointer",
  } as React.CSSProperties,
  secundario: {
    background: cores.bgCartao,
    color: cores.texto,
    border: `1px solid ${cores.bordaForte}`,
    borderRadius: raio.sm,
    padding: "6px 12px",
    fontSize: "0.82rem",
    fontWeight: 500,
    cursor: "pointer",
  } as React.CSSProperties,
  ligacao: {
    background: "none",
    border: "none",
    color: cores.acento,
    fontSize: "0.8rem",
    fontWeight: 500,
    cursor: "pointer",
    padding: 0,
  } as React.CSSProperties,
};

/** Estado vazio de uma secção (sem dados, sem resultados). */
export function Vazio({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ border: `1px dashed ${cores.bordaForte}`, borderRadius: raio.md, padding: espaco.lg, color: cores.textoSuave, fontSize: "0.85rem", textAlign: "center" }}>
      {children}
    </div>
  );
}
