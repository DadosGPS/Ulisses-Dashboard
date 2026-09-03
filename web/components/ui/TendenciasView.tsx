"use client";

import { useMemo, useState } from "react";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { cores, espaco, raio } from "@/lib/theme";

export interface MetricaDef {
  chave: string;
  label: string;
  unidade: string;
  cor: string;
  casas: number;
}

type Ponto = { data: string; valor: number | null };

const JANELAS = [
  { dias: 7, label: "7 dias" },
  { dias: 14, label: "14 dias" },
  { dias: 28, label: "28 dias" },
  { dias: 0, label: "Época" },
];

/** Análise de tendências por métrica — média móvel de 7 sessões, estatísticas
 * da janela e variação semana-a-semana. Reutiliza a série de evolução da
 * equipa devolvida pelo endpoint de carga externa. */
export function TendenciasView({
  metricas,
  evolucao,
}: {
  metricas: MetricaDef[];
  evolucao: Record<string, Ponto[]>;
}) {
  const [janela, setJanela] = useState(28);

  const estilo: React.CSSProperties = {
    background: cores.bgCartao,
    border: `1px solid ${cores.bordaForte}`,
    borderRadius: raio.sm,
    color: "white",
    padding: "6px 10px",
    fontSize: "0.8rem",
    fontWeight: 600,
    cursor: "pointer",
  };

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: espaco.sm, marginBottom: espaco.lg }}>
        <span style={{ fontSize: "0.75rem", color: cores.textoSuave }}>Janela</span>
        {JANELAS.map((j) => (
          <button
            key={j.dias}
            onClick={() => setJanela(j.dias)}
            style={{ ...estilo, background: janela === j.dias ? cores.destaque : cores.bgCartao, borderColor: janela === j.dias ? cores.destaque : cores.bordaForte }}
          >
            {j.label}
          </button>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: espaco.lg }}>
        {metricas.map((m) => (
          <CartaoTendencia key={m.chave} metrica={m} pontos={evolucao[m.chave] ?? []} janelaDias={janela} />
        ))}
      </div>
    </div>
  );
}

function CartaoTendencia({ metrica, pontos, janelaDias }: { metrica: MetricaDef; pontos: Ponto[]; janelaDias: number }) {
  const dados = useMemo(() => {
    const validos = pontos.filter((p): p is { data: string; valor: number } => p.valor !== null && p.valor !== undefined);
    if (validos.length === 0) return null;

    let janela = validos;
    if (janelaDias > 0) {
      const ultima = new Date(validos[validos.length - 1].data).getTime();
      const corte = ultima - janelaDias * 24 * 3600 * 1000;
      janela = validos.filter((p) => new Date(p.data).getTime() >= corte);
    }
    if (janela.length === 0) return null;

    const vals = janela.map((p) => p.valor);
    const media = vals.reduce((a, b) => a + b, 0) / vals.length;
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    const desvio = Math.sqrt(vals.reduce((a, b) => a + (b - media) ** 2, 0) / vals.length);

    // Média móvel de 7 sessões (trailing).
    const rolling = janela.map((p, i) => {
      const jan = janela.slice(Math.max(0, i - 6), i + 1).map((q) => q.valor);
      return jan.reduce((a, b) => a + b, 0) / jan.length;
    });

    // Variação semana-a-semana (últimos 7 vs 7 anteriores).
    let deltaSemana: number | null = null;
    if (janela.length >= 4) {
      const ult7 = vals.slice(-7);
      const ant7 = vals.slice(-14, -7);
      if (ant7.length > 0) {
        const mu = ult7.reduce((a, b) => a + b, 0) / ult7.length;
        const ma = ant7.reduce((a, b) => a + b, 0) / ant7.length;
        if (ma !== 0) deltaSemana = ((mu - ma) / ma) * 100;
      }
    }

    return { janela, rolling, media, min, max, desvio, deltaSemana };
  }, [pontos, janelaDias]);

  const casas = metrica.casas;
  const fmt = (v: number | null) => (v === null ? "—" : v.toLocaleString("pt-PT", { maximumFractionDigits: casas }));

  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: espaco.sm }}>
        <div className="font-display" style={{ fontSize: "0.86rem", fontWeight: 700, color: "white" }}>
          {metrica.label} <span style={{ color: cores.textoSuave, fontWeight: 500 }}>({metrica.unidade})</span>
        </div>
        {dados?.deltaSemana != null && (
          <span style={{ fontSize: "0.78rem", fontWeight: 700, color: dados.deltaSemana >= 0 ? cores.hsr : cores.sucesso }}>
            {dados.deltaSemana >= 0 ? "▲" : "▼"} {Math.abs(dados.deltaSemana).toFixed(1)}% <span style={{ color: cores.textoSuave, fontWeight: 400 }}>vs semana ant.</span>
          </span>
        )}
      </div>

      {dados ? (
        <>
          <PlotlyChart
            data={[
              {
                x: dados.janela.map((p) => p.data),
                y: dados.janela.map((p) => p.valor),
                type: "bar",
                marker: { color: `${metrica.cor}55` },
                name: "Sessão",
                hovertemplate: `%{x|%d/%m}<br>${metrica.label}: %{y} ${metrica.unidade}<extra></extra>`,
              },
              {
                x: dados.janela.map((p) => p.data),
                y: dados.rolling,
                type: "scatter",
                mode: "lines",
                line: { color: metrica.cor, width: 2.5, shape: "spline" },
                name: "Média móvel (7)",
                hovertemplate: `%{x|%d/%m}<br>Média móvel: %{y:.${casas}f} ${metrica.unidade}<extra></extra>`,
              },
            ]}
            layout={{
              xaxis: { type: "date", title: { text: "" } },
              yaxis: { title: { text: metrica.unidade } },
              showlegend: false,
            }}
            altura={190}
          />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: espaco.xs, marginTop: espaco.sm }}>
            <Stat label="Média" valor={fmt(dados.media)} />
            <Stat label="Mín" valor={fmt(dados.min)} />
            <Stat label="Máx" valor={fmt(dados.max)} />
            <Stat label="Desvio" valor={fmt(dados.desvio)} />
          </div>
        </>
      ) : (
        <p style={{ color: cores.textoSuave, fontSize: "0.85rem", padding: `${espaco.md}px 0` }}>Sem dados nesta janela.</p>
      )}
    </div>
  );
}

function Stat({ label, valor }: { label: string; valor: string }) {
  return (
    <div style={{ textAlign: "center", background: cores.bg, borderRadius: raio.sm, padding: "6px 4px" }}>
      <div style={{ fontSize: "0.62rem", color: cores.textoSuave, textTransform: "uppercase", letterSpacing: "0.04em" }}>{label}</div>
      <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "white", fontVariantNumeric: "tabular-nums" }}>{valor}</div>
    </div>
  );
}
