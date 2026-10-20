"use client";

import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { cores, espaco, raio } from "@/lib/theme";
import type { VelocidadeResponse } from "@/lib/types";

/** Tabela de limiares de velocidade individuais — cada jogador tem os seus
 * limiares (km/h) ancorados na Vmáx dele, em vez de um valor igual para todos. */
export function PerfilVelocidade({ dados }: { dados: VelocidadeResponse }) {
  const { oculto } = usePrivacidade();
  const { metabolico, mecanico, sprint } = dados.limiares_pct;

  if (!dados.tem_dados) {
    return (
      <p style={{ color: cores.textoSuave, fontSize: "0.9rem" }}>
        Ainda não há velocidade máxima registada. Importa sessões de GPS com a coluna de velocidade máxima.
      </p>
    );
  }

  const cols: { chave: keyof VelocidadeResponse["jogadores"][number]; label: string; cor?: string; sufixo?: string }[] = [
    { chave: "mss_kmh", label: "Vmáx (MSS)", sufixo: " km/h" },
    { chave: "limiar_metabolico_kmh", label: `HSR metabólico (${metabolico}%)`, cor: "#0d9488", sufixo: " km/h" },
    { chave: "limiar_mecanico_kmh", label: `HSR mecânico (${mecanico}%)`, cor: "#d97706", sufixo: " km/h" },
    { chave: "limiar_sprint_kmh", label: `Sprint (${sprint}%)`, cor: "#dc2626", sufixo: " km/h" },
  ];

  return (
    <div>
      {/* Nota científica + referência absoluta */}
      <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md, marginBottom: espaco.lg, fontSize: "0.82rem", color: cores.texto, lineHeight: 1.5 }}>
        Limiares ancorados na <strong>velocidade máxima individual (MSS/Vmáx)</strong> de cada jogador:
        HSR metabólico a <strong>{metabolico}%</strong>, HSR mecânico a <strong>{mecanico}%</strong> e sprint a <strong>{sprint}%</strong> da Vmáx.
        Referência absoluta clássica (igual para todos): HSR &gt; {dados.referencia_absoluta.hsr} km/h · Sprint &gt; {dados.referencia_absoluta.sprint} km/h.
      </div>

      <div style={{ overflowX: "auto", background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.84rem" }}>
          <thead>
            <tr style={{ borderBottom: `1px solid ${cores.borda}` }}>
              <th style={thEsq}>Jogador</th>
              <th style={thEsq}>Posição</th>
              {cols.map((c) => (
                <th key={String(c.chave)} style={{ ...thDir, color: c.cor ?? cores.textoSuave }}>{c.label}</th>
              ))}
              <th style={thDir} title="Sessões em que o pico de velocidade atingiu o limiar de sprint individual">
                Sessões c/ sprint (dele)
              </th>
            </tr>
          </thead>
          <tbody>
            {dados.jogadores.map((j) => (
              <tr key={j.jogador} style={{ borderBottom: `1px solid ${cores.borda}` }}>
                <td style={{ ...tdEsq, fontWeight: 600, color: "white" }}>{nomeOuOculto(j.jogador, oculto)}</td>
                <td style={{ ...tdEsq, color: cores.textoSuave }}>{j.posicao}</td>
                {cols.map((c) => {
                  const v = j[c.chave] as number | null;
                  return (
                    <td key={String(c.chave)} style={{ ...tdDir, color: c.cor ?? "white", fontVariantNumeric: "tabular-nums" }}>
                      {v !== null ? `${v.toLocaleString("pt-PT")}${c.sufixo ?? ""}` : "—"}
                    </td>
                  );
                })}
                <td style={{ ...tdDir, color: "white", fontVariantNumeric: "tabular-nums" }}>
                  {j.n_sprint_individual}<span style={{ color: cores.textoSuave }}> / {j.n_sessoes}</span>
                  {j.pct_sprint_individual !== null && (
                    <span style={{ color: cores.textoSuave, fontSize: "0.75rem" }}> ({j.pct_sprint_individual}%)</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p style={{ color: cores.textoSuave, fontSize: "0.76rem", marginTop: espaco.md, lineHeight: 1.5 }}>
        Nota: os metros de HSR/Sprint importados são calculados pelo GPS num limiar fixo. Estes limiares
        individualizam a <em>leitura</em> (km/h por jogador e classificação por pico de velocidade). Para
        recalcular os <em>metros</em> de HSR/Sprint por jogador é preciso exportar a distância por banda de velocidade.
      </p>
    </div>
  );
}

const thEsq: React.CSSProperties = { textAlign: "left", padding: "10px 12px", fontSize: "0.72rem", textTransform: "uppercase", letterSpacing: "0.03em", color: cores.textoSuave, fontWeight: 600 };
const thDir: React.CSSProperties = { ...thEsq, textAlign: "right" };
const tdEsq: React.CSSProperties = { textAlign: "left", padding: "9px 12px" };
const tdDir: React.CSSProperties = { textAlign: "right", padding: "9px 12px" };
