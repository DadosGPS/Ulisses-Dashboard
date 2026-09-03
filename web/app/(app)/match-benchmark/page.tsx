import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { NomeJogador } from "@/components/ui/NomeJogador";
import { cores, espaco, raio } from "@/lib/theme";

interface MetricaDef {
  chave: string;
  label: string;
  unidade: string;
  cor: string;
  casas: number;
}

interface EquipaMetrica {
  chave: string;
  label: string;
  unidade: string;
  cor: string;
  benchmark: number | null;
  atual: number | null;
  pct: number | null;
}

interface JogadorRow {
  jogador: string;
  posicao: string;
  metricas: Record<string, { atual: number | null; benchmark: number | null; pct: number | null }>;
}

interface Resposta {
  tem_dados: boolean;
  sem_referencia?: boolean;
  sem_treinos?: boolean;
  metricas: MetricaDef[];
  equipa: EquipaMetrica[];
  jogadores: JogadorRow[];
  data_treino: string | null;
  n_jogos: number;
}

async function obterDados(teamId: string, accessToken: string): Promise<Resposta> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/match-benchmark`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Falha (${res.status}).`);
  return res.json();
}

/** Cor por % de exposição face ao jogo — descritivo: quão perto o treino
 * ficou da exigência de jogo. */
function corPct(pct: number | null): string {
  if (pct === null) return cores.textoFraco;
  if (pct >= 100) return cores.cargaInterna;
  if (pct >= 75) return cores.sucesso;
  if (pct >= 50) return cores.atencao;
  return cores.info;
}

export default async function MatchBenchmarkPage() {
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

  let dados: Resposta;
  try {
    dados = await obterDados(membro.team_id, session.access_token);
  } catch {
    return <EstadoVazio mensagem="Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr." />;
  }

  if (!dados.tem_dados) {
    const msg = dados.sem_referencia
      ? "Ainda não há sessões de Jogo registadas para servir de referência. Marca sessões como 'Jogo' ao importar."
      : dados.sem_treinos
      ? "Ainda não há treinos para comparar com os jogos."
      : "Ainda não há dados suficientes para o benchmark de jogo.";
    return (
      <div>
        <PageHeader titulo="Match-Day Benchmark" subtitulo="Treino vs exigência de jogo" />
        <EstadoVazio mensagem={msg} />
      </div>
    );
  }

  const dataLegivel = dados.data_treino
    ? new Date(dados.data_treino).toLocaleDateString("pt-PT", { day: "2-digit", month: "long", year: "numeric" })
    : "—";

  return (
    <div>
      <PageHeader
        titulo="Match-Day Benchmark"
        subtitulo={`Treino de ${dataLegivel} vs média de ${dados.n_jogos} jogo(s) — % da exigência de jogo atingida`}
      />

      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        <SecaoTitulo>🎯 Equipa — % da exigência de jogo</SecaoTitulo>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))",
            gap: espaco.md,
            marginBottom: espaco.xxl,
          }}
        >
          {dados.equipa.map((m) => (
            <BenchmarkCard key={m.chave} m={m} />
          ))}
        </div>

        <SecaoTitulo>🏃 Por Jogador</SecaoTitulo>
        <p style={{ color: cores.textoSuave, fontSize: "0.78rem", margin: `0 0 ${espaco.md}px` }}>
          Cada valor é a % do treino recente face à média de jogos do próprio jogador.
        </p>
        <div style={{ overflowX: "auto", border: `1px solid ${cores.borda}`, borderRadius: raio.md, background: cores.bgCartao }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontVariantNumeric: "tabular-nums" }}>
            <thead>
              <tr style={{ background: "rgba(255,255,255,0.04)" }}>
                <th style={th("left")}>Jogador · Posição</th>
                {dados.metricas.map((m) => (
                  <th key={m.chave} style={th("center")}>{m.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dados.jogadores.map((j) => (
                <tr key={j.jogador} style={{ borderTop: `1px solid ${cores.borda}` }}>
                  <td style={{ padding: "8px 14px", fontSize: "0.8rem", fontWeight: 600, color: "rgba(255,255,255,0.9)", whiteSpace: "nowrap" }}>
                    <NomeJogador nome={j.jogador} /> <span style={{ color: cores.textoSuave, fontWeight: 400 }}>· {j.posicao}</span>
                  </td>
                  {dados.metricas.map((m) => {
                    const cel = j.metricas[m.chave];
                    const pct = cel?.pct ?? null;
                    return (
                      <td key={m.chave} style={{ padding: "8px 10px", textAlign: "center" }}>
                        {pct !== null ? (
                          <span style={{ fontSize: "0.82rem", fontWeight: 700, color: corPct(pct) }}>{pct}%</span>
                        ) : (
                          <span style={{ color: cores.textoFraco }}>—</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p style={{ color: cores.textoSuave, fontSize: "0.75rem", marginTop: espaco.md }}>
          <span style={{ color: cores.info }}>●</span> &lt;50% &nbsp;
          <span style={{ color: cores.atencao }}>●</span> 50–75% &nbsp;
          <span style={{ color: cores.sucesso }}>●</span> 75–100% &nbsp;
          <span style={{ color: cores.cargaInterna }}>●</span> ≥100% (igual ou acima do jogo) — descritivo, depende do objetivo do dia.
        </p>
      </div>
    </div>
  );
}

function BenchmarkCard({ m }: { m: EquipaMetrica }) {
  const pct = m.pct ?? 0;
  const cor = corPct(m.pct);
  const larguraBarra = Math.min(pct, 130);
  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderLeft: `3px solid ${m.cor}`, borderRadius: raio.md, padding: espaco.lg }}>
      <div style={{ fontSize: "0.72rem", letterSpacing: "0.04em", textTransform: "uppercase", color: cores.textoSuave, marginBottom: espaco.sm }}>
        {m.label}
      </div>
      <div className="font-display" style={{ fontSize: "1.9rem", fontWeight: 800, color: cor, lineHeight: 1, fontVariantNumeric: "tabular-nums" }}>
        {m.pct !== null ? `${m.pct}%` : "—"}
      </div>
      <div style={{ fontSize: "0.72rem", color: cores.textoSuave, marginTop: 2 }}>da exigência de jogo</div>

      {/* barra */}
      <div style={{ position: "relative", height: 6, background: cores.bg, borderRadius: 999, marginTop: espaco.md, overflow: "hidden" }}>
        <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${(larguraBarra / 130) * 100}%`, background: cor, borderRadius: 999 }} />
        {/* marca dos 100% */}
        <div style={{ position: "absolute", left: `${(100 / 130) * 100}%`, top: -2, bottom: -2, width: 1, background: "rgba(255,255,255,0.5)" }} />
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.72rem", color: cores.textoSuave, marginTop: espaco.sm }}>
        <span>treino {m.atual !== null ? m.atual.toLocaleString("pt-PT") : "—"}</span>
        <span>jogo {m.benchmark !== null ? m.benchmark.toLocaleString("pt-PT") : "—"} {m.unidade}</span>
      </div>
    </div>
  );
}

function SecaoTitulo({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="font-display" style={{ fontSize: "1rem", fontWeight: 600, color: "white", margin: `0 0 ${espaco.md}px` }}>
      {children}
    </h2>
  );
}

function th(align: "left" | "center"): React.CSSProperties {
  return { padding: "10px 12px", fontSize: "0.64rem", letterSpacing: "0.06em", textTransform: "uppercase", color: cores.textoSuave, textAlign: align, whiteSpace: "nowrap" };
}

function EstadoVazio({ mensagem }: { mensagem: string }) {
  return (
    <div style={{ maxWidth: 600, margin: "80px auto", padding: "0 24px", textAlign: "center" }}>
      <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.95rem" }}>{mensagem}</p>
    </div>
  );
}
