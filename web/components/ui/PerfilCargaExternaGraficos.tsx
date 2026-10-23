"use client";

import { GraficoExpansivel } from "@/components/ui/GraficoExpansivel";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { COR_METRICA, espaco, raio, cores } from "@/lib/theme";
import { useTr } from "@/lib/i18n/cliente";

interface Coluna {
  chave: string;
  label: string;
  cor: string;
  casas: number;
}

const UNIDADE: Record<string, string> = {
  distancia_total_m: "m", hsr_m: "m", sprint_m: "m", acc_n: "n", dcc_n: "n", vel_max_kmh: "km/h",
};
const unidade = (chave: string) => UNIDADE[chave] ?? "";
const TINTA = cores.texto;
const TINTA_SUAVE = cores.textoSuave;
const GRELHA = cores.borda;
const layoutBranco = {
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: { family: "Inter, Segoe UI, Arial, sans-serif", color: TINTA },
};

/** Uma métrica, um gráfico — colunas por jogador (nomes em baixo, valor na
 * vertical), do maior para o menor: quem carregou mais/menos num relance. */
export function PerfilCargaExternaGraficos({
  colunas,
  linhas,
}: {
  colunas: Coluna[];
  linhas: { jogador: string; valores: Record<string, number | null> }[];
}) {
  const tr = useTr();
  const { oculto } = usePrivacidade();

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 520px), 1fr))", gap: espaco.lg }}>
      {colunas.map((c) => {
        const ordenado = [...linhas]
          .filter((l) => l.valores[c.chave] !== null && l.valores[c.chave] !== undefined)
          .sort((a, b) => (b.valores[c.chave] as number) - (a.valores[c.chave] as number));

        if (ordenado.length === 0) return null;

        return (
          <div key={c.chave} style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
            <div className="font-display" style={{ fontSize: "0.86rem", fontWeight: 700, color: TINTA, marginBottom: espaco.sm }}>
              {tr(c.label)}
            </div>
            <GraficoExpansivel
              titulo={tr(c.label)}
              data={[
                {
                  x: ordenado.map((l) => nomeOuOculto(l.jogador, oculto)),
                  y: ordenado.map((l) => l.valores[c.chave]),
                  type: "bar",
                  marker: { color: COR_METRICA[c.chave] ?? c.cor },
                  text: ordenado.map((l) => (l.valores[c.chave] as number).toLocaleString(tr.loc, { maximumFractionDigits: c.casas })),
                  textposition: "outside",
                  textfont: { color: TINTA, size: ordenado.length > 18 ? 9 : 10 },
                  cliponaxis: false,
                  hovertemplate: `%{x}<br>%{y:,} ${unidade(c.chave)}<extra></extra>`,
                },
              ]}
              layout={{
                ...layoutBranco,
                margin: { l: 52, r: 12, t: 24, b: 10 },
                bargap: 0.25,
                xaxis: { tickfont: { size: 10, color: TINTA_SUAVE }, tickangle: -45, automargin: true },
                yaxis: { title: { text: unidade(c.chave) }, gridcolor: GRELHA, tickfont: { size: 11, color: TINTA_SUAVE }, zeroline: false, rangemode: "tozero" },
              }}
              altura={340}
            />
          </div>
        );
      })}
    </div>
  );
}
