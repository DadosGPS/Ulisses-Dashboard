"use client";

import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { cores, espaco, raio } from "@/lib/theme";

export interface LinhaCombinada {
  jogador: string;
  posicao: string;
  externo: number | null;
  interno: number | null;
  acwr: number | null;
  flag_ext: string;
  flag_int: string;
  flag: string;
}

interface Eixo { label: string; unidade: string }

function corQuadrante(extAlto: boolean, intAlto: boolean): string {
  if (extAlto && intAlto) return cores.cargaInterna; // muita carga total
  if (extAlto && !intAlto) return cores.atencao;     // externa alta, interna baixa
  if (!extAlto && intAlto) return cores.info;        // interna alta, externa baixa
  return cores.sucesso;                              // ambas baixas
}

/** Gráfico de quadrantes carga externa (x) × interna (y), com linhas na
 * mediana da equipa. Cada ponto é um jogador, colorido pelo quadrante. */
export function QuadranteCombinado({
  jogadores,
  medianaExterno,
  medianaInterno,
  eixoExterno,
  eixoInterno,
}: {
  jogadores: LinhaCombinada[];
  medianaExterno: number | null;
  medianaInterno: number | null;
  eixoExterno: Eixo;
  eixoInterno: Eixo;
}) {
  const { oculto } = usePrivacidade();
  const pts = jogadores.filter((j) => j.externo !== null && j.interno !== null);

  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
      <PlotlyChart
        titulo="Carga externa × interna"
        data={[
          {
            x: pts.map((p) => p.externo),
            y: pts.map((p) => p.interno),
            type: "scatter",
            mode: "text+markers",
            text: pts.map((p) => nomeOuOculto(p.jogador, oculto)),
            textposition: "top center",
            textfont: { size: 9, color: cores.textoSuave },
            marker: {
              size: 12,
              color: pts.map((p) => corQuadrante(p.flag_ext === "alto", p.flag_int === "alto")),
              line: { width: 1, color: "rgba(0,0,0,0.3)" },
            },
            hovertemplate: `%{text}<br>${eixoExterno.label}: %{x} ${eixoExterno.unidade}<br>${eixoInterno.label}: %{y} ${eixoInterno.unidade}<extra></extra>`,
          },
        ]}
        layout={{
          xaxis: { title: { text: `${eixoExterno.label} (${eixoExterno.unidade})` } },
          yaxis: { title: { text: `${eixoInterno.label} (${eixoInterno.unidade})` } },
          shapes: [
            ...(medianaExterno != null ? [{ type: "line" as const, x0: medianaExterno, x1: medianaExterno, yref: "paper" as const, y0: 0, y1: 1, line: { color: "rgba(255,255,255,0.25)", width: 1, dash: "dot" as const } }] : []),
            ...(medianaInterno != null ? [{ type: "line" as const, xref: "paper" as const, x0: 0, x1: 1, y0: medianaInterno, y1: medianaInterno, line: { color: "rgba(255,255,255,0.25)", width: 1, dash: "dot" as const } }] : []),
          ],
          margin: { l: 60, r: 20, t: 16, b: 50 },
        }}
        altura={380}
      />
      <div style={{ display: "flex", gap: espaco.lg, flexWrap: "wrap", marginTop: espaco.sm, fontSize: "0.72rem", color: cores.textoSuave }}>
        <span><span style={{ color: cores.cargaInterna }}>●</span> Ext↑ Int↑</span>
        <span><span style={{ color: cores.atencao }}>●</span> Ext↑ Int↓</span>
        <span><span style={{ color: cores.info }}>●</span> Ext↓ Int↑</span>
        <span><span style={{ color: cores.sucesso }}>●</span> Ext↓ Int↓</span>
        <span style={{ color: cores.textoFraco }}>linhas = mediana da equipa</span>
      </div>
    </div>
  );
}
