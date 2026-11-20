"use client";

/** Carga da semana face ao NORMAL de cada jogador (média das 4–6 semanas
 * anteriores dele). Substitui a lista de ACWR: descreve uma mudança — uma
 * subida grande é motivo para conversar com o jogador e o treinador, não uma
 * previsão de lesão. Barra divergente à volta de 0 %: azul/laranja acima,
 * violeta abaixo; cinzento quando está dentro da variação habitual dele. */
import { NomeJogador } from "@/components/ui/NomeJogador";
import { cores, desvio, espaco, estado, raio } from "@/lib/theme";
import type { SemanaNormalJogador } from "@/lib/types";
import { useTr } from "@/lib/i18n/cliente";

function corDe(d: SemanaNormalJogador, alto: number, muito: number): string {
  if (d.variacao_pct == null) return cores.textoFraco;
  if (d.estado === "alto") return d.variacao_pct >= muito ? estado.agir : d.variacao_pct >= alto ? estado.vigiar : desvio.acima;
  if (d.estado === "baixo") return desvio.abaixo;
  return estado.normal;
}

export function SemanaVsNormal({ dados, alto = 30, muito = 50 }: { dados: SemanaNormalJogador[]; alto?: number; muito?: number }) {
  const tr = useTr();
  if (dados.length === 0) {
    return <p style={{ color: cores.textoSuave, fontSize: "0.85rem" }}>{tr("Sem dados de carga interna.")}</p>;
  }
  const escala = Math.max(60, ...dados.map((d) => Math.abs(d.variacao_pct ?? 0)));
  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
      {dados.map((d) => {
        const cor = corDe(d, alto, muito);
        const v = d.variacao_pct;
        const larg = v == null ? 0 : (Math.min(Math.abs(v), escala) / escala) * 50;
        return (
          <div key={d.jogador} data-testid="semana-normal-linha" style={{ display: "flex", alignItems: "center", gap: espaco.sm, padding: "6px 4px" }}>
            <div style={{ width: 110, fontSize: "0.76rem", color: "rgb(var(--ink) / 0.85)", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              <NomeJogador nome={d.jogador} ficha />
            </div>
            <div style={{ width: 40, fontSize: "0.66rem", color: cores.textoFraco }}>{d.posicao}</div>
            <div style={{ flex: 1, background: "rgb(var(--ink) / 0.06)", borderRadius: 6, height: 16, position: "relative", overflow: "hidden" }}
              title={d.normal != null ? tr("{0} UA esta semana · normal dele {1} UA ({2} semanas)", [d.semana, d.normal, d.n_semanas]) : tr("Precisa de 4 semanas de histórico")}>
              <div style={{ position: "absolute", left: "50%", top: 0, bottom: 0, width: 1, background: cores.borda }} />
              {v != null && (
                <div style={{ position: "absolute", top: 0, bottom: 0, background: cor, borderRadius: 4,
                  left: v >= 0 ? "50%" : `${50 - larg}%`, width: `${larg}%` }} />
              )}
            </div>
            <div style={{ minWidth: 52, textAlign: "right", fontSize: "0.76rem", fontWeight: 700, color: cor }}>
              {v == null ? "—" : `${v > 0 ? "+" : ""}${v}%`}
            </div>
          </div>
        );
      })}
    </div>
  );
}
