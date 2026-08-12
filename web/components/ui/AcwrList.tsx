import { NomeJogador } from "@/components/ui/NomeJogador";
import { cores, espaco, raio } from "@/lib/theme";
import type { AcwrJogador } from "@/lib/types";

const COR_ESTADO: Record<string, string> = {
  RISCO: cores.perigo,
  "ATENÇÃO": cores.atencao,
  OK: cores.sucesso,
  "SUB-CARGA": cores.info,
};

function corDoEstado(estado: string): string {
  const chave = Object.keys(COR_ESTADO).find((k) => estado.includes(k));
  return chave ? COR_ESTADO[chave] : cores.textoSuave;
}

/** Lista ACWR por jogador — barra colorida por estado de risco, estilo BI/tabela densa. */
export function AcwrList({ dados }: { dados: AcwrJogador[] }) {
  if (dados.length === 0) {
    return <p style={{ color: cores.textoSuave, fontSize: "0.85rem" }}>Sem dados de ACWR disponíveis.</p>;
  }

  const maxAcwr = Math.max(...dados.map((d) => d.acwr ?? 0), 1.6);

  return (
    <div
      style={{
        background: cores.bgCartao,
        border: `1px solid ${cores.borda}`,
        borderRadius: raio.md,
        padding: espaco.md,
      }}
    >
      {dados.map((d) => {
        const cor = corDoEstado(d.estado);
        const largura = d.acwr !== null ? Math.min(100, (d.acwr / maxAcwr) * 100) : 0;
        return (
          <div key={d.jogador} style={{ display: "flex", alignItems: "center", gap: espaco.sm, padding: "6px 4px" }}>
            <div style={{ width: 110, fontSize: "0.76rem", color: "rgba(255,255,255,0.85)", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              <NomeJogador nome={d.jogador} />
            </div>
            <div style={{ width: 40, fontSize: "0.66rem", color: cores.textoFraco }}>{d.posicao}</div>
            <div style={{ flex: 1, background: "rgba(255,255,255,0.06)", borderRadius: 6, height: 16, position: "relative", overflow: "hidden" }}>
              <div style={{ width: `${largura}%`, height: "100%", background: cor, borderRadius: 6 }} />
            </div>
            <div style={{ minWidth: 44, textAlign: "right", fontSize: "0.76rem", fontWeight: 700, color: cor }}>
              {d.acwr !== null ? d.acwr.toFixed(2) : "—"}
            </div>
          </div>
        );
      })}
    </div>
  );
}
