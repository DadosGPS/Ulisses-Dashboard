import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { cores, espaco, raio } from "@/lib/theme";
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
    return <EstadoVazio mensagem="Ainda não há dados suficientes para calcular Z-Scores." />;
  }

  return (
    <div>
      <PageHeader titulo="Avançado" subtitulo={`Z-Score por jogador vs média da equipa · Microciclo ${dados.microciclo ?? "—"}`} />

      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px`, display: "grid", gridTemplateColumns: "1fr 1fr", gap: espaco.lg }}>
        {dados.metricas.map((m) => {
          const ordenado = [...m.jogadores].sort((a, b) => a.zscore - b.zscore);
          return (
            <div key={m.metrica} style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
              <div className="font-display" style={{ fontSize: "0.88rem", fontWeight: 600, color: "white", marginBottom: espaco.sm }}>
                {m.metrica}
              </div>
              <PlotlyChart
                data={[
                  {
                    x: ordenado.map((j) => j.zscore),
                    y: ordenado.map((j) => j.jogador),
                    type: "bar",
                    orientation: "h",
                    marker: { color: ordenado.map((j) => (j.zscore >= 0 ? cores.sucesso : cores.perigo)) },
                    text: ordenado.map((j) => j.zscore.toFixed(2)),
                    textposition: "outside",
                  },
                ]}
                layout={{
                  margin: { l: 110, r: 30, t: 10, b: 30 },
                  yaxis: { tickfont: { size: 10 } },
                  xaxis: { title: { text: "Desvios-padrão vs média da equipa" }, zeroline: true, zerolinecolor: "rgba(255,255,255,0.25)" },
                }}
                altura={Math.max(220, ordenado.length * 24)}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}

function EstadoVazio({ mensagem }: { mensagem: string }) {
  return (
    <div style={{ maxWidth: 600, margin: "80px auto", padding: "0 24px", textAlign: "center" }}>
      <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.95rem" }}>{mensagem}</p>
    </div>
  );
}
