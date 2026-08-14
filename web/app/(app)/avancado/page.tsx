import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { NomeJogador } from "@/components/ui/NomeJogador";
import { alphaHex, cores, espaco, raio } from "@/lib/theme";
import type { AvancadoResponse } from "@/lib/types";

async function obterAvancado(teamId: string, accessToken: string): Promise<AvancadoResponse> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/avancado`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Falha ao carregar (${res.status}).`);
  return res.json();
}

export default async function AvancadoPage() {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) return null;

  const { data: membro } = await supabase
    .from("team_members")
    .select("team_id")
    .eq("user_id", session.user.id)
    .limit(1)
    .single();

  if (!membro) return <EstadoVazio mensagem="Ainda não estás associado a nenhuma equipa." />;

  let dados: AvancadoResponse;
  try {
    dados = await obterAvancado(membro.team_id, session.access_token);
  } catch {
    return <EstadoVazio mensagem="Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr." />;
  }

  if (!dados.tem_dados || dados.metricas.length === 0) {
    return <EstadoVazio mensagem="Ainda não há dados suficientes para calcular Z-Scores de carga externa." />;
  }

  // Jogador → posição (a real, não o grupo de comparação — um jogador sem
  // peers suficientes na sua posição ainda assim aparece na secção da sua
  // posição real, só o cálculo do z-score é que cai para a equipa toda).
  const posicaoPorJogador = new Map<string, string>();
  const zscorePorJogadorMetrica = new Map<string, Map<string, { zscore: number; grupo: string }>>();
  for (const m of dados.metricas) {
    for (const j of m.jogadores) {
      if (!posicaoPorJogador.has(j.jogador)) posicaoPorJogador.set(j.jogador, j.posicao);
      if (!zscorePorJogadorMetrica.has(j.jogador)) zscorePorJogadorMetrica.set(j.jogador, new Map());
      zscorePorJogadorMetrica.get(j.jogador)!.set(m.metrica, { zscore: j.zscore, grupo: j.grupo_comparacao });
    }
  }

  const posicoes = [...new Set(posicaoPorJogador.values())].sort((a, b) => a.localeCompare(b, "pt"));

  return (
    <div>
      <PageHeader
        titulo="Avançado"
        subtitulo={`Z-Score de carga externa vs colegas da mesma posição · Microciclo ${dados.microciclo ?? "—"}`}
      />

      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px`, display: "flex", flexDirection: "column", gap: espaco.xl }}>
        {posicoes.map((posicao) => {
          const jogadoresPos = [...posicaoPorJogador.entries()]
            .filter(([, p]) => p === posicao)
            .map(([j]) => j)
            .sort((a, b) => a.localeCompare(b, "pt"));

          return (
            <div key={posicao}>
              <h2 className="font-display" style={{ fontSize: "0.9rem", fontWeight: 700, color: "white", margin: `0 0 ${espaco.sm}px` }}>
                {posicao === "—" ? "Sem posição registada" : posicao}
              </h2>
              <div style={{ overflowX: "auto", border: `1px solid ${cores.borda}`, borderRadius: raio.md, background: cores.bgCartao }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontVariantNumeric: "tabular-nums" }}>
                  <thead>
                    <tr style={{ background: "rgba(255,255,255,0.04)" }}>
                      <th style={thStyle("left")}>Jogador</th>
                      {dados.metricas.map((m) => (
                        <th key={m.metrica} style={thStyle("center")}>
                          {m.metrica}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {jogadoresPos.map((jogador) => (
                      <tr key={jogador}>
                        <td style={{ padding: "8px 14px", fontSize: "0.8rem", fontWeight: 600, color: "rgba(255,255,255,0.9)", whiteSpace: "nowrap" }}>
                          <NomeJogador nome={jogador} />
                        </td>
                        {dados.metricas.map((m) => {
                          const cel = zscorePorJogadorMetrica.get(jogador)?.get(m.metrica);
                          if (cel === undefined) {
                            return (
                              <td key={m.metrica} style={{ padding: "6px 8px", textAlign: "center", color: cores.textoFraco }}>
                                —
                              </td>
                            );
                          }
                          const { zscore: z, grupo } = cel;
                          // Escala divergente: verde = acima da média do grupo, vermelho = abaixo,
                          // saturação cresce com a magnitude do desvio (±2.5 DP = saturação máxima).
                          const cor = z >= 0 ? cores.sucesso : cores.perigo;
                          const alpha = 0.15 + Math.min(Math.abs(z) / 2.5, 1) * 0.55;
                          return (
                            <td key={m.metrica} style={{ padding: "6px 8px", textAlign: "center" }}>
                              <span
                                title={grupo === "equipa" ? "vs equipa toda (sem peers suficientes na posição)" : `vs ${grupo}`}
                                style={{
                                  display: "inline-block",
                                  minWidth: 52,
                                  padding: "5px 10px",
                                  borderRadius: 14,
                                  background: `${cor}${alphaHex(alpha)}`,
                                  color: "white",
                                  fontWeight: 700,
                                  fontSize: "0.75rem",
                                  cursor: "default",
                                }}
                              >
                                {z.toFixed(2)}
                              </span>
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          );
        })}
      </div>
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

function EstadoVazio({ mensagem }: { mensagem: string }) {
  return (
    <div style={{ maxWidth: 600, margin: "80px auto", padding: "0 24px", textAlign: "center" }}>
      <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.95rem" }}>{mensagem}</p>
    </div>
  );
}
