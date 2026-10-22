"use client";

import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { espaco, raio, cores } from "@/lib/theme";
import type { PerfilResponse } from "@/lib/types";
import { useTr } from "@/lib/i18n/cliente";

const TINTA = cores.texto;
const TINTA_SUAVE = cores.textoSuave;

// STEN 1–10, diverging à volta de 5.5: âmbar (abaixo da média da posição) →
// neutro → azul (acima). Azul/âmbar é seguro para daltonismo.
function corSten(sten: number | null): { bg: string; fg: string } {
  if (sten === null || sten === undefined) return { bg: cores.superficie, fg: cores.textoFraco };
  const t = Math.max(-1, Math.min(1, (sten - 5.5) / 4.5)); // -1 (=1) … +1 (=10)
  const k = Math.abs(t);
  const cor = t >= 0 ? "rgb(37, 99, 235)" : "rgb(217, 119, 6)";
  const bg = `color-mix(in srgb, ${cor} ${Math.round(k * 100)}%, var(--bg-cartao))`;
  return { bg, fg: k > (t >= 0 ? 0.55 : 0.6) ? "#ffffff" : TINTA };
}

export function PerfilJogadores({ dados }: { dados: PerfilResponse }) {
  const tr = useTr();
  const { oculto } = usePrivacidade();

  if (!dados.tem_dados) {
    return (
      <p style={{ color: cores.textoSuave, fontSize: "0.85rem" }}>
        {tr("Ainda não há testes importados. Adiciona a folha")}{" "}<strong>{tr("Testes_Neuromusculares")}</strong> {tr("ao ficheiro e reimporta.")}</p>
    );
  }

  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
      <p style={{ fontSize: "0.78rem", color: cores.textoSuave, margin: `0 0 ${espaco.md}px` }}>
        {tr("Cada teste convertido em")}{" "}<strong>{tr("STEN (1–10)")}</strong> {tr("vs o plantel. Azul = acima da média da equipa · Âmbar = abaixo. Passa o rato para ver o valor real.")}</p>
      <div style={{ overflowX: "auto" }}>
        <table style={{ borderCollapse: "separate", borderSpacing: 2, fontSize: "0.8rem" }}>
          <thead>
            <tr>
              <th style={{ position: "sticky", left: 0, background: cores.bgCartao, zIndex: 1, textAlign: "left", padding: "6px 10px", fontSize: "0.72rem", color: TINTA_SUAVE, minWidth: 150 }}>
                {tr("Jogador · Posição")}</th>
              <th style={cabecalho}>{tr("STEN médio")}</th>
              {dados.metricas.map((m) => (
                <th key={m.chave} style={cabecalho} title={tr(m.grupo)}>{tr(m.label)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dados.jogadores.map((j) => (
              <tr key={j.jogador}>
                <td style={{ position: "sticky", left: 0, background: cores.bgCartao, zIndex: 1, padding: "6px 10px", whiteSpace: "nowrap" }}>
                  <span style={{ fontWeight: 600, color: TINTA }}>{nomeOuOculto(j.jogador, oculto)}</span>
                  <span style={{ color: cores.textoFraco, fontSize: "0.72rem" }}> · {j.posicao}</span>
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
                      title={t ? tr("{0}: {1}{2} · STEN {3}", [m.label, t.valor, m.unidade ? " " + m.unidade : "", t.sten ?? "—"]) : tr("sem dados")}
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
      <p style={{ fontSize: "0.72rem", color: cores.textoSuave, marginTop: espaco.sm }}>
        {tr("STEN = 5.5 + 2·z (escala 1–10). Referência: o plantel inteiro.")}</p>
    </div>
  );
}

const cabecalho: React.CSSProperties = { minWidth: 62, textAlign: "center", padding: "6px 4px", fontSize: "0.68rem", color: TINTA_SUAVE, fontWeight: 600, verticalAlign: "bottom" };
const celula: React.CSSProperties = { minWidth: 62, textAlign: "center", height: 30, borderRadius: 4 };
