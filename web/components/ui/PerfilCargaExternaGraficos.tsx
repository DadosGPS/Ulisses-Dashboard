"use client";

import { GraficoExpansivel } from "@/components/ui/GraficoExpansivel";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { espaco, raio } from "@/lib/theme";

interface Coluna {
  chave: string;
  label: string;
  cor: string;
  casas: number;
}

// Estilo de relatório (fundo branco) — cores com contraste ≥ 3:1 validado.
const COR_RELATORIO: Record<string, string> = {
  distancia_total_m: "#2563eb",
  hsr_m: "#d97706",
  sprint_m: "#dc2626",
  acc_n: "#0d9488",
  dcc_n: "#059669",
  vel_max_kmh: "#7c3aed",
};
const TINTA = "#1e293b";
const TINTA_SUAVE = "#334155";
const GRELHA = "#e2e8f0";
const layoutBranco = {
  paper_bgcolor: "#ffffff",
  plot_bgcolor: "#ffffff",
  font: { family: "Inter, Segoe UI, Arial, sans-serif", color: TINTA },
};

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
          <div key={c.chave} style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: raio.md, padding: espaco.md }}>
            <div className="font-display" style={{ fontSize: "0.86rem", fontWeight: 700, color: TINTA, marginBottom: espaco.sm }}>
              {c.label}
            </div>
            <GraficoExpansivel
              titulo={c.label}
              data={[
                {
                  x: ordenado.map((l) => l.valores[c.chave]),
                  y: ordenado.map((l) => nomeOuOculto(l.jogador, oculto)),
                  type: "bar",
                  orientation: "h",
                  marker: { color: COR_RELATORIO[c.chave] ?? c.cor },
                  text: ordenado.map((l) => (l.valores[c.chave] as number).toLocaleString("pt-PT", { maximumFractionDigits: c.casas })),
                  textposition: "outside",
                  textfont: { color: TINTA, size: 11 },
                  cliponaxis: false,
                },
              ]}
              layout={{
                ...layoutBranco,
                margin: { l: 120, r: 52, t: 10, b: 40 },
                xaxis: { title: { text: c.label }, gridcolor: GRELHA, tickfont: { size: 11, color: TINTA_SUAVE }, zeroline: false },
                yaxis: { tickfont: { size: 10, color: TINTA_SUAVE }, automargin: true },
              }}
              altura={Math.max(220, ordenado.length * 22)}
            />
          </div>
        );
      })}
    </div>
  );
}
