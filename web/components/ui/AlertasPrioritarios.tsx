"use client";

import { NomeJogador } from "@/components/ui/NomeJogador";
import { cores, espaco, raio } from "@/lib/theme";
import type { AlertaPrioritario, JogadorIndisponivel } from "@/lib/types";
import { useTr } from "@/lib/i18n/cliente";
import type { Tr } from "@/lib/i18n/core";

const LABEL_ESTADO: Record<string, string> = {
  lesionado: "Lesionado",
  em_recuperacao: "Em recuperação",
  ausente: "Ausente",
};

/** Junta ACWR + wellness num único sinal "quem precisa de atenção hoje" —
 * antes disto era preciso cruzar manualmente a página Equipa com a Jogadores. */
export function AlertasPrioritarios({
  prioritarios,
  indisponiveis,
}: {
  prioritarios: AlertaPrioritario[];
  indisponiveis: JogadorIndisponivel[];
}) {
  const tr = useTr();
  if (prioritarios.length === 0 && indisponiveis.length === 0) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: espaco.sm, marginBottom: espaco.xxl }}>
      {prioritarios.length > 0 && (
        <div
          style={{
            background: cores.bgCartao,
            border: `1px solid ${cores.borda}`,
            borderLeft: `3px solid ${cores.perigo}`,
            borderRadius: raio.md,
            padding: espaco.md,
          }}
        >
          <div className="font-display" style={{ fontSize: "0.8rem", fontWeight: 700, color: cores.textoForte, marginBottom: espaco.sm }}>
            {tr("Precisam de atenção")}</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {prioritarios.map((a, i) => (
              <div
                key={`${a.jogador}-${a.tipo}-${i}`}
                style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "0.8rem" }}
              >
                <span style={{ color: "rgb(var(--ink) / 0.85)", fontWeight: 500 }}>
                  <NomeJogador nome={a.jogador} /> <span style={{ color: cores.textoFraco }}>· {tr(a.tipo)}</span>
                </span>
                <span style={{ fontWeight: 700 }}>
                  {a.estado}{" "}
                  {a.valor !== null && (
                    <span style={{ color: cores.textoSuave, fontWeight: 500 }}>({formatarValor(a.tipo, a.valor, tr)})</span>
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {indisponiveis.length > 0 && (
        <div
          style={{
            background: cores.bgCartao,
            border: `1px solid ${cores.borda}`,
            borderLeft: `3px solid ${cores.info}`,
            borderRadius: raio.md,
            padding: espaco.md,
          }}
        >
          <div className="font-display" style={{ fontSize: "0.8rem", fontWeight: 700, color: cores.textoForte, marginBottom: espaco.sm }}>
            {tr("Indisponíveis")}</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {indisponiveis.map((j) => (
              <div key={j.jogador} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "0.8rem" }}>
                <span style={{ color: "rgb(var(--ink) / 0.85)", fontWeight: 500 }}>
                  <NomeJogador nome={j.jogador} />
                </span>
                <span style={{ color: cores.textoSuave }}>
                  {tr(LABEL_ESTADO[j.estado] ?? j.estado)}
                  {j.motivo ? ` · ${j.motivo}` : ""}
                  {j.desde ? tr(" · desde {0}", [j.desde]) : ""}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function formatarValor(tipo: AlertaPrioritario["tipo"], valor: number, tr: Tr): string {
  if (tipo === "Dados") return tr("há {0} dias", [valor]);
  if (tipo === "Velocidade") return tr("{0}% do recorde", [valor]);
  if (tipo === "PSE vs GPS") return `Δz ${valor}`;
  return String(valor);
}
