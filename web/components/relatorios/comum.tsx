/** Peças partilhadas pelos relatórios de treino e de jogo (servidor e cliente). */
import { cores, espaco, raio } from "@/lib/theme";
import type { Tr } from "@/lib/i18n/core";

export type Banda = "muito_abaixo" | "abaixo" | "dentro" | "acima" | "muito_acima";
export type Estado = "alto" | "baixo" | "normal" | "insuficiente";
export interface MetricaDesc { chave: string; label: string; unidade: string; casas: number }

/** Cor de cada métrica (a mesma da app inteira). */
export const COR: Record<string, string> = {
  distancia: cores.distanciaTotal, hsr: cores.hsr, sprint: cores.sprint, acc: cores.acc, dcc: cores.dcc, vmax: cores.velMax,
};

export const COR_BANDA: Record<Banda, string> = {
  muito_abaixo: cores.info, abaixo: "#60a5fa", dentro: cores.sucesso, acima: cores.atencao, muito_acima: cores.perigo,
};
export const ROTULO_BANDA: Record<Banda, string> = {
  muito_abaixo: "< 80 %", abaixo: "80–90 %", dentro: "90–110 %", acima: "110–120 %", muito_acima: "> 120 %",
};
export const COR_ESTADO: Record<Estado, string> = {
  alto: cores.sucesso, baixo: cores.perigo, normal: cores.textoSuave, insuficiente: cores.textoFraco,
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

/** Cartão de número grande (KPI). */
export function Kpi({ rotulo, valor, unidade, rodape, cor, destaque }: {
  rotulo: string; valor: string; unidade?: string; rodape?: React.ReactNode; cor?: string; destaque?: string;
}) {
  return (
    <div style={{
      background: destaque ? `color-mix(in srgb, ${destaque} 9%, ${cores.bgCartao})` : cores.bgCartao,
      border: `1px solid ${destaque ? `color-mix(in srgb, ${destaque} 40%, transparent)` : cores.borda}`,
      borderRadius: raio.md, padding: `${espaco.md}px ${espaco.lg}px`, minWidth: 0,
    }}>
      <div style={{ fontSize: "0.68rem", fontWeight: 600, letterSpacing: "0.04em", textTransform: "uppercase", color: cores.textoSuave }}>{rotulo}</div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 5, marginTop: 4 }}>
        <span className="font-display" style={{ fontSize: "1.65rem", fontWeight: 700, color: cor ?? cores.textoForte, letterSpacing: "-0.02em", lineHeight: 1.1 }}>{valor}</span>
        {unidade && <span style={{ fontSize: "0.8rem", color: cores.textoSuave }}>{unidade}</span>}
      </div>
      {rodape && <div style={{ fontSize: "0.74rem", color: cores.textoSuave, marginTop: 4 }}>{rodape}</div>}
    </div>
  );
}

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
  return (
    <div style={{ display: "flex", gap: espaco.md, flexWrap: "wrap", fontSize: "0.72rem", color: cores.textoSuave }}>
      {(Object.keys(ROTULO_BANDA) as Banda[]).map((b) => (
        <span key={b} style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
          <span style={{ width: 9, height: 9, borderRadius: 3, background: COR_BANDA[b] }} />{ROTULO_BANDA[b]}{b === "dentro" ? ` · ${tr("dentro do alvo")}` : ""}
        </span>
      ))}
    </div>
  );
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
