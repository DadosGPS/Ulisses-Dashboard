import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { AcwrList } from "@/components/ui/AcwrList";
import { IntervaloMicrociclos } from "@/components/ui/IntervaloMicrociclos";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { cores, espaco } from "@/lib/theme";
import type { EquipaResponse } from "@/lib/types";

// Cores de relatório (fundo branco) — contraste ≥ 3:1 validado com o skill dataviz.
const LABEL_EXTERNA: Record<string, { label: string; unidade: string; cor: string }> = {
  distancia_total_m: { label: "Distância Total", unidade: "m", cor: "#2563eb" },
  hsr_m: { label: "HSR", unidade: "m", cor: "#d97706" },
  sprint_m: { label: "Sprint", unidade: "m", cor: "#dc2626" },
  acc_n: { label: "Acelerações", unidade: "", cor: "#0d9488" },
  dcc_n: { label: "Desacelerações", unidade: "", cor: "#059669" },
  vel_max_kmh: { label: "Vel. Máxima", unidade: "km/h", cor: "#7c3aed" },
};
const COR_CARGA_INTERNA = "#dc2626"; // carga interna (evolução) em fundo branco
const COR_MONOTONIA = "#7c3aed";

// Estilo de relatório (fundo branco) para os gráficos de evolução da Época.
const TINTA = "#1e293b";
const TINTA_SUAVE = "#334155";
const GRELHA = "#e2e8f0";
const layoutBranco = {
  paper_bgcolor: "#ffffff",
  plot_bgcolor: "#ffffff",
  font: { family: "Inter, Segoe UI, Arial, sans-serif", color: TINTA },
};
const cartaoBranco: React.CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e2e8f0",
  borderRadius: 12,
  padding: 16,
};

async function obterEquipa(teamId: string, accessToken: string, microInicio?: string, microFim?: string): Promise<EquipaResponse> {
  const url = new URL(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/equipa`);
  if (microInicio) url.searchParams.set("micro_inicio", microInicio);
  if (microFim) url.searchParams.set("micro_fim", microFim);
  const res = await fetch(url, { headers: { Authorization: `Bearer ${accessToken}` }, cache: "no-store" });
  if (!res.ok) throw new Error(`Falha ao carregar a época (${res.status}).`);
  return res.json();
}

export default async function EpocaPage({
  searchParams,
}: {
  searchParams: Promise<{ micro_inicio?: string; micro_fim?: string }>;
}) {
  const { micro_inicio, micro_fim } = await searchParams;

  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;

  const { data: membro } = await supabase
    .from("team_members").select("team_id").eq("user_id", session.user.id).limit(1).single();
  if (!membro) return <EstadoVazio mensagem="Ainda não estás associado a nenhuma equipa." />;

  let dados: EquipaResponse;
  try {
    dados = await obterEquipa(membro.team_id, session.access_token, micro_inicio, micro_fim);
  } catch {
    return <EstadoVazio mensagem="Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr." />;
  }
  if (!dados.tem_dados) {
    return (
      <div>
        <PageHeader titulo="Época" subtitulo="Evolução da carga ao longo dos microciclos" />
        <EstadoVazio mensagem="Ainda não há dados carregados para esta equipa." />
      </div>
    );
  }

  const inicioNum = micro_inicio ? Number(micro_inicio) : null;
  const fimNum = micro_fim ? Number(micro_fim) : null;

  return (
    <div>
      <PageHeader titulo="Época" subtitulo="Evolução da carga ao longo dos microciclos — visão longitudinal" />

      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {/* Seletor de semanas — governa TODA a página (ACWR + evolução). */}
        <div style={{ display: "flex", alignItems: "center", gap: espaco.md, flexWrap: "wrap", marginBottom: espaco.lg }}>
          <span style={{ fontSize: "0.85rem", fontWeight: 600, color: cores.textoSuave }}>🗓️ Semanas em análise:</span>
          <IntervaloMicrociclos opcoes={dados.microciclos_disponiveis} inicio={inicioNum} fim={fimNum} />
        </div>

        <SecaoTitulo>🚦 ACWR por jogador</SecaoTitulo>
        <p style={{ fontSize: "0.82rem", color: cores.textoSuave, margin: `-6px 0 ${espaco.sm}px` }}>
          {dados.acwr_intervalo.inicio != null
            ? `Calculado com as semanas ${dados.acwr_intervalo.inicio}–${dados.acwr_intervalo.fim} (${dados.acwr_intervalo.n_semanas} ${dados.acwr_intervalo.n_semanas === 1 ? "semana" : "semanas"}).`
            : "Calculado com todas as semanas disponíveis."}
        </p>
        {dados.acwr_poucas_semanas && (
          <div style={{ maxWidth: 480, marginBottom: espaco.md, padding: `9px ${espaco.md}px`, background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.35)", borderRadius: 8, fontSize: "0.8rem", color: cores.texto }}>
            ⚠️ Poucas semanas selecionadas para o ACWR. A carga crónica precisa de ~4 semanas de histórico — com menos, o valor pode não ser fiável. Alarga o intervalo para maior rigor.
          </div>
        )}
        <div style={{ marginBottom: espaco.xxl, maxWidth: 480 }}>
          <AcwrList dados={dados.acwr} />
        </div>

        <h2 className="font-display" style={{ fontSize: "1rem", fontWeight: 600, color: "white", margin: `0 0 ${espaco.md}px` }}>
          📈 Evolução ao longo do tempo
        </h2>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: espaco.lg, marginBottom: espaco.lg }}>
          <GraficoEvolucao titulo="Carga Interna" unidade="UA" cor={COR_CARGA_INTERNA} pontos={dados.ci_evolucao.map((p) => ({ microciclo: p.microciclo, valor: p.carga_interna_media }))} />
          <GraficoMonotonia pontos={dados.monotonia_evolucao} />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: espaco.lg }}>
          {Object.entries(dados.carga_externa_evolucao).map(([chave, pontos]) => {
            const cfg = LABEL_EXTERNA[chave];
            if (!cfg) return null;
            return <GraficoEvolucao key={chave} titulo={cfg.label} unidade={cfg.unidade} cor={cfg.cor} pontos={pontos} />;
          })}
        </div>
      </div>
    </div>
  );
}

function GraficoEvolucao({ titulo, unidade, cor, pontos }: { titulo: string; unidade: string; cor: string; pontos: { microciclo: number; valor: number }[] }) {
  return (
    <div style={cartaoBranco}>
      <div className="font-display" style={{ fontSize: "0.86rem", fontWeight: 700, color: TINTA, marginBottom: espaco.sm }}>{titulo}</div>
      {pontos.length > 0 ? (
        <PlotlyChart
          titulo={titulo}
          data={[{
            x: pontos.map((p) => p.microciclo), y: pontos.map((p) => p.valor),
            type: "scatter", mode: "lines+markers", line: { color: cor, width: 2.5 }, marker: { size: 6, color: cor },
            fill: "tozeroy", fillcolor: `${cor}1f`,
            hovertemplate: `Semana %{x}<br>${titulo}: %{y}${unidade ? " " + unidade : ""}<extra></extra>`,
          }]}
          layout={{
            ...layoutBranco,
            xaxis: { title: { text: "Microciclo" }, dtick: pontos.length > 20 ? 4 : 1, gridcolor: GRELHA, tickfont: { size: 11, color: TINTA_SUAVE }, zeroline: false },
            yaxis: { title: { text: unidade ? `${titulo} (${unidade})` : titulo }, gridcolor: GRELHA, tickfont: { size: 11, color: TINTA_SUAVE }, zeroline: false },
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
    <div style={cartaoBranco}>
      <div className="font-display" style={{ fontSize: "0.86rem", fontWeight: 700, color: TINTA, marginBottom: espaco.sm }}>Monotonia</div>
      {pontos.length > 0 ? (
        <PlotlyChart
          titulo="Monotonia"
          data={[
            { x: pontos.map((p) => p.microciclo), y: pontos.map((p) => p.monotonia_media), type: "scatter", mode: "lines+markers", line: { color: COR_MONOTONIA, width: 2.5 }, marker: { size: 6, color: COR_MONOTONIA }, hovertemplate: "Semana %{x}<br>Monotonia: %{y:.2f}<extra></extra>", showlegend: false },
            { x: pontos.map((p) => p.microciclo), y: pontos.map(() => 2), type: "scatter", mode: "lines", line: { color: "rgba(217,119,6,0.7)", width: 1.5, dash: "dot" }, hoverinfo: "skip", showlegend: false },
          ]}
          layout={{
            ...layoutBranco,
            xaxis: { title: { text: "Microciclo" }, dtick: pontos.length > 20 ? 4 : 1, gridcolor: GRELHA, tickfont: { size: 11, color: TINTA_SUAVE }, zeroline: false },
            yaxis: { title: { text: "Monotonia" }, gridcolor: GRELHA, tickfont: { size: 11, color: TINTA_SUAVE }, zeroline: false },
            annotations: [{ x: 1, xref: "paper", y: 2, yref: "y", text: "zona de risco (>2)", showarrow: false, xanchor: "right", yanchor: "bottom", font: { size: 9, color: "#b45309" } }],
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
  return <h2 className="font-display" style={{ fontSize: "1rem", fontWeight: 600, color: "white", margin: `0 0 ${espaco.md}px` }}>{children}</h2>;
}

function EstadoVazio({ mensagem }: { mensagem: string }) {
  return (
    <div style={{ maxWidth: 600, margin: "80px auto", padding: "0 24px", textAlign: "center" }}>
      <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.95rem" }}>{mensagem}</p>
    </div>
  );
}
