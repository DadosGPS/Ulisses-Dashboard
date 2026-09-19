"use client";

import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { espaco, raio } from "@/lib/theme";
import type { PerfilResponse } from "@/lib/types";

const TINTA = "#1e293b";
const TINTA_SUAVE = "#334155";

// STEN 1–10, diverging à volta de 5.5: âmbar (abaixo da média da posição) →
// neutro → azul (acima). Azul/âmbar é seguro para daltonismo.
function corSten(sten: number | null): { bg: string; fg: string } {
  if (sten === null || sten === undefined) return { bg: "#f1f5f9", fg: "#94a3b8" };
  const t = Math.max(-1, Math.min(1, (sten - 5.5) / 4.5)); // -1 (=1) … +1 (=10)
  const lerp = (a: number, b: number, x: number) => Math.round(a + (b - a) * x);
  if (t >= 0) {
    const k = t;
    return { bg: `rgb(${lerp(255, 37, k)}, ${lerp(255, 99, k)}, ${lerp(255, 235, k)})`, fg: k > 0.55 ? "#ffffff" : TINTA };
  }
  const k = -t;
  return { bg: `rgb(${lerp(255, 217, k)}, ${lerp(255, 119, k)}, ${lerp(255, 6, k)})`, fg: k > 0.6 ? "#ffffff" : TINTA };
}

export function PerfilJogadores({ dados }: { dados: PerfilResponse }) {
  const { oculto } = usePrivacidade();

  if (!dados.tem_dados) {
    return (
      <p style={{ color: "#64748b", fontSize: "0.85rem" }}>
        Ainda não há testes importados. Adiciona a folha <strong>Testes_Neuromusculares</strong> ao ficheiro e reimporta.
      </p>
    );
  }

  return (
    <div style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: raio.md, padding: espaco.md }}>
      <p style={{ fontSize: "0.78rem", color: "#64748b", margin: `0 0 ${espaco.md}px` }}>
        Cada teste convertido em <strong>STEN (1–10)</strong> vs o plantel. Azul = acima da média da equipa · Âmbar = abaixo.
        Passa o rato para ver o valor real.
      </p>
      <div style={{ overflowX: "auto" }}>
        <table style={{ borderCollapse: "separate", borderSpacing: 2, fontSize: "0.8rem" }}>
          <thead>
            <tr>
              <th style={{ position: "sticky", left: 0, background: "#ffffff", zIndex: 1, textAlign: "left", padding: "6px 10px", fontSize: "0.72rem", color: TINTA_SUAVE, minWidth: 150 }}>
                Jogador · Posição
              </th>
              <th style={cabecalho}>STEN médio</th>
              {dados.metricas.map((m) => (
                <th key={m.chave} style={cabecalho} title={m.grupo}>{m.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dados.jogadores.map((j) => (
              <tr key={j.jogador}>
                <td style={{ position: "sticky", left: 0, background: "#ffffff", zIndex: 1, padding: "6px 10px", whiteSpace: "nowrap" }}>
                  <span style={{ fontWeight: 600, color: TINTA }}>{nomeOuOculto(j.jogador, oculto)}</span>
                  <span style={{ color: "#94a3b8", fontSize: "0.72rem" }}> · {j.posicao}</span>
                </td>
                {(() => {
                  const c = corSten(j.sten_medio);
                  return (
                    <td style={{ ...celula, background: c.bg, color: c.fg, fontWeight: 700 }}>
                      {j.sten_medio ?? "—"}
                    </td>
                  );
                })()}
                {dados.metricas.map((m) => {
                  const t = j.testes[m.chave];
                  const c = corSten(t?.sten ?? null);
                  return (
                    <td
                      key={m.chave}
                      title={t ? `${m.label}: ${t.valor}${m.unidade ? " " + m.unidade : ""} · STEN ${t.sten ?? "—"}` : "sem dados"}
                      style={{ ...celula, background: c.bg, color: c.fg }}
                    >
                      {t?.sten ?? "—"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p style={{ fontSize: "0.72rem", color: "#64748b", marginTop: espaco.sm }}>
        STEN = 5.5 + 2·z (escala 1–10). Referência: o plantel inteiro.
      </p>
    </div>
  );
}

const cabecalho: React.CSSProperties = { minWidth: 62, textAlign: "center", padding: "6px 4px", fontSize: "0.68rem", color: TINTA_SUAVE, fontWeight: 600, verticalAlign: "bottom" };
const celula: React.CSSProperties = { minWidth: 62, textAlign: "center", height: 30, borderRadius: 4 };
