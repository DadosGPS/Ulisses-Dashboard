"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { IconExpand, IconX } from "@/components/icons/Icons";
import { cores, espaco, raio, plotlyLayoutBase } from "@/lib/theme";
import type { Data, Layout } from "plotly.js";

// Plotly acede a `window` — sem SSR, carregado só no browser.
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

function Grafico({ data, layout, altura }: { data: Data[]; layout?: Partial<Layout>; altura: number }) {
  return (
    <Plot
      data={data}
      layout={{ ...plotlyLayoutBase, height: altura, ...layout } as Partial<Layout>}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: "100%" }}
      useResizeHandler
    />
  );
}

/**
 * Gráfico Plotly com botão de ampliar embutido — clicar abre o mesmo gráfico
 * maior, num overlay. Passar `expansivel={false}` desliga (ex: quando o
 * chamador já fornece o seu próprio expandir, como o GraficoExpansivel).
 */
export function PlotlyChart({
  data,
  layout,
  altura = 280,
  expansivel = true,
  titulo,
}: {
  data: Data[];
  layout?: Partial<Layout>;
  altura?: number;
  expansivel?: boolean;
  titulo?: string;
}) {
  const [expandido, setExpandido] = useState(false);

  if (!expansivel) {
    return <Grafico data={data} layout={layout} altura={altura} />;
  }

  return (
    <>
      <div style={{ position: "relative" }}>
        <button
          onClick={() => setExpandido(true)}
          title="Ver em grande"
          aria-label="Ver gráfico em grande"
          style={{
            position: "absolute",
            top: -2,
            right: 0,
            zIndex: 1,
            background: "transparent",
            border: "none",
            color: cores.textoSuave,
            cursor: "pointer",
            padding: 4,
          }}
        >
          <IconExpand size={15} />
        </button>
        <Grafico data={data} layout={layout} altura={altura} />
      </div>

      {expandido && (
        <div
          onClick={() => setExpandido(false)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.75)",
            zIndex: 1000,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: espaco.xl,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: cores.bgCartao,
              border: `1px solid ${cores.borda}`,
              borderRadius: raio.md,
              padding: espaco.lg,
              width: "min(1200px, 96vw)",
              maxHeight: "92vh",
              overflow: "auto",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: espaco.md }}>
              <div className="font-display" style={{ fontSize: "1rem", fontWeight: 700, color: "white" }}>
                {titulo ?? "Gráfico"}
              </div>
              <button
                onClick={() => setExpandido(false)}
                title="Fechar"
                aria-label="Fechar"
                style={{ background: "transparent", border: "none", color: cores.textoSuave, cursor: "pointer", padding: 4 }}
              >
                <IconX size={18} />
              </button>
            </div>
            <Grafico data={data} layout={layout} altura={Math.max(altura * 2, 520)} />
          </div>
        </div>
      )}
    </>
  );
}
