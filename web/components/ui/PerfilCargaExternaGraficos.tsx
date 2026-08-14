"use client";

import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { cores, espaco, raio } from "@/lib/theme";

interface Coluna {
  chave: string;
  label: string;
  cor: string;
  casas: number;
}

/** Uma métrica, um gráfico — barras horizontais em vez da tabela densa
 * anterior, para leitura mais direta de quem carrega mais/menos por métrica. */
export function PerfilCargaExternaGraficos({
  colunas,
  linhas,
}: {
  colunas: Coluna[];
  linhas: { jogador: string; valores: Record<string, number | null> }[];
}) {
  const { oculto } = usePrivacidade();

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: espaco.lg }}>
      {colunas.map((c) => {
        const ordenado = [...linhas]
          .filter((l) => l.valores[c.chave] !== null && l.valores[c.chave] !== undefined)
          .sort((a, b) => (a.valores[c.chave] as number) - (b.valores[c.chave] as number));

        if (ordenado.length === 0) return null;

        return (
          <div key={c.chave} style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
            <div className="font-display" style={{ fontSize: "0.86rem", fontWeight: 700, color: "white", marginBottom: espaco.sm }}>
              {c.label}
            </div>
            <PlotlyChart
              data={[
                {
                  x: ordenado.map((l) => l.valores[c.chave]),
                  y: ordenado.map((l) => nomeOuOculto(l.jogador, oculto)),
                  type: "bar",
                  orientation: "h",
                  marker: { color: c.cor },
                  text: ordenado.map((l) => (l.valores[c.chave] as number).toLocaleString("pt-PT", { maximumFractionDigits: c.casas })),
                  textposition: "outside",
                },
              ]}
              layout={{
                margin: { l: 120, r: 40, t: 10, b: 40 },
                xaxis: { title: { text: c.label } },
                yaxis: { tickfont: { size: 10 } },
              }}
              altura={Math.max(220, ordenado.length * 22)}
            />
          </div>
        );
      })}
    </div>
  );
}
