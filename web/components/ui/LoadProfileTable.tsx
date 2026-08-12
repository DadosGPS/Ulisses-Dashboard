import { NomeJogador } from "@/components/ui/NomeJogador";
import { alphaHex, cores, raio } from "@/lib/theme";

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

/** Porta de tabela_carga_colorida() em utils/ui_safe.py — heatmap por linha/coluna.
 * Reutilizável para qualquer tabela "entidade × métrica" (jogadores, dias MD, ...). */
export function LoadProfileTable({
  colunas,
  linhas,
  labelLinha = "Jogador",
}: {
  colunas: ColunaCarga[];
  linhas: LinhaCarga[];
  labelLinha?: string;
}) {
  if (linhas.length === 0 || colunas.length === 0) return null;

  const ranges = Object.fromEntries(
    colunas.map((c) => {
      const vals = linhas.map((l) => l.valores[c.chave]).filter((v): v is number => v !== null && v !== undefined);
      return [c.chave, vals.length ? [Math.min(...vals), Math.max(...vals)] : [0, 1]];
    })
  ) as Record<string, [number, number]>;

  return (
    <div
      style={{
        overflowX: "auto",
        border: `1px solid ${cores.borda}`,
        borderRadius: raio.md,
        background: cores.bgCartao,
      }}
    >
      <table style={{ width: "100%", borderCollapse: "collapse", fontVariantNumeric: "tabular-nums" }}>
        <thead>
          <tr style={{ background: "rgba(255,255,255,0.04)" }}>
            <th style={thStyle("left")}>{labelLinha}</th>
            {colunas.map((c) => (
              <th key={c.chave} style={thStyle("center")}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {linhas.map((linha) => (
            <tr key={linha.jogador}>
              <td
                style={{
                  padding: "8px 14px",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  color: "rgba(255,255,255,0.9)",
                  whiteSpace: "nowrap",
                }}
              >
                <NomeJogador nome={linha.jogador} />
              </td>
              {colunas.map((c) => {
                const v = linha.valores[c.chave];
                if (v === null || v === undefined) {
                  return (
                    <td key={c.chave} style={{ padding: "6px 8px", textAlign: "center", color: cores.textoFraco }}>
                      —
                    </td>
                  );
                }
                const [lo, hi] = ranges[c.chave];
                const pct = hi > lo ? (v - lo) / (hi - lo) : 0.5;
                const alpha = 0.18 + pct * 0.55;
                return (
                  <td key={c.chave} style={{ padding: "6px 8px", textAlign: "center" }}>
                    <span
                      style={{
                        display: "inline-block",
                        minWidth: 58,
                        padding: "5px 10px",
                        borderRadius: 14,
                        background: `${c.cor}${alphaHex(alpha)}`,
                        color: "white",
                        fontWeight: 700,
                        fontSize: "0.75rem",
                      }}
                    >
                      {v.toLocaleString("pt-PT", { maximumFractionDigits: c.casas ?? 0 })}
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

function thStyle(align: "left" | "center"): React.CSSProperties {
  return {
    padding: "10px 12px",
    fontSize: "0.64rem",
    letterSpacing: "0.06em",
    textTransform: "uppercase",
    color: cores.textoSuave,
    textAlign: align,
    whiteSpace: "nowrap",
  };
}
