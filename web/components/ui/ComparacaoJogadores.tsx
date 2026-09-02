"use client";

import { useState } from "react";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { cores, espaco, raio } from "@/lib/theme";

export interface MetricaDef {
  chave: string;
  label: string;
  unidade: string;
  cor: string;
  casas: number;
}

export interface JogadorResumo {
  jogador: string;
  posicao: string;
  n_sessoes: number;
  valores: Record<string, number | null>;
}

const MAX = 4;

/** Comparação lado a lado de até 4 jogadores, com dados reais. O gráfico
 * mostra cada métrica como % da média da equipa, para tornar comparáveis
 * métricas de escalas muito diferentes (distância vs Vmax). */
export function ComparacaoJogadores({
  metricas,
  jogadores,
  benchmark,
}: {
  metricas: MetricaDef[];
  jogadores: JogadorResumo[];
  benchmark: Record<string, number | null>;
}) {
  const { oculto } = usePrivacidade();
  const [selecionados, setSelecionados] = useState<string[]>(
    jogadores.slice(0, Math.min(3, jogadores.length)).map((j) => j.jogador)
  );

  const escolhidos = jogadores.filter((j) => selecionados.includes(j.jogador));
  const paleta = ["#2563eb", "#e63946", "#22c55e", "#f59e0b"];

  function alternar(nome: string) {
    setSelecionados((atual) => {
      if (atual.includes(nome)) return atual.filter((n) => n !== nome);
      if (atual.length >= MAX) return atual;
      return [...atual, nome];
    });
  }

  function estiloVsBench(valor: number | null, bench: number | null): React.CSSProperties {
    if (valor === null || bench === null || bench === 0) return { color: cores.textoFraco };
    const r = valor / bench;
    if (r >= 1.1) return { color: cores.cargaInterna, fontWeight: 700 };
    if (r <= 0.9) return { color: cores.info, fontWeight: 700 };
    return { color: cores.sucesso, fontWeight: 700 };
  }

  return (
    <div>
      {/* Seleção de jogadores */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: espaco.sm, marginBottom: espaco.lg }}>
        {jogadores.map((j) => {
          const ativo = selecionados.includes(j.jogador);
          const cheio = !ativo && selecionados.length >= MAX;
          return (
            <button
              key={j.jogador}
              onClick={() => alternar(j.jogador)}
              disabled={cheio}
              style={{
                background: ativo ? cores.destaque : cores.bgCartao,
                color: ativo ? "white" : cheio ? cores.textoFraco : cores.textoSuave,
                border: `1px solid ${ativo ? cores.destaque : cores.borda}`,
                borderRadius: raio.sm,
                padding: "6px 12px",
                fontSize: "0.8rem",
                fontWeight: 600,
                cursor: cheio ? "not-allowed" : "pointer",
              }}
            >
              {nomeOuOculto(j.jogador, oculto)} · {j.posicao}
            </button>
          );
        })}
      </div>

      {escolhidos.length === 0 ? (
        <p style={{ color: cores.textoSuave, fontSize: "0.9rem" }}>Seleciona pelo menos um jogador.</p>
      ) : (
        <>
          {/* Tabela comparativa */}
          <div
            style={{
              overflowX: "auto",
              border: `1px solid ${cores.borda}`,
              borderRadius: raio.md,
              background: cores.bgCartao,
              marginBottom: espaco.xxl,
            }}
          >
            <table style={{ width: "100%", borderCollapse: "collapse", fontVariantNumeric: "tabular-nums" }}>
              <thead>
                <tr style={{ background: "rgba(255,255,255,0.04)" }}>
                  <th style={th("left")}>Métrica</th>
                  <th style={th("center")}>Média Equipa</th>
                  {escolhidos.map((j, i) => (
                    <th key={j.jogador} style={{ ...th("center"), color: paleta[i % paleta.length] }}>
                      {nomeOuOculto(j.jogador, oculto)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {metricas.map((m) => (
                  <tr key={m.chave} style={{ borderTop: `1px solid ${cores.borda}` }}>
                    <td style={{ padding: "9px 14px", fontSize: "0.8rem", fontWeight: 600, color: "rgba(255,255,255,0.9)", whiteSpace: "nowrap" }}>
                      <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: 2, background: m.cor, marginRight: 8 }} />
                      {m.label} {m.unidade && <span style={{ color: cores.textoSuave, fontWeight: 400 }}>({m.unidade})</span>}
                    </td>
                    <td style={{ padding: "9px 14px", textAlign: "center", fontSize: "0.8rem", color: cores.textoSuave }}>
                      {fmt(benchmark[m.chave], m.casas)}
                    </td>
                    {escolhidos.map((j) => (
                      <td key={j.jogador} style={{ padding: "9px 14px", textAlign: "center", fontSize: "0.82rem", ...estiloVsBench(j.valores[m.chave], benchmark[m.chave]) }}>
                        {fmt(j.valores[m.chave], m.casas)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Gráfico: % da média da equipa */}
          <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
            <div className="font-display" style={{ fontSize: "0.86rem", fontWeight: 700, color: "white", marginBottom: espaco.sm }}>
              Perfil vs média da equipa (100% = média)
            </div>
            <PlotlyChart
              data={escolhidos.map((j, i) => ({
                x: metricas.map((m) => m.label),
                y: metricas.map((m) => {
                  const v = j.valores[m.chave];
                  const b = benchmark[m.chave];
                  return v !== null && b && b !== 0 ? Math.round((v / b) * 100) : null;
                }),
                type: "bar",
                name: nomeOuOculto(j.jogador, oculto),
                marker: { color: paleta[i % paleta.length] },
                hovertemplate: `%{x}<br>%{y}% da média<extra>${nomeOuOculto(j.jogador, oculto)}</extra>`,
              }))}
              layout={{
                barmode: "group",
                yaxis: { title: { text: "% da média" }, ticksuffix: "%" },
                shapes: [
                  { type: "line", x0: -0.5, x1: metricas.length - 0.5, y0: 100, y1: 100, line: { color: "rgba(255,255,255,0.4)", width: 1, dash: "dot" } },
                ],
                legend: { orientation: "h", y: -0.2 },
                margin: { l: 50, r: 20, t: 10, b: 80 },
              }}
              altura={320}
            />
          </div>

          <p style={{ color: cores.textoSuave, fontSize: "0.75rem", marginTop: espaco.md }}>
            <span style={{ color: cores.cargaInterna }}>●</span> acima da média &nbsp;
            <span style={{ color: cores.sucesso }}>●</span> em linha &nbsp;
            <span style={{ color: cores.info }}>●</span> abaixo — descritivo, não é uma nota de qualidade.
          </p>
        </>
      )}
    </div>
  );
}

function fmt(v: number | null, casas: number): string {
  return v === null || v === undefined ? "—" : v.toLocaleString("pt-PT", { maximumFractionDigits: casas });
}

function th(align: "left" | "center"): React.CSSProperties {
  return {
    padding: "10px 14px",
    fontSize: "0.64rem",
    letterSpacing: "0.06em",
    textTransform: "uppercase",
    color: cores.textoSuave,
    textAlign: align,
    whiteSpace: "nowrap",
  };
}
