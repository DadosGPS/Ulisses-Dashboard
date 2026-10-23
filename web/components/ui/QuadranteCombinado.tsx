"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { cores, espaco, raio } from "@/lib/theme";
import { useTr } from "@/lib/i18n/cliente";

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
export interface OpcaoEixo extends Eixo { chave: string }

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
  eixos = [],
  eixo,
}: {
  jogadores: LinhaCombinada[];
  medianaExterno: number | null;
  medianaInterno: number | null;
  eixoExterno: Eixo;
  eixoInterno: Eixo;
  eixos?: OpcaoEixo[];
  eixo?: string;
}) {
  const tr = useTr();
  const router = useRouter();
  const caminho = usePathname();
  const params = useSearchParams();
  const mudarEixo = (chave: string) => {
    const q = new URLSearchParams(params.toString());
    q.set("eixo", chave);
    router.replace(`${caminho}?${q}`, { scroll: false });
  };
  const { oculto } = usePrivacidade();
  const pts = jogadores.filter((j) => j.externo !== null && j.interno !== null);

  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
      {eixos.length > 1 && (
        <div style={{ display: "flex", alignItems: "center", gap: espaco.sm, flexWrap: "wrap", marginBottom: espaco.sm }}>
          <span style={{ fontSize: "0.74rem", color: cores.textoSuave, fontWeight: 600 }}>{tr("Carga externa")}</span>
          <div role="radiogroup" aria-label={tr("Métrica de carga externa")} style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
            {eixos.map((e) => {
              const ativo = e.chave === eixo;
              return (
                <button key={e.chave} role="radio" aria-checked={ativo} onClick={() => !ativo && mudarEixo(e.chave)}
                  style={{
                    fontSize: "0.74rem", padding: "4px 10px", borderRadius: 999, cursor: ativo ? "default" : "pointer",
                    border: `1px solid ${ativo ? cores.acento : cores.bordaForte}`,
                    background: ativo ? `color-mix(in srgb, ${cores.acento} 14%, transparent)` : "transparent",
                    color: ativo ? cores.textoForte : cores.textoSuave, fontWeight: ativo ? 600 : 400,
                  }}>
                  {tr(e.label)}
                </button>
              );
            })}
          </div>
          {eixos.find((e) => e.chave === eixo)?.unidade.endsWith("/min") && (
            <span style={{ fontSize: "0.72rem", color: cores.textoFraco }}>{tr("por minuto compara-se com a PSE (intensidade com intensidade)")}</span>
          )}
        </div>
      )}
      <PlotlyChart
        titulo={tr("Carga externa × interna")}
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
            hovertemplate: tr("%{text}<br>{0}: %{x} {1}<br>{2}: %{y} {3}<extra></extra>", [tr(eixoExterno.label), eixoExterno.unidade, tr(eixoInterno.label), eixoInterno.unidade]),
          },
        ]}
        layout={{
          xaxis: { title: { text: `${tr(eixoExterno.label)} (${eixoExterno.unidade})` } },
          yaxis: { title: { text: `${tr(eixoInterno.label)} (${eixoInterno.unidade})` } },
          shapes: [
            ...(medianaExterno != null ? [{ type: "line" as const, x0: medianaExterno, x1: medianaExterno, yref: "paper" as const, y0: 0, y1: 1, line: { color: "rgb(var(--ink) / 0.25)", width: 1, dash: "dot" as const } }] : []),
            ...(medianaInterno != null ? [{ type: "line" as const, xref: "paper" as const, x0: 0, x1: 1, y0: medianaInterno, y1: medianaInterno, line: { color: "rgb(var(--ink) / 0.25)", width: 1, dash: "dot" as const } }] : []),
          ],
          margin: { l: 60, r: 20, t: 16, b: 50 },
        }}
        altura={380}
      />
      <div style={{ display: "flex", gap: espaco.lg, flexWrap: "wrap", marginTop: espaco.sm, fontSize: "0.72rem", color: cores.textoSuave }}>
        <span><span style={{ color: cores.cargaInterna }}>●</span> {tr("Ext↑ Int↑")}</span>
        <span><span style={{ color: cores.atencao }}>●</span> {tr("Ext↑ Int↓")}</span>
        <span><span style={{ color: cores.info }}>●</span> {tr("Ext↓ Int↑")}</span>
        <span><span style={{ color: cores.sucesso }}>●</span> {tr("Ext↓ Int↓")}</span>
        <span style={{ color: cores.textoFraco }}>{tr("linhas = mediana da equipa")}</span>
      </div>
    </div>
  );
}
