import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { LoadProfileTable, type ColunaCarga, type LinhaCarga } from "@/components/ui/LoadProfileTable";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { cores, espaco, raio } from "@/lib/theme";

interface MetricaDef {
  chave: string;
  label: string;
  unidade: string;
  cor: string;
  casas: number;
}

interface PosicaoRow {
  posicao: string;
  n_jogadores: number;
  n_sessoes: number;
  valores: Record<string, number | null>;
}

interface ComparacaoPosicoesResponse {
  tem_dados: boolean;
  metricas: MetricaDef[];
  posicoes: PosicaoRow[];
  benchmark: Record<string, number | null>;
}

async function obterDados(teamId: string, accessToken: string): Promise<ComparacaoPosicoesResponse> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/comparacao/posicoes`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Falha (${res.status}).`);
  return res.json();
}

export default async function PosicaoPage() {
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

  let dados: ComparacaoPosicoesResponse;
  try {
    dados = await obterDados(membro.team_id, session.access_token);
  } catch {
    return <EstadoVazio mensagem="Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr." />;
  }

  if (!dados.tem_dados || dados.posicoes.length === 0) {
    return (
      <div>
        <PageHeader titulo="Comparação por Posição" subtitulo="Médias por posição táctica" />
        <EstadoVazio mensagem="Ainda não há dados com posições definidas. Define a posição dos jogadores e carrega sessões de GPS." />
      </div>
    );
  }

  const colunas: ColunaCarga[] = [
    { chave: "__n", label: "Jogadores", cor: cores.destaque, casas: 0 },
    ...dados.metricas.map((m) => ({ chave: m.chave, label: m.label, cor: m.cor, casas: m.casas })),
  ];
  const linhas: LinhaCarga[] = dados.posicoes.map((p) => ({
    jogador: p.posicao,
    valores: { __n: p.n_jogadores, ...p.valores },
  }));

  return (
    <div>
      <PageHeader
        titulo="Comparação por Posição"
        subtitulo="Média por jogador (época), agregada por posição táctica"
      />

      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        <SecaoTitulo>📊 Tabela por Posição</SecaoTitulo>
        <p style={{ color: cores.textoSuave, fontSize: "0.78rem", margin: `0 0 ${espaco.md}px` }}>
          Cada valor é a média por jogador dessa posição. Cor mais intensa = valor mais alto na coluna.
        </p>
        <div style={{ marginBottom: espaco.xxl }}>
          <LoadProfileTable colunas={colunas} linhas={linhas} labelLinha="Posição" />
        </div>

        <SecaoTitulo>📈 Comparação por Métrica</SecaoTitulo>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
            gap: espaco.lg,
          }}
        >
          {dados.metricas.map((m) => (
            <GraficoPosicao key={m.chave} metrica={m} posicoes={dados.posicoes} benchmark={dados.benchmark[m.chave]} />
          ))}
        </div>
      </div>
    </div>
  );
}

function GraficoPosicao({
  metrica,
  posicoes,
  benchmark,
}: {
  metrica: MetricaDef;
  posicoes: PosicaoRow[];
  benchmark: number | null;
}) {
  const dados = posicoes
    .map((p) => ({ posicao: p.posicao, valor: p.valores[metrica.chave] }))
    .filter((d): d is { posicao: string; valor: number } => d.valor !== null && d.valor !== undefined);

  if (dados.length === 0) return null;

  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
      <div className="font-display" style={{ fontSize: "0.86rem", fontWeight: 700, color: "white", marginBottom: espaco.sm }}>
        {metrica.label} <span style={{ color: cores.textoSuave, fontWeight: 500 }}>({metrica.unidade})</span>
      </div>
      <PlotlyChart
        data={[
          {
            x: dados.map((d) => d.posicao),
            y: dados.map((d) => d.valor),
            type: "bar",
            marker: { color: metrica.cor },
            text: dados.map((d) => d.valor.toLocaleString("pt-PT", { maximumFractionDigits: metrica.casas })),
            textposition: "outside",
            hovertemplate: `%{x}<br>${metrica.label}: %{y} ${metrica.unidade}<extra></extra>`,
          },
        ]}
        layout={{
          yaxis: { title: { text: metrica.unidade } },
          ...(benchmark
            ? {
                shapes: [
                  {
                    type: "line",
                    x0: -0.5,
                    x1: dados.length - 0.5,
                    y0: benchmark,
                    y1: benchmark,
                    line: { color: "rgba(255,255,255,0.4)", width: 1, dash: "dot" },
                  },
                ],
                annotations: [
                  {
                    x: 1,
                    xref: "paper",
                    y: benchmark,
                    yref: "y",
                    text: "média equipa",
                    showarrow: false,
                    xanchor: "right",
                    yanchor: "bottom",
                    font: { size: 9, color: "rgba(255,255,255,0.5)" },
                  },
                ],
              }
            : {}),
        }}
        altura={220}
      />
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
