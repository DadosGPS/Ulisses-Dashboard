import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { QuadranteCombinado, type LinhaCombinada } from "@/components/ui/QuadranteCombinado";
import { NomeJogador } from "@/components/ui/NomeJogador";
import { cores, espaco, raio } from "@/lib/theme";

interface Resposta {
  tem_dados: boolean;
  eixo_externo?: { label: string; unidade: string };
  eixo_interno?: { label: string; unidade: string };
  mediana_externo?: number | null;
  mediana_interno?: number | null;
  jogadores?: LinhaCombinada[];
}

async function obterDados(teamId: string, accessToken: string, f: { microciclo?: string; dia_md?: string }): Promise<Resposta> {
  const url = new URL(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/combinada`);
  if (f.microciclo) url.searchParams.set("microciclo", f.microciclo);
  if (f.dia_md) url.searchParams.set("dia_md", f.dia_md);
  const res = await fetch(url, { headers: { Authorization: `Bearer ${accessToken}` }, cache: "no-store" });
  if (!res.ok) throw new Error(`Falha (${res.status}).`);
  return res.json();
}

const CORES_FLAG: Record<string, string> = {
  "alto|alto": cores.cargaInterna,
  "alto|baixo": cores.atencao,
  "baixo|alto": cores.info,
  "baixo|baixo": cores.sucesso,
};

export default async function CombinadaPage({
  searchParams,
}: {
  searchParams: Promise<{ microciclo?: string; dia_md?: string }>;
}) {
  const { microciclo, dia_md } = await searchParams;

  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;

  const { data: membro } = await supabase.from("team_members").select("team_id").eq("user_id", session.user.id).limit(1).single();
  if (!membro) return <EstadoVazio mensagem="Ainda não estás associado a nenhuma equipa." />;

  let dados: Resposta;
  try {
    dados = await obterDados(membro.team_id, session.access_token, { microciclo, dia_md });
  } catch {
    return <EstadoVazio mensagem="Não foi possível ligar à API." />;
  }

  return (
    <div>
      <PageHeader titulo="Carga Externa × Interna" subtitulo="Cruzamento das duas cargas — flags de monitorização, não diagnóstico" />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {!dados.tem_dados || !dados.jogadores || dados.jogadores.length === 0 ? (
          <EstadoVazio mensagem="Sem dados para esta janela. É preciso carga externa (distância) e interna (Carga Interna ou PSE) — ajusta o microciclo/dia ou confirma a importação." />
        ) : (
          <>
            <QuadranteCombinado
              jogadores={dados.jogadores}
              medianaExterno={dados.mediana_externo ?? null}
              medianaInterno={dados.mediana_interno ?? null}
              eixoExterno={dados.eixo_externo!}
              eixoInterno={dados.eixo_interno!}
            />

            <p style={{ color: cores.textoSuave, fontSize: "0.78rem", margin: `${espaco.lg}px 0 ${espaco.md}px` }}>
              A leitura de cada quadrante depende do objetivo do dia — são pistas para o preparador olhar, não juízos automáticos.
              Ex.: <strong>Ext↓ Int↑</strong> (esforço percebido alto para pouca distância) pode indicar fadiga ou doença; <strong>Ext↑ Int↓</strong> pode ser boa eficiência ou sub-registo da PSE.
            </p>

            <div style={{ overflowX: "auto", border: `1px solid ${cores.borda}`, borderRadius: raio.md, background: cores.bgCartao, marginTop: espaco.md }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontVariantNumeric: "tabular-nums" }}>
                <thead>
                  <tr style={{ background: "rgba(255,255,255,0.04)" }}>
                    <th style={th("left")}>Jogador · Posição</th>
                    <th style={th("center")}>{dados.eixo_externo?.label} ({dados.eixo_externo?.unidade})</th>
                    <th style={th("center")}>{dados.eixo_interno?.label} ({dados.eixo_interno?.unidade})</th>
                    <th style={th("center")}>Flag</th>
                  </tr>
                </thead>
                <tbody>
                  {dados.jogadores.map((j) => (
                    <tr key={j.jogador} style={{ borderTop: `1px solid ${cores.borda}` }}>
                      <td style={{ padding: "8px 12px", fontSize: "0.8rem", fontWeight: 600, color: "rgba(255,255,255,0.9)", whiteSpace: "nowrap" }}>
                        <NomeJogador nome={j.jogador} /> <span style={{ color: cores.textoSuave, fontWeight: 400 }}>· {j.posicao}</span>
                      </td>
                      <td style={tdNum}>{j.externo?.toLocaleString("pt-PT") ?? "—"}</td>
                      <td style={tdNum}>{j.interno?.toLocaleString("pt-PT") ?? "—"}</td>
                      <td style={{ padding: "8px 12px", textAlign: "center", whiteSpace: "nowrap" }}>
                        <span style={{ fontSize: "0.72rem", fontWeight: 700, color: CORES_FLAG[`${j.flag_ext}|${j.flag_int}`] ?? cores.textoSuave }}>{j.flag}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function th(align: "left" | "center"): React.CSSProperties {
  return { padding: "10px 12px", fontSize: "0.62rem", letterSpacing: "0.06em", textTransform: "uppercase", color: cores.textoSuave, textAlign: align, whiteSpace: "nowrap" };
}
const tdNum: React.CSSProperties = { padding: "8px 12px", textAlign: "center", fontSize: "0.82rem", color: "white", fontWeight: 600 };

function EstadoVazio({ mensagem }: { mensagem: string }) {
  return (
    <div style={{ maxWidth: 600, margin: "80px auto", padding: "0 24px", textAlign: "center" }}>
      <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.95rem" }}>{mensagem}</p>
    </div>
  );
}
