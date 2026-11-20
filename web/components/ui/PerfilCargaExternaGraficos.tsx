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

/** Uma métrica, um gráfico — barras horizontais por jogador, do maior (em
 * cima) para o menor, com um traço na média DELE nas sessões equivalentes
 * (o mesmo Dia MD; as outras semanas no modo semana): vê-se num relance quem
 * carregou mais e quem ficou acima ou abaixo do seu normal. */
export function PerfilCargaExternaGraficos({
  colunas,
  linhas,
  mediaLabel,
}: {
  colunas: Coluna[];
  linhas: { jogador: string; valores: Record<string, number | null>; medias?: Record<string, number | null> }[];
  mediaLabel?: string | null;
}) {
  const tr = useTr();
  const { oculto } = usePrivacidade();
  const temMedias = linhas.some((l) => Object.values(l.medias ?? {}).some((v) => v != null));

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 440px), 1fr))", gap: espaco.lg }}>
        {colunas.map((c) => {
          const ordenado = [...linhas]
            .filter((l) => l.valores[c.chave] !== null && l.valores[c.chave] !== undefined)
            .sort((a, b) => (b.valores[c.chave] as number) - (a.valores[c.chave] as number));

          if (ordenado.length === 0) return null;
          const nomes = ordenado.map((l) => nomeOuOculto(l.jogador, oculto));
          const fmtv = (v: number) => v.toLocaleString(tr.loc, { maximumFractionDigits: c.casas });
          const medias = ordenado.map((l) => l.medias?.[c.chave] ?? null);
          const dicas = ordenado.map((l, i) => {
            const v = l.valores[c.chave] as number;
            const m = medias[i];
            if (m == null || m === 0) return `${fmtv(v)} ${unidade(c.chave)}`;
            const d = Math.round(((v - m) / m) * 100);
            return `${fmtv(v)} ${unidade(c.chave)}<br>${tr("média dele")}: ${fmtv(m)} (${d > 0 ? "+" : ""}${d}%)`;
          });
          const cor = COR_METRICA[c.chave] ?? c.cor;

          return (
            <div key={c.chave} style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
              <div className="font-display" style={{ fontSize: "0.86rem", fontWeight: 700, color: TINTA, marginBottom: espaco.sm }}>
                {tr(c.label)} <span style={{ fontWeight: 500, color: TINTA_SUAVE, fontSize: "0.74rem" }}>{unidade(c.chave)}</span>
              </div>
              <GraficoExpansivel
                titulo={tr(c.label)}
                data={[
                  {
                    y: nomes,
                    x: ordenado.map((l) => l.valores[c.chave]),
                    type: "bar",
                    orientation: "h",
                    marker: { color: cor },
                    text: ordenado.map((l) => fmtv(l.valores[c.chave] as number)),
                    textposition: "outside",
                    textfont: { color: TINTA, size: 10 },
                    cliponaxis: false,
                    customdata: dicas,
                    hovertemplate: "<b>%{y}</b><br>%{customdata}<extra></extra>",
                    name: tr(c.label),
                  },
                  ...(temMedias ? [{
                    y: nomes,
                    x: medias,
                    type: "scatter" as const,
                    mode: "markers" as const,
                    marker: { symbol: "line-ns-open", size: 18, color: TINTA, line: { width: 2.5, color: TINTA } },
                    customdata: dicas,
                    hovertemplate: "<b>%{y}</b><br>%{customdata}<extra></extra>",
                    name: tr("média dele"),
                  }] : []),
                ]}
                layout={{
                  ...layoutBranco,
                  showlegend: false,
                  margin: { l: 10, r: 44, t: 6, b: 24 },
                  bargap: 0.28,
                  yaxis: { autorange: "reversed", automargin: true, tickfont: { size: 11, color: TINTA }, ticksuffix: "  " },
                  xaxis: { gridcolor: GRELHA, tickfont: { size: 10, color: TINTA_SUAVE }, zeroline: false, rangemode: "tozero" },
                }}
                altura={Math.max(220, ordenado.length * 24 + 40)}
              />
            </div>
          );
        })}
      </div>
      {temMedias && mediaLabel && (
        <p style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.76rem", color: TINTA_SUAVE, margin: `${espaco.sm}px 2px 0` }}>
          <span style={{ display: "inline-block", width: 2.5, height: 14, background: TINTA, borderRadius: 1 }} />
          {tr("Traço = {0}. Passa o rato por cima para ver a diferença em %.", [tr(mediaLabel)])}
        </p>
      )}
    </div>
  );
}
