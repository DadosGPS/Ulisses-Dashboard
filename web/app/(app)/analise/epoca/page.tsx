import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { AcwrList } from "@/components/ui/AcwrList";
import { IntervaloMicrociclos } from "@/components/ui/IntervaloMicrociclos";
import { SeletorJogadorEpoca } from "@/components/ui/SeletorJogadorEpoca";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { MapaCalorEpoca } from "@/components/ui/MapaCalorEpoca";
import { cores, espaco } from "@/lib/theme";
import type { EquipaResponse, MapaCalorResponse } from "@/lib/types";
import type { Data } from "plotly.js";

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

async function obterEquipa(teamId: string, accessToken: string, microInicio?: string, microFim?: string, jogador?: string): Promise<EquipaResponse> {
  const url = new URL(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/equipa`);
  if (microInicio) url.searchParams.set("micro_inicio", microInicio);
  if (microFim) url.searchParams.set("micro_fim", microFim);
  if (jogador) url.searchParams.set("jogador", jogador);
  const res = await fetch(url, { headers: { Authorization: `Bearer ${accessToken}` }, cache: "no-store" });
  if (!res.ok) throw new Error(`Falha ao carregar a época (${res.status}).`);
  return res.json();
}

async function obterMapaCalor(teamId: string, accessToken: string): Promise<MapaCalorResponse | null> {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/mapa-calor`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function EpocaPage({
  searchParams,
}: {
  searchParams: Promise<{ micro_inicio?: string; micro_fim?: string; jogador?: string }>;
}) {
  const { micro_inicio, micro_fim, jogador } = await searchParams;

  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;

  const { data: membro } = await supabase
    .from("team_members").select("team_id").eq("user_id", session.user.id).limit(1).single();
  if (!membro) return <EstadoVazio mensagem="Ainda não estás associado a nenhuma equipa." />;

  let dados: EquipaResponse;
  try {
    dados = await obterEquipa(membro.team_id, session.access_token, micro_inicio, micro_fim, jogador);
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

  const mapa = await obterMapaCalor(membro.team_id, session.access_token);

  const inicioNum = micro_inicio ? Number(micro_inicio) : null;
  const fimNum = micro_fim ? Number(micro_fim) : null;

  return (
    <div>
      <PageHeader titulo="Época" subtitulo="Evolução da carga ao longo dos microciclos — visão longitudinal" />

      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {/* Seletor de semanas — governa TODA a página (ACWR + evolução). */}
        <div style={{ display: "flex", alignItems: "center", gap: espaco.lg, flexWrap: "wrap", marginBottom: espaco.lg }}>
          <div style={{ display: "flex", alignItems: "center", gap: espaco.md }}>
            <span style={{ fontSize: "0.85rem", fontWeight: 600, color: cores.textoSuave }}>🗓️ Semanas em análise:</span>
            <IntervaloMicrociclos opcoes={dados.microciclos_disponiveis} inicio={inicioNum} fim={fimNum} />
          </div>
          <SeletorJogadorEpoca jogadores={dados.jogadores_disponiveis} jogador={dados.jogador_selecionado} />
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

        {mapa && mapa.tem_dados && (
          <div style={{ marginBottom: espaco.xxl }}>
            <SecaoTitulo>🗺️ Mapa de calor da época</SecaoTitulo>
            <MapaCalorEpoca dados={mapa} />
          </div>
        )}

        <h2 className="font-display" style={{ fontSize: "1rem", fontWeight: 600, color: "white", margin: `0 0 4px` }}>
          📈 Evolução ao longo do tempo
        </h2>
        <p style={{ fontSize: "0.82rem", color: cores.textoSuave, margin: `0 0 ${espaco.md}px` }}>
          {dados.jogador_selecionado
            ? `${dados.jogador_selecionado} (linha a cor) vs média da equipa (linha cinza, referência).`
            : "Média da equipa por microciclo. Escolhe um jogador para ver a evolução dele face à equipa."}
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: espaco.lg, marginBottom: espaco.lg }}>
          <GraficoEvolucao
            titulo="Carga Interna"
            unidade="UA"
            cor={COR_CARGA_INTERNA}
            pontos={dados.ci_evolucao.map((p) => ({ microciclo: p.microciclo, valor: p.carga_interna_media }))}
            pontosJogador={dados.jogador_selecionado ? dados.ci_evolucao_jogador.map((p) => ({ microciclo: p.microciclo, valor: p.carga_interna_media })) : undefined}
            nomeJogador={dados.jogador_selecionado}
          />
          <GraficoMonotonia
            pontos={dados.monotonia_evolucao}
            pontosJogador={dados.jogador_selecionado ? dados.monotonia_evolucao_jogador : undefined}
            nomeJogador={dados.jogador_selecionado}
          />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: espaco.lg }}>
          {Object.entries(dados.carga_externa_evolucao).map(([chave, pontos]) => {
            const cfg = LABEL_EXTERNA[chave];
            if (!cfg) return null;
            return (
              <GraficoEvolucao
                key={chave}
                titulo={cfg.label}
                unidade={cfg.unidade}
                cor={cfg.cor}
                pontos={pontos}
                pontosJogador={dados.jogador_selecionado ? dados.carga_externa_evolucao_jogador[chave] : undefined}
                nomeJogador={dados.jogador_selecionado}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}

// Cinza da linha de referência da equipa (quando um jogador está selecionado).
const COR_EQUIPA_REF = "#94a3b8";

function GraficoEvolucao({
  titulo, unidade, cor, pontos, pontosJogador, nomeJogador,
}: {
  titulo: string;
  unidade: string;
  cor: string;
  pontos: { microciclo: number; valor: number }[];
  pontosJogador?: { microciclo: number; valor: number }[];
  nomeJogador?: string | null;
}) {
  const temJogador = !!(pontosJogador && pontosJogador.length > 0);
  const data: Data[] = temJogador
    ? [
        // Equipa como referência de fundo (cinza, fina, sem preenchimento).
        {
          x: pontos.map((p) => p.microciclo), y: pontos.map((p) => p.valor),
          type: "scatter", mode: "lines", name: "Equipa (média)",
          line: { color: COR_EQUIPA_REF, width: 1.8, dash: "dot" },
          hovertemplate: `Semana %{x}<br>Equipa: %{y}${unidade ? " " + unidade : ""}<extra></extra>`,
        },
        // Jogador em destaque.
        {
          x: pontosJogador!.map((p) => p.microciclo), y: pontosJogador!.map((p) => p.valor),
          type: "scatter", mode: "lines+markers", name: nomeJogador ?? "Jogador",
          line: { color: cor, width: 2.5 }, marker: { size: 6, color: cor },
          hovertemplate: `Semana %{x}<br>${nomeJogador ?? "Jogador"}: %{y}${unidade ? " " + unidade : ""}<extra></extra>`,
        },
      ]
    : [
        {
          x: pontos.map((p) => p.microciclo), y: pontos.map((p) => p.valor),
          type: "scatter", mode: "lines+markers", line: { color: cor, width: 2.5 }, marker: { size: 6, color: cor },
          fill: "tozeroy", fillcolor: `${cor}1f`,
          hovertemplate: `Semana %{x}<br>${titulo}: %{y}${unidade ? " " + unidade : ""}<extra></extra>`,
        },
      ];

  const nPontos = Math.max(pontos.length, pontosJogador?.length ?? 0);
  return (
    <div style={cartaoBranco}>
      <div className="font-display" style={{ fontSize: "0.86rem", fontWeight: 700, color: TINTA, marginBottom: espaco.sm }}>{titulo}</div>
      {nPontos > 0 ? (
        <PlotlyChart
          titulo={titulo}
          data={data}
          layout={{
            ...layoutBranco,
            showlegend: temJogador,
            legend: { orientation: "h", y: 1.15, x: 0, font: { size: 10, color: TINTA_SUAVE } },
            xaxis: { title: { text: "Microciclo" }, dtick: nPontos > 20 ? 4 : 1, gridcolor: GRELHA, tickfont: { size: 11, color: TINTA_SUAVE }, zeroline: false },
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

function GraficoMonotonia({
  pontos, pontosJogador, nomeJogador,
}: {
  pontos: { microciclo: number; monotonia_media: number }[];
  pontosJogador?: { microciclo: number; monotonia_media: number }[];
  nomeJogador?: string | null;
}) {
  const temJogador = !!(pontosJogador && pontosJogador.length > 0);
  const nPontos = Math.max(pontos.length, pontosJogador?.length ?? 0);
  const eixoX = nPontos > 0 ? (temJogador ? pontosJogador! : pontos).map((p) => p.microciclo) : [];

  const linhas: Data[] = [];
  if (temJogador) {
    linhas.push({
      x: pontos.map((p) => p.microciclo), y: pontos.map((p) => p.monotonia_media),
      type: "scatter", mode: "lines", name: "Equipa (média)",
      line: { color: COR_EQUIPA_REF, width: 1.8, dash: "dot" },
      hovertemplate: "Semana %{x}<br>Equipa: %{y:.2f}<extra></extra>",
    });
    linhas.push({
      x: pontosJogador!.map((p) => p.microciclo), y: pontosJogador!.map((p) => p.monotonia_media),
      type: "scatter", mode: "lines+markers", name: nomeJogador ?? "Jogador",
      line: { color: COR_MONOTONIA, width: 2.5 }, marker: { size: 6, color: COR_MONOTONIA },
      hovertemplate: `Semana %{x}<br>${nomeJogador ?? "Jogador"}: %{y:.2f}<extra></extra>`,
    });
  } else {
    linhas.push({
      x: pontos.map((p) => p.microciclo), y: pontos.map((p) => p.monotonia_media),
      type: "scatter", mode: "lines+markers", line: { color: COR_MONOTONIA, width: 2.5 }, marker: { size: 6, color: COR_MONOTONIA },
      hovertemplate: "Semana %{x}<br>Monotonia: %{y:.2f}<extra></extra>", showlegend: false,
    });
  }
  // Linha da zona de risco (>2), sem entrada na legenda.
  linhas.push({
    x: eixoX, y: eixoX.map(() => 2), type: "scatter", mode: "lines",
    line: { color: "rgba(217,119,6,0.7)", width: 1.5, dash: "dot" }, hoverinfo: "skip", showlegend: false,
  });

  return (
    <div style={cartaoBranco}>
      <div className="font-display" style={{ fontSize: "0.86rem", fontWeight: 700, color: TINTA, marginBottom: espaco.sm }}>Monotonia</div>
      {nPontos > 0 ? (
        <PlotlyChart
          titulo="Monotonia"
          data={linhas}
          layout={{
            ...layoutBranco,
            showlegend: temJogador,
            legend: { orientation: "h", y: 1.15, x: 0, font: { size: 10, color: TINTA_SUAVE } },
            xaxis: { title: { text: "Microciclo" }, dtick: nPontos > 20 ? 4 : 1, gridcolor: GRELHA, tickfont: { size: 11, color: TINTA_SUAVE }, zeroline: false },
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
