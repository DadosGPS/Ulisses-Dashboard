import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { cores, espaco, raio } from "@/lib/theme";

interface Sessao {
  data: string;
  tipo: string;
  dia_md: string;
  microciclo: number | null;
  n_jogadores: number;
  duracao_min: number | null;
  distancia_total_m: number | null;
  hsr_m: number | null;
  sprint_m: number | null;
  carga_interna_media: number | null;
}

interface Resposta {
  tem_dados: boolean;
  sessoes: Sessao[];
}

async function obterDados(teamId: string, accessToken: string): Promise<Resposta> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/sessoes`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Falha (${res.status}).`);
  return res.json();
}

const num = (v: number | null, casas = 0) => (v === null || v === undefined ? "—" : v.toLocaleString("pt-PT", { maximumFractionDigits: casas }));

export default async function SessoesListaPage() {
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

  return (
    <div>
      <PageHeader titulo="Todas as Sessões" subtitulo={`${dados.sessoes?.length ?? 0} sessões registadas`} />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {!dados.tem_dados || dados.sessoes.length === 0 ? (
          <EstadoVazio mensagem="Ainda não há sessões carregadas. Importa dados de GPS para começar." />
        ) : (
          <div style={{ overflowX: "auto", border: `1px solid ${cores.borda}`, borderRadius: raio.md, background: cores.bgCartao }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontVariantNumeric: "tabular-nums" }}>
              <thead>
                <tr style={{ background: "rgba(255,255,255,0.04)" }}>
                  <th style={th("left")}>Data</th>
                  <th style={th("left")}>Tipo</th>
                  <th style={th("left")}>MD</th>
                  <th style={th("center")}>Micro</th>
                  <th style={th("center")}>Jogadores</th>
                  <th style={th("center")}>Duração</th>
                  <th style={th("center")}>Dist. Total (m)</th>
                  <th style={th("center")}>HSR (m)</th>
                  <th style={th("center")}>Sprint (m)</th>
                  <th style={th("center")}>Carga Int. média</th>
                </tr>
              </thead>
              <tbody>
                {dados.sessoes.map((s, i) => (
                  <tr key={`${s.data}-${s.tipo}-${i}`} style={{ borderTop: `1px solid ${cores.borda}` }}>
                    <td style={tdTexto}>{new Date(s.data).toLocaleDateString("pt-PT")}</td>
                    <td style={tdTexto}>
                      <span
                        style={{
                          fontSize: "0.7rem",
                          fontWeight: 700,
                          padding: "2px 8px",
                          borderRadius: 999,
                          color: s.tipo === "Jogo" ? cores.cargaInterna : cores.info,
                          background: `color-mix(in srgb, ${s.tipo === "Jogo" ? cores.cargaInterna : cores.info} 15%, transparent)`,
                        }}
                      >
                        {s.tipo}
                      </span>
                    </td>
                    <td style={tdTexto}>{s.dia_md}</td>
                    <td style={{ ...tdTexto, textAlign: "center" }}>{s.microciclo ?? "—"}</td>
                    <td style={{ ...tdTexto, textAlign: "center" }}>{s.n_jogadores}</td>
                    <td style={{ ...tdTexto, textAlign: "center" }}>{num(s.duracao_min)}{s.duracao_min ? " min" : ""}</td>
                    <td style={tdNum}>{num(s.distancia_total_m)}</td>
                    <td style={tdNum}>{num(s.hsr_m)}</td>
                    <td style={tdNum}>{num(s.sprint_m)}</td>
                    <td style={tdNum}>{num(s.carga_interna_media)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function th(align: "left" | "center"): React.CSSProperties {
  return { padding: "10px 12px", fontSize: "0.62rem", letterSpacing: "0.06em", textTransform: "uppercase", color: cores.textoSuave, textAlign: align, whiteSpace: "nowrap" };
}
const tdTexto: React.CSSProperties = { padding: "8px 12px", fontSize: "0.78rem", color: "rgba(255,255,255,0.82)", whiteSpace: "nowrap" };
const tdNum: React.CSSProperties = { padding: "8px 12px", fontSize: "0.8rem", color: "white", textAlign: "center", fontWeight: 600 };

function EstadoVazio({ mensagem }: { mensagem: string }) {
  return (
    <div style={{ maxWidth: 600, margin: "80px auto", padding: "0 24px", textAlign: "center" }}>
      <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.95rem" }}>{mensagem}</p>
    </div>
  );
}
