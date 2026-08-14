"use client";

import { useState } from "react";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { IconExpand, IconX } from "@/components/icons/Icons";
import { cores, espaco, raio } from "@/lib/theme";
import type { Data, Layout } from "plotly.js";

/** Wrapper que acrescenta um botão de expandir a qualquer PlotlyChart —
 * abre o mesmo gráfico maior, num overlay, para análise mais detalhada. */
export function GraficoExpansivel({
  titulo,
  data,
  layout,
  altura = 220,
}: {
  titulo: string;
  data: Data[];
  layout?: Partial<Layout>;
  altura?: number;
}) {
  const [expandido, setExpandido] = useState(false);

  return (
    <>
      <div style={{ position: "relative" }}>
        <button
          onClick={() => setExpandido(true)}
          title="Expandir gráfico"
          style={{
            position: "absolute",
            top: -4,
            right: 0,
            zIndex: 1,
            background: "transparent",
            border: "none",
            color: cores.textoSuave,
            cursor: "pointer",
            padding: 4,
          }}
        >
          <IconExpand size={14} />
        </button>
        <PlotlyChart data={data} layout={layout} altura={altura} />
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
              width: "min(1100px, 95vw)",
              maxHeight: "90vh",
              overflow: "auto",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: espaco.md }}>
              <div className="font-display" style={{ fontSize: "1rem", fontWeight: 700, color: "white" }}>
                {titulo}
              </div>
              <button
                onClick={() => setExpandido(false)}
                title="Fechar"
                style={{ background: "transparent", border: "none", color: cores.textoSuave, cursor: "pointer", padding: 4 }}
              >
                <IconX size={18} />
              </button>
            </div>
            <PlotlyChart data={data} layout={layout} altura={Math.max(altura * 2, 480)} />
          </div>
        </div>
      )}
    </>
  );
}
