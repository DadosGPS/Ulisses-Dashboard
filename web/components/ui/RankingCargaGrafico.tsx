"use client";

import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { cores, espaco, raio } from "@/lib/theme";

/** Ranking de atletas por carga em barras horizontais — leitura de 3 segundos
 * de quem carregou mais e menos. Substitui a tabela: numa barra vê-se logo a
 * distância entre atletas, que numa coluna de números passa despercebida. */
export function RankingCargaGrafico({
  linhas,
  label,
  unidade = "UA",
  cor = cores.cargaInterna,
}: {
  linhas: { jogador: string; valor: number }[];
  label: string;
  unidade?: string;
  cor?: string;
}) {
  const { oculto } = usePrivacidade();
  if (linhas.length === 0) {
    return <p style={{ color: cores.textoSuave, fontSize: "0.85rem" }}>Sem dados suficientes.</p>;
  }

  // Ordenar desc e inverter: em barras horizontais o Plotly desenha o primeiro
  // item em baixo, por isso o maior tem de ir no fim para aparecer no topo.
  const ordenadas = [...linhas].sort((a, b) => a.valor - b.valor);
  const nomes = ordenadas.map((l) => nomeOuOculto(l.jogador, oculto));
  const valores = ordenadas.map((l) => l.valor);

  // Altura adapta-se ao nº de atletas para as barras não ficarem esmagadas.
  const altura = Math.max(220, ordenadas.length * 26 + 60);

  return (
    <div style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: raio.md, padding: espaco.md }}>
      <PlotlyChart
        titulo={`Ranking — ${label}`}
        data={[
          {
            x: valores,
            y: nomes,
            type: "bar",
            orientation: "h",
            marker: { color: cor },
            text: valores.map((v) => v.toLocaleString("pt-PT")),
            textposition: "outside",
            textfont: { color: "#1e293b", size: 11 },
            cliponaxis: false,
            hovertemplate: `%{y}<br>%{x:,} ${unidade}<extra></extra>`,
          },
        ]}
        layout={{
          paper_bgcolor: "#ffffff",
          plot_bgcolor: "#ffffff",
          font: { family: "Inter, Segoe UI, Arial, sans-serif", color: "#1e293b" },
          xaxis: { title: { text: unidade }, zeroline: false, gridcolor: "#e2e8f0", tickfont: { size: 11, color: "#334155" } },
          yaxis: { type: "category", automargin: true, tickfont: { size: 11, color: "#334155" } },
          margin: { l: 8, r: 56, t: 16, b: 36 },
          bargap: 0.28,
        }}
        altura={altura}
      />
    </div>
  );
}
