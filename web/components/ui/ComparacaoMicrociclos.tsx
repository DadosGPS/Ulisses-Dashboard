"use client";

import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { cores, espaco, raio } from "@/lib/theme";
import type { ResumoSemana } from "@/lib/types";

const ORDEM_MD = ["MD-6", "MD-5", "MD-4", "MD-3", "MD-2", "MD-1", "MD", "MD+1", "MD+2"];
const COR_A = cores.cargaInterna;
const COR_B = cores.info;

function uniaoDias(a: { dia_md: string }[], b: { dia_md: string }[]): string[] {
  const set = new Set([...a.map((d) => d.dia_md), ...b.map((d) => d.dia_md)]);
  return ORDEM_MD.filter((d) => set.has(d));
}

/** Comparação lado a lado de dois microciclos: barras agrupadas por dia MD
 * para carga interna e PSE, mais um resumo de deltas. */
export function ComparacaoMicrociclos({ a, b }: { a: ResumoSemana; b: ResumoSemana }) {
  const labelA = `Semana ${a.microciclo ?? "?"}`;
  const labelB = `Semana ${b.microciclo ?? "?"}`;

  const diasCarga = uniaoDias(a.carga_por_dia, b.carga_por_dia);
  const diasPse = uniaoDias(a.pse_por_dia, b.pse_por_dia);

  const valCarga = (r: ResumoSemana, dia: string) => r.carga_por_dia.find((d) => d.dia_md === dia)?.carga_media ?? null;
  const valPse = (r: ResumoSemana, dia: string) => r.pse_por_dia.find((d) => d.dia_md === dia)?.pse_media ?? null;

  return (
    <div>
      {/* Deltas resumo */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: espaco.md, marginBottom: espaco.lg }}>
        <DeltaCard titulo="Carga interna média" a={a.carga_interna_media} b={b.carga_interna_media} unidade="UA" labelA={labelA} labelB={labelB} />
        <DeltaCard titulo="Monotonia" a={a.monotonia_media} b={b.monotonia_media} unidade="" labelA={labelA} labelB={labelB} casas={2} />
        <DeltaCard titulo="Strain" a={a.strain_medio} b={b.strain_medio} unidade="" labelA={labelA} labelB={labelB} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: espaco.lg }}>
        <GraficoAgrupado
          titulo="Carga por dia (UA)"
          dias={diasCarga}
          serieA={diasCarga.map((d) => valCarga(a, d))}
          serieB={diasCarga.map((d) => valCarga(b, d))}
          labelA={labelA}
          labelB={labelB}
          unidade="UA"
        />
        <GraficoAgrupado
          titulo="PSE por dia (/10)"
          dias={diasPse}
          serieA={diasPse.map((d) => valPse(a, d))}
          serieB={diasPse.map((d) => valPse(b, d))}
          labelA={labelA}
          labelB={labelB}
          unidade="/10"
        />
      </div>
    </div>
  );
}

function GraficoAgrupado({
  titulo,
  dias,
  serieA,
  serieB,
  labelA,
  labelB,
  unidade,
}: {
  titulo: string;
  dias: string[];
  serieA: (number | null)[];
  serieB: (number | null)[];
  labelA: string;
  labelB: string;
  unidade: string;
}) {
  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
      <div className="font-display" style={{ fontSize: "0.86rem", fontWeight: 700, color: "white", marginBottom: espaco.sm }}>
        {titulo}
      </div>
      {dias.length === 0 ? (
        <p style={{ color: cores.textoSuave, fontSize: "0.85rem" }}>Sem dados.</p>
      ) : (
        <PlotlyChart
          data={[
            { x: dias, y: serieA, type: "bar", name: labelA, marker: { color: COR_A }, hovertemplate: `${labelA} · %{x}<br>%{y} ${unidade}<extra></extra>` },
            { x: dias, y: serieB, type: "bar", name: labelB, marker: { color: COR_B }, hovertemplate: `${labelB} · %{x}<br>%{y} ${unidade}<extra></extra>` },
          ]}
          layout={{
            barmode: "group",
            xaxis: { type: "category", categoryorder: "array", categoryarray: dias },
            yaxis: { title: { text: unidade } },
            legend: { orientation: "h", y: -0.25 },
            margin: { l: 44, r: 16, t: 12, b: 60 },
          }}
          altura={240}
        />
      )}
    </div>
  );
}

function DeltaCard({
  titulo,
  a,
  b,
  unidade,
  labelA,
  labelB,
  casas = 0,
}: {
  titulo: string;
  a: number | null;
  b: number | null;
  unidade: string;
  labelA: string;
  labelB: string;
  casas?: number;
}) {
  const delta = a !== null && b !== null && b !== 0 ? ((a - b) / b) * 100 : null;
  const fmt = (v: number | null) => (v === null ? "—" : v.toLocaleString("pt-PT", { maximumFractionDigits: casas }));
  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
      <div style={{ fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.04em", color: cores.textoSuave, marginBottom: 6 }}>{titulo}</div>
      <div style={{ display: "flex", alignItems: "baseline", gap: espaco.md }}>
        <span className="font-display" style={{ fontSize: "1.3rem", fontWeight: 800, color: COR_A }}>{fmt(a)}</span>
        <span style={{ color: cores.textoFraco }}>vs</span>
        <span className="font-display" style={{ fontSize: "1.3rem", fontWeight: 800, color: COR_B }}>{fmt(b)}</span>
        <span style={{ fontSize: "0.72rem", color: cores.textoSuave }}>{unidade}</span>
      </div>
      <div style={{ fontSize: "0.75rem", marginTop: 4, color: delta === null ? cores.textoFraco : delta >= 0 ? cores.cargaInterna : cores.sucesso, fontWeight: 700 }}>
        {delta === null ? "—" : `${delta >= 0 ? "▲" : "▼"} ${Math.abs(delta).toFixed(1)}%`}{" "}
        <span style={{ color: cores.textoSuave, fontWeight: 400 }}>{labelA} vs {labelB}</span>
      </div>
    </div>
  );
}
