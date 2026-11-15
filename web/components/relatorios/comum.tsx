/** Peças partilhadas pelos relatórios de treino e de jogo (servidor e cliente). */
import { cores, corAlvo, desvio, espaco, estado } from "@/lib/theme";
import type { Tr } from "@/lib/i18n/core";
import { LegendaCores } from "@/components/ui/Indicadores";

export type Banda = "muito_abaixo" | "abaixo" | "dentro" | "acima" | "muito_acima";
export type Estado = "alto" | "baixo" | "normal" | "insuficiente";
export interface MetricaDesc { chave: string; label: string; unidade: string; casas: number }

/** Cor de cada métrica (a mesma da app inteira). */
export const COR: Record<string, string> = {
  distancia: cores.distanciaTotal, hsr: cores.hsr, sprint: cores.sprint, acc: cores.acc, dcc: cores.dcc, vmax: cores.velMax,
};

/** Bandas do alvo na linguagem de cor da app (theme.ts): fora de 80–120 % = agir. */
export const COR_BANDA: Record<Banda, string> = {
  muito_abaixo: estado.agir, abaixo: estado.vigiar, dentro: estado.ok, acima: estado.vigiar, muito_acima: estado.agir,
};
export { corAlvo };
export const ROTULO_BANDA: Record<Banda, string> = {
  muito_abaixo: "< 80 %", abaixo: "80–90 %", dentro: "90–110 %", acima: "110–120 %", muito_acima: "> 120 %",
};
/** Acima / abaixo do habitual: desvio sem juízo (azul / violeta), nunca verde/vermelho. */
export const COR_ESTADO: Record<Estado, string> = {
  alto: desvio.acima, baixo: desvio.abaixo, normal: cores.textoSuave, insuficiente: cores.textoFraco,
};

export function fmt(v: number | null | undefined, casas = 0, loc = "pt-PT"): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return v.toLocaleString(loc, { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

export function fmtPct(v: number | null | undefined, loc = "pt-PT", sinal = true): string {
  if (v === null || v === undefined) return "—";
  return `${sinal && v > 0 ? "+" : ""}${fmt(v, 0, loc)} %`;
}

export function dataCurta(iso: string, loc: string): string {
  const d = new Date(`${iso}T12:00:00`);
  return d.toLocaleDateString(loc, { weekday: "short", day: "2-digit", month: "short" });
}

export { Kpi } from "@/components/ui/Indicadores";

/** Célula com a % do alvo, colorida pela banda. */
export function CelulaPct({ pct, banda, loc }: { pct: number | null; banda: Banda | null; loc: string }) {
  if (pct === null || !banda) return <span style={{ color: cores.textoFraco }}>—</span>;
  const cor = COR_BANDA[banda];
  return (
    <span style={{ display: "inline-block", minWidth: 52, textAlign: "center", fontWeight: 650, fontSize: "0.78rem", color: cor,
      background: `color-mix(in srgb, ${cor} 13%, transparent)`, borderRadius: 6, padding: "2px 6px" }}>
      {fmt(pct, 0, loc)} %
    </span>
  );
}

/** Seta/etiqueta de estado face ao habitual (próprio histórico). */
export function MarcaEstado({ estado, delta, tr }: { estado: Estado; delta: number | null; tr: Tr }) {
  if (estado === "insuficiente") return <span title={tr("Histórico insuficiente")} style={{ color: cores.textoFraco, fontSize: "0.72rem" }}>·</span>;
  const cor = COR_ESTADO[estado];
  const simb = estado === "alto" ? "▲" : estado === "baixo" ? "▼" : "•";
  return (
    <span title={delta !== null ? fmtPct(delta, tr.loc) : undefined} style={{ color: cor, fontSize: "0.7rem", marginLeft: 4 }}>{simb}</span>
  );
}

/** Legenda das bandas do alvo. */
export function LegendaBandas({ tr }: { tr: Tr }) {
  return <LegendaCores tr={tr} tipos={["alvo", "desvio"]} />;
}

export const tabela: React.CSSProperties = { width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" };
export const th: React.CSSProperties = {
  textAlign: "right", padding: "8px 10px", fontSize: "0.64rem", letterSpacing: "0.05em", textTransform: "uppercase",
  color: cores.textoSuave, fontWeight: 600, whiteSpace: "nowrap", borderBottom: `1px solid ${cores.borda}`,
};
export const thEsq: React.CSSProperties = { ...th, textAlign: "left" };
export const td: React.CSSProperties = { padding: "7px 10px", textAlign: "right", whiteSpace: "nowrap", color: cores.texto, borderBottom: `1px solid ${cores.borda}` };
export const tdEsq: React.CSSProperties = { ...td, textAlign: "left" };
export const nota: React.CSSProperties = { fontSize: "0.74rem", color: cores.textoSuave, lineHeight: 1.5, margin: `${espaco.md}px 0 0` };
