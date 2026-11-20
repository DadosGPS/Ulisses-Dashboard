/** Problemas da verificação de dados: texto (traduzível) e lista. */
import { cores, espaco, raio, letra } from "@/lib/theme";
import type { Tr } from "@/lib/i18n/core";

export interface Exemplo { linha?: number; jogador: string; data: string | null; periodo?: string; valor?: number | null }
export interface Problema { codigo: string; nivel: "erro" | "aviso" | "info"; texto: string; n: number; exemplos: Exemplo[] }
export interface Verificacao {
  problemas: Problema[];
  resumo: { erros: number; avisos: number; info: number; linhas?: number; jogadores?: number; datas?: [string, string] | null; n_linhas_erro?: number;
    recontagem?: { sessoes?: { linhas: number; valores: number }; periodos?: { linhas: number; valores: number } } };
  n_linhas_erro?: number;
  recontagem?: { sessoes?: { linhas: number; valores: number }; periodos?: { linhas: number; valores: number } };
}

export const COR_NIVEL = { erro: cores.perigo, aviso: cores.atencao, info: cores.info } as const;

/** Modelos por código (português = chave da tradução). {0} = n, {1} = coluna. */
const MODELOS: Record<string, string> = {
  data_invalida: "{0} linha(s) sem data válida — sem data não se sabe a que sessão pertencem.",
  negativo: "{0} linha(s) com «{1}» negativo.",
  vel_impossivel: "{0} linha(s) com velocidade máxima acima de 45 km/h — erro do GPS ou de unidades (m/s?).",
  dist_impossivel: "{0} linha(s) com mais de 30 000 m numa sessão — confirma as unidades do export.",
  hsr_maior_dist: "{0} linha(s) com HSR maior do que a distância total — colunas trocadas no mapeamento?",
  sprint_maior_dist: "{0} linha(s) com sprint maior do que a distância total.",
  duracao_impossivel: "{0} linha(s) com mais de 300 minutos — a duração está em segundos?",
  pse_fora: "{0} linha(s) com PSE acima de 10.",
  wellness_fora: "{0} linha(s) com «{1}» fora de 1–5.",
  vel_pico: "{0} linha(s) com velocidade máxima acima de 36 km/h — pode ser um pico do GPS; confirma antes de virar recorde.",
  dist_alta: "{0} linha(s) com mais de 16 000 m.",
  sem_gps: "{0} linha(s) com duração mas zero em todas as métricas de GPS — unidade desligada ou não usada?",
  data_futura: "{0} linha(s) com data no futuro — formato da data trocado (dia/mês)?",
  linhas_repetidas: "{0} caso(s) de um jogador com várias linhas no mesmo dia. Vão ser somadas numa só sessão — se forem partes ou exercícios, mapeia a coluna do nome do período para «Período».",
  periodos_vs_total: "{0} sessão(ões) em que a soma das partes/exercícios difere do total do ficheiro em mais de 5 %. É o total que conta para a carga do dia.",
  nome_parecido: "{0} nome(s) quase iguais a jogadores que já existem — vão ser criados como jogadores novos. Corrige a grafia no ficheiro se for o mesmo jogador.",
  jogo_sem_minutos: "Os jogos não têm minutos jogados («Duração»). Sem eles, a referência de jogo usa o pico em vez da média por jogo completo.",
};

const EFEITO_SEM: Record<string, string> = {
  "Tipo": "{0} linha(s) sem «Tipo»: não dá para separar jogo de treino.",
  "Dia MD": "{0} linha(s) sem «Dia MD»: o planeamento por dia e a deteção de jogo ficam incompletos.",
  "Microciclo (Nr)": "{0} linha(s) sem «Microciclo (Nr)»: a leitura semanal não as inclui.",
};

export function textoProblema(p: Problema, tr: Tr): string {
  if (tr.lingua === "pt") return p.texto;
  const [base, col] = p.codigo.split(":");
  if (base === "sem" && col && EFEITO_SEM[col]) return tr(EFEITO_SEM[col], [p.n]);
  if (base === "periodos") return tr("Períodos detetados: {0} linha(s) — ficam guardados para os relatórios de jogo e de treino.", [p.n]);
  if (base === "recontagem") return tr("Os valores lidos de volta da base de dados não batem com o ficheiro. A importação foi desfeita.");
  const m = MODELOS[base];
  return m ? tr(m, [p.n, col ?? ""]) : p.texto;
}

export function ListaProblemas({ problemas, tr, vazio }: { problemas: Problema[]; tr: Tr; vazio?: string }) {
  if (!problemas.length) return <p style={{ fontSize: letra.texto, color: cores.textoSuave, margin: 0, textAlign: "center", padding: espaco.lg }}>{vazio ?? tr("Nada a mostrar.")}</p>;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: espaco.sm }}>
      {problemas.map((p, i) => {
        const cor = COR_NIVEL[p.nivel];
        return (
          <div key={`${p.codigo}-${i}`} style={{ padding: `10px ${espaco.md}px`, background: `color-mix(in srgb, ${cor} 7%, transparent)`, border: `1px solid color-mix(in srgb, ${cor} 30%, transparent)`, borderRadius: raio.sm }}>
            <div style={{ display: "flex", gap: espaco.sm, alignItems: "flex-start", fontSize: letra.texto, color: cores.texto }}>
              <span style={{ fontSize: letra.legenda, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", color: cor, minWidth: 44, marginTop: 2 }}>
                {p.nivel === "erro" ? tr("Erro") : p.nivel === "aviso" ? tr("Aviso") : tr("Info")}
              </span>
              <span>{textoProblema(p, tr)}</span>
            </div>
            {p.exemplos.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 6, marginLeft: 56 }}>
                {p.exemplos.map((e, j) => (
                  <span key={j} style={{ fontSize: letra.pequeno, color: cores.textoSuave, background: cores.superficie, borderRadius: 6, padding: "2px 8px" }}>
                    {e.jogador}{e.data ? ` · ${e.data}` : ""}{e.periodo ? ` · ${e.periodo}` : ""}{e.valor !== undefined && e.valor !== null ? ` · ${e.valor}` : ""}
                  </span>
                ))}
                {p.n > p.exemplos.length && <span style={{ fontSize: letra.pequeno, color: cores.textoFraco }}>{tr("+{0} mais", [p.n - p.exemplos.length])}</span>}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
