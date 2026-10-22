"use client";

import { useState } from "react";
import { NomeJogador } from "@/components/ui/NomeJogador";
import { alphaHex, cores, raio } from "@/lib/theme";
import { useTr } from "@/lib/i18n/cliente";

export interface ColunaCarga {
  chave: string;
  label: string;
  cor: string;
  casas?: number;
}

export interface LinhaCarga {
  jogador: string;
  valores: Record<string, number | null>;
}

/** Tabela "entidade × métrica" (jogadores, posições…). Números simples; em
 * cada coluna só os extremos levam cor — os mais altos realçados na cor da
 * métrica, os mais baixos a cinzento — para o olho ir direto ao que importa.
 * Clicar num cabeçalho ordena por essa coluna. */
export function LoadProfileTable({
  colunas,
  linhas,
  labelLinha = "Jogador",
}: {
  colunas: ColunaCarga[];
  linhas: LinhaCarga[];
  labelLinha?: string;
}) {
  const tr = useTr();
  const [ordem, setOrdem] = useState<{ chave: string; desc: boolean } | null>(null);
  if (linhas.length === 0 || colunas.length === 0) return null;

  // Quantos extremos marcar por coluna: 3 com 10+ linhas, menos em tabelas curtas.
  const n = linhas.length >= 10 ? 3 : linhas.length >= 6 ? 2 : linhas.length >= 3 ? 1 : 0;
  const extremos = Object.fromEntries(
    colunas.map((c) => {
      const vals = linhas.map((l) => l.valores[c.chave]).filter((v): v is number => v !== null && v !== undefined).sort((x, y) => x - y);
      if (vals.length < 2 * n + 1 || n === 0) return [c.chave, null];
      return [c.chave, { alto: vals[vals.length - n], baixo: vals[n - 1] }];
    })
  ) as Record<string, { alto: number; baixo: number } | null>;

  const ordenadas = ordem
    ? [...linhas].sort((a, b) => {
        const va = a.valores[ordem.chave], vb = b.valores[ordem.chave];
        if (va == null) return 1;
        if (vb == null) return -1;
        return ordem.desc ? vb - va : va - vb;
      })
    : linhas;
  const clicar = (chave: string) => setOrdem(ordem?.chave === chave ? (ordem.desc ? { chave, desc: false } : null) : { chave, desc: true });

  return (
    <div style={{ overflowX: "auto", border: `1px solid ${cores.borda}`, borderRadius: raio.md, background: cores.bgCartao }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontVariantNumeric: "tabular-nums" }}>
        <thead>
          <tr style={{ borderBottom: `1px solid ${cores.borda}` }}>
            <th style={thStyle("left")}>{labelLinha}</th>
            {colunas.map((c) => {
              const ativa = ordem?.chave === c.chave;
              return (
                <th key={c.chave} className="lm-ordenar" onClick={() => clicar(c.chave)} aria-sort={ativa ? (ordem!.desc ? "descending" : "ascending") : "none"}
                  style={{ ...thStyle("right"), whiteSpace: "normal", lineHeight: 1.3, maxWidth: 96, color: ativa ? cores.textoForte : cores.textoSuave }}>
                  <span style={{ display: "inline-block", width: 6, height: 6, borderRadius: 2, background: c.cor, marginRight: 5, verticalAlign: "middle" }} />
                  {tr(c.label)}{ativa ? (ordem!.desc ? " ↓" : " ↑") : ""}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {ordenadas.map((linha, i) => (
            <tr key={linha.jogador} style={{ borderTop: i ? `1px solid ${cores.borda}` : "none" }}>
              <td style={{ padding: "8px 14px", fontSize: "0.8rem", fontWeight: 600, color: cores.textoForte, whiteSpace: "nowrap" }}>
                <NomeJogador nome={linha.jogador} />
              </td>
              {colunas.map((c) => {
                const v = linha.valores[c.chave];
                if (v === null || v === undefined) {
                  return <td key={c.chave} style={{ ...tdNum, color: cores.textoFraco }}>—</td>;
                }
                const e = extremos[c.chave];
                const alto = e != null && v >= e.alto;
                const baixo = e != null && !alto && v <= e.baixo;
                return (
                  <td key={c.chave} style={tdNum}>
                    <span style={{
                      display: "inline-block", padding: "2px 7px", borderRadius: 6,
                      background: alto ? `${c.cor}${alphaHex(0.22)}` : "transparent",
                      color: alto ? cores.textoForte : baixo ? cores.textoFraco : cores.texto,
                      fontWeight: alto ? 700 : 500,
                    }}>
                      {v.toLocaleString(tr.loc, { maximumFractionDigits: c.casas ?? 0 })}
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const tdNum: React.CSSProperties = { padding: "6px 8px", textAlign: "right", fontSize: "0.8rem" };

function thStyle(align: "left" | "right"): React.CSSProperties {
  return {
    padding: "10px 8px",
    fontSize: "0.62rem",
    letterSpacing: "0.05em",
    textTransform: "uppercase",
    color: cores.textoSuave,
    textAlign: align,
    whiteSpace: "nowrap",
    fontWeight: 600,
  };
}
