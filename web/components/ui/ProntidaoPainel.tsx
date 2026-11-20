"use client";

import { cores, espaco, raio } from "@/lib/theme";
import { NomeJogador } from "@/components/ui/NomeJogador";
import { useTr } from "@/lib/i18n/cliente";

type ChaveItem = "sono" | "energia" | "dor_musc" | "stress" | "humor" | "prontidao" | "dor";

interface Wellness {
  data: string;
  dias_desde: number;
  itens: Partial<Record<ChaveItem, number>>;
  pode_treinar: boolean | null;
  local_dor: string | null;
}

interface JogadorProntidao {
  jogador: string;
  posicao: string;
  estado_jogador: string;
  wellness: Wellness | null;
}

export interface ProntidaoResponse {
  tem_dados: boolean;
  motivo: string | null;
  data_referencia?: string;
  cobertura?: { wellness_hoje?: number; total: number };
  jogadores: JogadorProntidao[];
}

/** Colunas do relatório de wellness, na ordem do formulário. Só aparecem as
 * que alguém respondeu. Escala da app: 1 = pior … 5 = melhor em todos. */
const ITENS: { chave: ChaveItem; label: string }[] = [
  { chave: "sono", label: "Sono" },
  { chave: "energia", label: "Energia" },
  { chave: "dor_musc", label: "Dor muscular" },
  { chave: "stress", label: "Stress" },
  { chave: "humor", label: "Humor" },
  { chave: "prontidao", label: "Prontidão para treinar" },
  { chave: "dor", label: "Dor" },
];

const ESTADO_JOGADOR: Record<string, string> = {
  lesionado: "lesionado",
  em_recuperacao: "em recuperação",
  ausente: "ausente",
};

/** Cor só nos valores baixos (1–2), para os saltar à vista; o resto fica neutro. */
function corValor(v: number): string | undefined {
  if (v <= 1) return cores.perigo;
  if (v <= 2) return cores.atencao;
  return undefined;
}

export function ProntidaoPainel({ dados }: { dados: ProntidaoResponse }) {
  const tr = useTr();
  const jogadores = [...dados.jogadores].sort((a, b) => {
    const da = a.wellness?.dias_desde ?? 9999;
    const db = b.wellness?.dias_desde ?? 9999;
    if ((da === 0) !== (db === 0)) return da === 0 ? -1 : 1; // quem respondeu hoje primeiro
    return String(a.jogador).localeCompare(String(b.jogador));
  });
  const colunas = ITENS.filter((i) => jogadores.some((j) => j.wellness?.itens[i.chave] != null));
  const temPode = jogadores.some((j) => j.wellness?.pode_treinar != null);
  const temLocal = jogadores.some((j) => j.wellness?.local_dor);
  const cob = dados.cobertura;

  return (
    <div>
      <p style={{ fontSize: "0.8rem", color: cores.textoSuave, margin: `0 0 ${espaco.md}px` }}>
        {cob?.wellness_hoje != null && (
          <>
            <span style={{ fontWeight: 600, color: cores.textoForte }}>{tr("Responderam hoje: {0} de {1}", [cob.wellness_hoje, cob.total])}</span>
            {" · "}
          </>
        )}
        {tr("Escala 1 = pior … 5 = melhor em todos os itens.")}
      </p>

      <div style={{ overflowX: "auto", background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md }}>
        <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 640 }}>
          <thead>
            <tr style={{ background: "rgb(var(--ink) / 0.04)" }}>
              <th style={th}>{tr("Jogador")}</th>
              <th style={th}>{tr("Resposta")}</th>
              {colunas.map((c) => (
                <th key={c.chave} style={{ ...th, textAlign: "center" }}>{tr(c.label)}</th>
              ))}
              {temPode && <th style={{ ...th, textAlign: "center" }}>{tr("Pode treinar")}</th>}
              {temLocal && <th style={th}>{tr("Local da dor")}</th>}
            </tr>
          </thead>
          <tbody>
            {jogadores.map((j) => {
              const w = j.wellness;
              const antiga = !w || w.dias_desde > 0;
              return (
                <tr key={j.jogador} style={{ borderTop: `1px solid ${cores.borda}` }}>
                  <td style={td}>
                    <span style={{ fontWeight: 600, color: cores.textoForte }}><NomeJogador nome={j.jogador} /></span>
                    {j.estado_jogador && j.estado_jogador !== "apto" && (
                      <span style={{ fontSize: "0.72rem", color: cores.textoSuave }}> · {tr(ESTADO_JOGADOR[j.estado_jogador] ?? j.estado_jogador)}</span>
                    )}
                  </td>
                  <td style={{ ...td, color: antiga ? cores.textoFraco : cores.textoSuave, whiteSpace: "nowrap", fontSize: "0.75rem" }}>
                    {!w ? tr("sem resposta") : w.dias_desde === 0 ? tr("hoje") : tr("há {0} d", [w.dias_desde])}
                  </td>
                  {colunas.map((c) => {
                    const v = w?.itens[c.chave];
                    const cor = v != null ? corValor(v) : undefined;
                    return (
                      <td key={c.chave} style={{ ...td, textAlign: "center", opacity: antiga ? 0.5 : 1 }}>
                        {v == null ? (
                          <span style={{ color: cores.textoFraco }}>—</span>
                        ) : (
                          <span style={{
                            display: "inline-block", minWidth: 26, padding: "2px 6px", borderRadius: 6, fontWeight: 700,
                            fontVariantNumeric: "tabular-nums", color: cor ?? cores.textoForte,
                            background: cor ? `color-mix(in srgb, ${cor} 15%, transparent)` : "transparent",
                          }}>{v.toLocaleString(tr.loc)}</span>
                        )}
                      </td>
                    );
                  })}
                  {temPode && (
                    <td style={{ ...td, textAlign: "center", opacity: antiga ? 0.5 : 1 }}>
                      {w?.pode_treinar == null ? (
                        <span style={{ color: cores.textoFraco }}>—</span>
                      ) : w.pode_treinar ? (
                        <span style={{ color: cores.textoForte }}>{tr("Sim")}</span>
                      ) : (
                        <span style={{ fontWeight: 700, color: cores.perigo }}>{tr("Não")}</span>
                      )}
                    </td>
                  )}
                  {temLocal && (
                    <td style={{ ...td, fontSize: "0.75rem", color: cores.textoSuave, opacity: antiga ? 0.5 : 1 }}>{w?.local_dor ?? "—"}</td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const th: React.CSSProperties = { textAlign: "left", padding: "9px 12px", fontSize: "0.62rem", letterSpacing: "0.06em", textTransform: "uppercase", color: cores.textoSuave, fontWeight: 600 };
const td: React.CSSProperties = { padding: "9px 12px", fontSize: "0.82rem", color: cores.texto, verticalAlign: "middle" };
