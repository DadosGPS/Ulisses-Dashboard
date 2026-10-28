"use client";

/** O que a equipa decidiu face a cada tipo de aviso e o que aconteceu a seguir
 * (lesão ou o mesmo aviso de novo nos 14 dias seguintes). Serve para calibrar
 * os limiares desta página com dados do próprio clube. */
import { useEffect, useState } from "react";
import { cores, espaco, raio } from "@/lib/theme";
import { SecaoTitulo, Vazio } from "@/components/ui/base";
import { pedidoApi } from "@/lib/api-cliente";
import { useTr } from "@/lib/i18n/cliente";

type Linha = {
  sinal: string; n: number; por_decisao: Record<string, number>;
  em_seguimento: number; fechadas: number; lesao_seguinte: number; repetido: number;
};
type Resumo = { disponivel: boolean; motivo: string | null; seguimento_dias: number; total: number; sinais: Linha[] };

const NOME_SINAL: Record<string, string> = {
  acwr: "ACWR elevado", vmax: "Pouco estímulo de velocidade", hooper: "Bem-estar abaixo do habitual", cmj: "Queda do CMJ",
  hsr_baixo: "Exposição HSR baixa", hsr_alto: "Exposição HSR elevada", sprint_baixo: "Exposição Sprint baixa",
  sprint_alto: "Exposição Sprint elevada", sem_dados: "Sem dados recentes", pse_gps: "PSE e GPS em sentidos opostos",
  habitual_hsr: "HSR acima do habitual", habitual_sprint: "Sprint acima do habitual", "habitual_distância": "Distância acima do habitual",
};

export function ResumoDecisoes({ teamId }: { teamId: string }) {
  const tr = useTr();
  const [dados, setDados] = useState<Resumo | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  useEffect(() => {
    pedidoApi<Resumo>(`/api/teams/${teamId}/decisoes/resumo`).then(setDados).catch((e) => setErro(e.message));
  }, [teamId]);

  const pct = (a: number, b: number) => (b ? `${Math.round((a / b) * 100)}%` : "—");
  return (
    <section style={{ marginTop: espaco.xxl, maxWidth: 900 }}>
      <SecaoTitulo subtitulo={tr("O que a equipa decidiu face a cada aviso, e o que aconteceu nos {0} dias seguintes. Um aviso muitas vezes ignorado sem consequências é candidato a limiar mais alto.", [dados?.seguimento_dias ?? 14])}>
        {tr("Decisões e seguimento")}</SecaoTitulo>
      {erro ? <Vazio>{erro}</Vazio>
        : !dados ? <Vazio>{tr("A carregar…")}</Vazio>
        : !dados.disponivel ? <Vazio>{dados.motivo}</Vazio>
        : dados.total === 0 ? <Vazio>{tr("Ainda não há decisões registadas. Regista-as no Centro de Controlo, ao clicar num jogador em «Precisam de atenção».")}</Vazio>
        : (
          <div style={{ overflowX: "auto", background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem", minWidth: 680 }}>
              <thead>
                <tr style={{ background: "rgb(var(--ink) / 0.04)" }}>
                  {["Aviso", "Decisões", "Reduzir", "Ajustar", "Manter", "Ignorar", "Lesão a seguir", "Aviso repetido"].map((h, i) => (
                    <th key={h} style={{ ...th, textAlign: i ? "right" : "left" }}>{tr(h)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dados.sinais.map((l) => (
                  <tr key={l.sinal} style={{ borderTop: `1px solid ${cores.borda}` }}>
                    <td style={td}>{tr(NOME_SINAL[l.sinal] ?? l.sinal)}</td>
                    <td style={tdN}>{l.n}{l.em_seguimento ? <span style={{ color: cores.textoFraco }}> ({tr("{0} em curso", [l.em_seguimento])})</span> : null}</td>
                    {["reduzir", "ajustar", "manter", "ignorar"].map((k) => <td key={k} style={tdN}>{l.por_decisao[k] ?? 0}</td>)}
                    <td style={tdN}>{l.lesao_seguinte} <span style={{ color: cores.textoFraco }}>/ {l.fechadas} · {pct(l.lesao_seguinte, l.fechadas)}</span></td>
                    <td style={tdN}>{l.repetido} <span style={{ color: cores.textoFraco }}>/ {l.fechadas}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p style={{ margin: 0, padding: `8px ${espaco.md}px`, fontSize: "0.72rem", color: cores.textoSuave, borderTop: `1px solid ${cores.borda}` }}>
              {tr("«Lesão a seguir» e «Aviso repetido» só contam decisões com pelo menos {0} dias. São contagens descritivas com poucos casos — servem para levantar perguntas, não para provar causas.", [dados.seguimento_dias])}
            </p>
          </div>
        )}
    </section>
  );
}

const th: React.CSSProperties = { padding: "7px 10px", fontSize: "0.68rem", letterSpacing: "0.04em", textTransform: "uppercase", color: cores.textoSuave, fontWeight: 600, whiteSpace: "nowrap" };
const td: React.CSSProperties = { padding: "7px 10px", color: cores.texto };
const tdN: React.CSSProperties = { ...td, textAlign: "right", fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" };
