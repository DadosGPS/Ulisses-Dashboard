import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { AcwrList } from "@/components/ui/AcwrList";
import { PerfilCargaExternaGraficos } from "@/components/ui/PerfilCargaExternaGraficos";
import { IntervaloMicrociclos } from "@/components/ui/IntervaloMicrociclos";
import { EstadoAtletas } from "@/components/ui/EstadoAtletas";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { cores, espaco } from "@/lib/theme";
import type { EquipaResponse, EstadoJogador } from "@/lib/types";

const LABEL_EXTERNA: Record<string, { label: string; unidade: string; cor: string }> = {
  distancia_total_m: { label: "Distância Total", unidade: "m", cor: cores.distanciaTotal },
  hsr_m: { label: "HSR", unidade: "m", cor: cores.hsr },
  sprint_m: { label: "Sprint", unidade: "m", cor: cores.sprint },
  acc_n: { label: "Acelerações", unidade: "", cor: cores.acc },
  dcc_n: { label: "Desacelerações", unidade: "", cor: cores.dcc },
  vel_max_kmh: { label: "Vel. Máxima", unidade: "km/h", cor: cores.velMax },
};

async function obterEquipa(
  teamId: string,
  accessToken: string,
  microInicio?: string,
  microFim?: string
): Promise<EquipaResponse> {
  const url = new URL(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/equipa`);
  if (microInicio) url.searchParams.set("micro_inicio", microInicio);
  if (microFim) url.searchParams.set("micro_fim", microFim);
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Falha ao carregar a equipa (${res.status}).`);
  return res.json();
}

async function obterEstados(teamId: string, accessToken: string): Promise<EstadoJogador[]> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/jogadores/estado`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
  if (!res.ok) return [];
  const dados = await res.json();
  return dados.jogadores;
}

export default async function EquipaPage({
  searchParams,
}: {
  searchParams: Promise<{ micro_inicio?: string; micro_fim?: string }>;
}) {
  const { micro_inicio, micro_fim } = await searchParams;

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
    dados = await obterEquipa(membro.team_id, session.access_token, micro_inicio, micro_fim);
  } catch {
    return <EstadoVazio mensagem="Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr." />;
  }
  const estados = await obterEstados(membro.team_id, session.access_token);

  if (!dados.tem_dados) {
    return <EstadoVazio mensagem="Ainda não há dados carregados para esta equipa." />;
  }

  const linhasTabela = dados.load_profile.linhas.map((l) => ({ jogador: l.jogador, valores: l.valores }));
  const inicioNum = micro_inicio ? Number(micro_inicio) : null;
  const fimNum = micro_fim ? Number(micro_fim) : null;

  return (
    <div>
      <PageHeader titulo="Equipa" subtitulo="ACWR, evolução de carga e perfil de carga externa por jogador" />

      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        <SecaoTitulo>🚦 ACWR por Jogador</SecaoTitulo>
        <div style={{ marginBottom: espaco.xxl, maxWidth: 480 }}>
          <AcwrList dados={dados.acwr} />
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: espaco.md }}>
          <h2 className="font-display" style={{ fontSize: "1rem", fontWeight: 600, color: "white", margin: 0 }}>
            📈 Evolução ao Longo do Tempo
          </h2>
          <IntervaloMicrociclos opcoes={dados.microciclos_disponiveis} inicio={inicioNum} fim={fimNum} />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: espaco.lg, marginBottom: espaco.lg }}>
          <GraficoEvolucao
            titulo="Carga Interna"
            unidade="UA"
            cor={cores.cargaInterna}
            pontos={dados.ci_evolucao.map((p) => ({ microciclo: p.microciclo, valor: p.carga_interna_media }))}
          />
          <GraficoMonotonia pontos={dados.monotonia_evolucao} />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: espaco.lg, marginBottom: espaco.xxl }}>
          {Object.entries(dados.carga_externa_evolucao).map(([chave, pontos]) => {
            const cfg = LABEL_EXTERNA[chave];
            if (!cfg) return null;
            return (
              <GraficoEvolucao key={chave} titulo={cfg.label} unidade={cfg.unidade} cor={cfg.cor} pontos={pontos} />
            );
          })}
        </div>

        <SecaoTitulo>🏃 Perfil de Carga Externa — por Jogador</SecaoTitulo>
        {dados.load_profile.colunas.length > 0 ? (
          <div style={{ marginBottom: espaco.xxl }}>
            <PerfilCargaExternaGraficos colunas={dados.load_profile.colunas} linhas={linhasTabela} />
          </div>
        ) : (
          <p style={{ color: cores.textoSuave, fontSize: "0.85rem", marginBottom: espaco.xxl }}>Sem métricas GPS disponíveis.</p>
        )}

        <div>
          <SecaoTitulo>🩺 Estado dos Atletas</SecaoTitulo>
          <EstadoAtletas teamId={membro.team_id} estadosIniciais={estados} />
        </div>
      </div>
    </div>
  );
}

function GraficoEvolucao({
  titulo,
  unidade,
  cor,
  pontos,
}: {
  titulo: string;
  unidade: string;
  cor: string;
  pontos: { microciclo: number; valor: number }[];
}) {
  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: 12, padding: espaco.md }}>
      <div className="font-display" style={{ fontSize: "0.86rem", fontWeight: 700, color: "white", marginBottom: espaco.sm }}>
        {titulo}
      </div>
      {pontos.length > 0 ? (
        <PlotlyChart
          data={[
            {
              x: pontos.map((p) => p.microciclo),
              y: pontos.map((p) => p.valor),
              type: "scatter",
              mode: "lines+markers",
              line: { color: cor, width: 2.5 },
              marker: { size: 6, color: cor },
              fill: "tozeroy",
              fillcolor: `${cor}12`,
              hovertemplate: `Semana %{x}<br>${titulo}: %{y}${unidade ? " " + unidade : ""}<extra></extra>`,
            },
          ]}
          layout={{
            xaxis: { title: { text: "Microciclo" }, dtick: pontos.length > 20 ? 4 : 1 },
            yaxis: { title: { text: unidade ? `${titulo} (${unidade})` : titulo } },
          }}
          altura={220}
        />
      ) : (
        <p style={{ color: cores.textoSuave, fontSize: "0.85rem" }}>Sem dados suficientes.</p>
      )}
    </div>
  );
}

function GraficoMonotonia({ pontos }: { pontos: { microciclo: number; monotonia_media: number }[] }) {
  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: 12, padding: espaco.md }}>
      <div className="font-display" style={{ fontSize: "0.86rem", fontWeight: 700, color: "white", marginBottom: espaco.sm }}>
        Monotonia
      </div>
      {pontos.length > 0 ? (
        <PlotlyChart
          data={[
            {
              x: pontos.map((p) => p.microciclo),
              y: pontos.map((p) => p.monotonia_media),
              type: "scatter",
              mode: "lines+markers",
              line: { color: cores.destaque, width: 2.5 },
              marker: { size: 6, color: cores.destaque },
              hovertemplate: "Semana %{x}<br>Monotonia: %{y:.2f}<extra></extra>",
              showlegend: false,
            },
            {
              x: pontos.map((p) => p.microciclo),
              y: pontos.map(() => 2),
              type: "scatter",
              mode: "lines",
              line: { color: "rgba(245,158,11,0.4)", width: 1, dash: "dot" },
              hoverinfo: "skip",
              showlegend: false,
            },
          ]}
          layout={{
            xaxis: { title: { text: "Microciclo" }, dtick: pontos.length > 20 ? 4 : 1 },
            yaxis: { title: { text: "Monotonia" } },
            annotations: [
              {
                x: 1, xref: "paper", y: 2, yref: "y",
                text: "zona de risco (>2)", showarrow: false,
                xanchor: "right", yanchor: "bottom",
                font: { size: 9, color: "rgba(245,158,11,0.7)" },
              },
            ],
          }}
          altura={220}
        />
      ) : (
        <p style={{ color: cores.textoSuave, fontSize: "0.85rem" }}>Sem dados suficientes.</p>
      )}
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
