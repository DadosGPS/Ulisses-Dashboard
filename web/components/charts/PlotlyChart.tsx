"use client";

import dynamic from "next/dynamic";
import { plotlyLayoutBase } from "@/lib/theme";
import type { Data, Layout } from "plotly.js";

// Plotly acede a `window` — sem SSR, carregado só no browser.
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

export function PlotlyChart({
  data,
  layout,
  altura = 280,
}: {
  data: Data[];
  layout?: Partial<Layout>;
  altura?: number;
}) {
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
