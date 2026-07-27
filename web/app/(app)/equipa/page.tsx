import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { AcwrList } from "@/components/ui/AcwrList";
import { LoadProfileTable } from "@/components/ui/LoadProfileTable";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { cores, espaco } from "@/lib/theme";
import type { EquipaResponse } from "@/lib/types";

async function obterEquipa(teamId: string, accessToken: string): Promise<EquipaResponse> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/equipa`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Falha ao carregar a equipa (${res.status}).`);
  return res.json();
}

export default async function EquipaPage() {
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

  if (!membro) {
    return <EstadoVazio mensagem="Ainda não estás associado a nenhuma equipa." />;
  }

  let dados: EquipaResponse;
  try {
    dados = await obterEquipa(membro.team_id, session.access_token);
  } catch {
    return <EstadoVazio mensagem="Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr." />;
  }

  if (!dados.tem_dados) {
    return <EstadoVazio mensagem="Ainda não há dados carregados para esta equipa." />;
  }

  const linhasTabela = dados.load_profile.linhas.map((l) => ({ jogador: l.jogador, valores: l.valores }));

  return (
    <div>
      <PageHeader titulo="Equipa" subtitulo="ACWR, evolução de carga e perfil de carga externa por jogador" />

      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1.4fr", gap: espaco.lg, marginBottom: espaco.xxl }}>
          <div>
            <SecaoTitulo>🚦 ACWR por Jogador</SecaoTitulo>
            <AcwrList dados={dados.acwr} />
          </div>

          <div>
            <SecaoTitulo>📈 Evolução da Carga Interna</SecaoTitulo>
            <div
              style={{
                background: cores.bgCartao,
                border: `1px solid ${cores.borda}`,
                borderRadius: 12,
                padding: espaco.md,
              }}
            >
              {dados.ci_evolucao.length > 0 ? (
                <PlotlyChart
                  data={[
                    {
                      x: dados.ci_evolucao.map((p) => `MC ${p.microciclo}`),
                      y: dados.ci_evolucao.map((p) => p.carga_interna_media),
                      type: "scatter",
                      mode: "text+lines+markers",
                      text: dados.ci_evolucao.map((p) => String(Math.round(p.carga_interna_media))),
                      textposition: "top center",
                      textfont: { size: 10, color: "white" },
                      line: { color: cores.cargaInterna, width: 3 },
                      marker: { size: 9, color: cores.cargaInterna, line: { width: 2, color: "white" } },
                      fill: "tozeroy",
                      fillcolor: "rgba(230,57,70,0.06)",
                    },
                  ]}
                  altura={260}
                />
              ) : (
                <p style={{ color: cores.textoSuave, fontSize: "0.85rem" }}>Sem microciclos suficientes.</p>
              )}
            </div>
          </div>
        </div>

        <SecaoTitulo>🏃 Perfil de Carga Externa — por Jogador</SecaoTitulo>
        {dados.load_profile.colunas.length > 0 ? (
          <LoadProfileTable colunas={dados.load_profile.colunas.map((c) => ({ chave: c.chave, label: c.label, cor: c.cor, casas: c.casas }))} linhas={linhasTabela} />
        ) : (
          <p style={{ color: cores.textoSuave, fontSize: "0.85rem" }}>Sem métricas GPS disponíveis.</p>
        )}
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

function EstadoVazio({ mensagem }: { mensagem: string }) {
  return (
    <div style={{ maxWidth: 600, margin: "80px auto", padding: "0 24px", textAlign: "center" }}>
      <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.95rem" }}>{mensagem}</p>
    </div>
  );
}
