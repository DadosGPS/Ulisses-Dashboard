import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { KpiTile } from "@/components/ui/KpiTile";
import { RankingCargaGrafico } from "@/components/ui/RankingCargaGrafico";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { CompararMicrocicloSelector } from "@/components/ui/AnaliseSeletores";
import { ComparacaoMicrociclos } from "@/components/ui/ComparacaoMicrociclos";
import { NomeJogador } from "@/components/ui/NomeJogador";
import { AlertasPrioritarios } from "@/components/ui/AlertasPrioritarios";
import { cores, espaco, raio } from "@/lib/theme";
import type { AnaliseResponse } from "@/lib/types";
import type { Data } from "plotly.js";

async function obterAnalise(
  teamId: string,
  accessToken: string,
  microciclo?: string,
  diaMd?: string,
  jogador?: string,
  comparar?: string
): Promise<AnaliseResponse> {
  const url = new URL(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/analise`);
  if (microciclo) url.searchParams.set("microciclo", microciclo);
  if (diaMd) url.searchParams.set("dia_md", diaMd);
  if (jogador) url.searchParams.set("jogador", jogador);
  if (comparar) url.searchParams.set("comparar", comparar);
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Falha ao carregar a análise (${res.status}).`);
  }
  return res.json();
}

export default async function AnalisePage({
  searchParams,
}: {
  searchParams: Promise<{ microciclo?: string; dia_md?: string; jogador?: string; comparar?: string }>;
}) {
  const { microciclo, dia_md, jogador, comparar } = await searchParams;

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

  let dados: AnaliseResponse;
  try {
    dados = await obterAnalise(membro.team_id, session.access_token, microciclo, dia_md, jogador, comparar);
  } catch {
    return <EstadoVazio mensagem="Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr." />;
  }

  if (!dados.tem_dados) {
    return (
      <EstadoVazio mensagem="Ainda não há dados carregados para esta equipa.">
        <Link
          href="/upload"
          style={{
            display: "inline-block",
            marginTop: 16,
            padding: "10px 20px",
            background: cores.cargaInterna,
            borderRadius: 8,
            color: "white",
            fontWeight: 700,
            fontSize: "0.85rem",
            textDecoration: "none",
          }}
        >
          📤 Carregar dados
        </Link>
      </EstadoVazio>
    );
  }

  const cargaLabel = dados.dia_md_selecionado
    ? `média de ${dados.dia_md_selecionado}`
    : "carga semanal total média";

  return (
    <div>
      <PageHeader
        titulo="Análise"
        subtitulo={[
          dados.jogador_selecionado ?? "Toda a equipa",
          dados.microciclo_selecionado ? `Semana ${dados.microciclo_selecionado}` : null,
          dados.microciclo_comparar ? `vs Semana ${dados.microciclo_comparar}` : null,
        ]
          .filter(Boolean)
          .join(" · ")}
        acoes={
          <CompararMicrocicloSelector
            opcoes={dados.microciclos_disponiveis}
            atual={dados.microciclo_comparar}
            microcicloSelecionado={dados.microciclo_selecionado}
          />
        }
      />

      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        <AlertasPrioritarios prioritarios={dados.alertas.prioritarios} indisponiveis={dados.alertas.indisponiveis} />

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: espaco.md, marginBottom: espaco.xxl }}>
          <KpiTile
            label="Carga Interna"
            valor={dados.carga_interna_media ?? "—"}
            unidade="UA"
            subLabel={cargaLabel}
            cor={cores.cargaInterna}
          />
          <KpiTile
            label="Carga Máxima"
            valor={dados.carga_maxima?.valor ?? "—"}
            unidade="UA"
            subLabel={dados.carga_maxima ? <NomeJogador nome={dados.carga_maxima.jogador} /> : "—"}
            cor={cores.perigo}
          />
          <KpiTile
            label="Carga Mínima"
            valor={dados.carga_minima?.valor ?? "—"}
            unidade="UA"
            subLabel={dados.carga_minima ? <NomeJogador nome={dados.carga_minima.jogador} /> : "—"}
            cor={cores.info}
          />
          <KpiTile
            label="Monotonia / Strain"
            valor={dados.monotonia_media ?? "—"}
            unidade={dados.strain_medio ? `· Strain ${dados.strain_medio.toLocaleString("pt-PT")}` : ""}
            subLabel="médias da equipa · semana completa"
            cor={cores.destaque}
          />
        </div>

        <div style={{ marginBottom: espaco.xxl }}>
          <SecaoTitulo>🗣️ RPE por Dia · atingido vs esperado</SecaoTitulo>
          <GraficoRpeDia
            pseReal={dados.pse_por_dia}
            pseEsperada={dados.pse_esperada_por_dia}
          />
        </div>

        {dados.comparacao && (
          <div style={{ marginBottom: espaco.xxl }}>
            <SecaoTitulo>⚖️ Comparação de Microciclos</SecaoTitulo>
            <ComparacaoMicrociclos a={dados.comparacao.a} b={dados.comparacao.b} />
          </div>
        )}

        {dados.comparacao && dados.comparacao.por_jogador.length > 0 && (
          <div style={{ marginBottom: espaco.xxl }}>
            <SecaoTitulo>
              👤 Carga por Jogador · Semana {dados.microciclo_selecionado} vs {dados.microciclo_comparar}
            </SecaoTitulo>
            <GraficoCargaPorJogador
              porJogador={dados.comparacao.por_jogador}
              semanaA={dados.microciclo_selecionado}
              semanaB={dados.microciclo_comparar}
            />
          </div>
        )}

        {!dados.jogador_selecionado && (
          <>
            <SecaoTitulo>🏆 Ranking de Atletas por Carga</SecaoTitulo>
            <RankingCargaGrafico linhas={dados.ranking_carga} label={cargaLabel} unidade="UA" cor="#2563eb" />
          </>
        )}
      </div>
    </div>
  );
}

// Paleta dos gráficos de relatório (fundo branco) — validada para daltonismo
// e contraste com o validador do skill dataviz (ΔE 32, contraste ≥ 3:1).
const COR_ATINGIDO = "#2563eb"; // azul — RPE atingido / semana atual
const COR_ESPERADO = "#d97706"; // âmbar — RPE esperado / semana anterior
const TINTA = "#1e293b"; // texto escuro para fundo branco
const TINTA_SUAVE = "#334155";
const GRELHA = "#e2e8f0";

// Base de layout para gráficos de relatório em fundo branco — sobrepõe-se ao
// plotlyLayoutBase (que é escuro) para os gráficos ficarem prontos a colar em
// documentos/relatórios.
const layoutBranco = {
  paper_bgcolor: "#ffffff",
  plot_bgcolor: "#ffffff",
  font: { family: "Inter, Segoe UI, Arial, sans-serif", color: TINTA },
};

// Cartão branco que envolve cada gráfico de relatório.
const cartaoBranco: React.CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e2e8f0",
  borderRadius: raio.md,
  padding: espaco.md,
};

// RPE por dia: barras = RPE atingido, linha = RPE esperado (planeado). Eixo
// único (PSE /10), com os valores da PSE nas etiquetas — pronto para relatório.
function GraficoRpeDia({
  pseReal,
  pseEsperada,
}: {
  pseReal: { dia_md: string; pse_media: number }[];
  pseEsperada: { dia_md: string; pse_esperada: number }[];
}) {
  if (pseReal.length === 0 && pseEsperada.length === 0) return <SemDados />;
  const dias = (pseReal.length ? pseReal : pseEsperada).map((d) => d.dia_md);
  const realMap = new Map(pseReal.map((d) => [d.dia_md, d.pse_media]));
  const espMap = new Map(pseEsperada.map((d) => [d.dia_md, d.pse_esperada]));
  const atingido = dias.map((d) => realMap.get(d) ?? null);
  const esperado = dias.map((d) => espMap.get(d) ?? null);
  const rotulo = (v: number | null) => (v == null ? "" : v.toLocaleString("pt-PT"));

  const data: Data[] = [
    {
      x: dias,
      y: atingido,
      type: "bar",
      name: "RPE atingido",
      marker: { color: COR_ATINGIDO },
      text: atingido.map(rotulo),
      textposition: "outside",
      textfont: { color: TINTA, size: 13 },
      cliponaxis: false,
      hovertemplate: "%{x}<br>RPE atingido %{y}<extra></extra>",
    },
  ];
  if (esperado.some((v) => v !== null)) {
    data.push({
      x: dias,
      y: esperado,
      type: "scatter",
      mode: "text+lines+markers",
      name: "RPE esperado",
      line: { color: COR_ESPERADO, width: 3 },
      marker: { size: 9, color: COR_ESPERADO },
      text: esperado.map(rotulo),
      textposition: "top center",
      textfont: { color: COR_ESPERADO, size: 12 },
      connectgaps: true,
      hovertemplate: "%{x}<br>RPE esperado %{y}<extra></extra>",
    });
  }

  return (
    <div style={cartaoBranco}>
      <PlotlyChart
        titulo="RPE por dia — atingido vs esperado"
        data={data}
        layout={{
          ...layoutBranco,
          barmode: "group",
          xaxis: { type: "category", categoryorder: "array", categoryarray: dias, tickfont: { size: 12, color: TINTA_SUAVE }, linecolor: "#cbd5e1" },
          yaxis: { title: { text: "PSE (/10)" }, range: [0, 10], gridcolor: GRELHA, tickfont: { size: 11, color: TINTA_SUAVE }, zeroline: false },
          legend: { orientation: "h", y: 1.15, font: { color: TINTA_SUAVE } },
          margin: { l: 48, r: 24, t: 42, b: 40 },
        }}
        altura={300}
      />
    </div>
  );
}

// Comparação da Carga Interna por jogador entre duas semanas — barras
// HORIZONTAIS com altura adaptativa para caberem TODOS os jogadores de forma
// legível (na janela grande dá para colar no relatório).
function GraficoCargaPorJogador({
  porJogador,
  semanaA,
  semanaB,
}: {
  porJogador: { jogador: string; a: number; b: number }[];
  semanaA: number | null;
  semanaB: number | null;
}) {
  if (porJogador.length === 0) return <SemDados />;
  // Em barras horizontais o Plotly desenha o 1.º item em baixo — ordenar
  // ascendente pela semana atual põe o maior no topo.
  const ordenadas = [...porJogador].sort((a, b) => a.a - b.a);
  const nomes = ordenadas.map((p) => p.jogador);
  const rotulo = (v: number) => (v ? v.toLocaleString("pt-PT") : "");
  const altura = Math.max(300, ordenadas.length * 44 + 90);

  return (
    <div style={cartaoBranco}>
      <PlotlyChart
        titulo={`Carga por jogador — Semana ${semanaA ?? ""} vs ${semanaB ?? ""}`}
        data={[
          {
            x: ordenadas.map((p) => p.a),
            y: nomes,
            type: "bar",
            orientation: "h",
            name: `Semana ${semanaA ?? "atual"}`,
            marker: { color: COR_ATINGIDO },
            text: ordenadas.map((p) => rotulo(p.a)),
            textposition: "outside",
            textfont: { color: TINTA, size: 11 },
            cliponaxis: false,
            hovertemplate: "%{y}<br>%{x:,} UA<extra>Semana atual</extra>",
          },
          {
            x: ordenadas.map((p) => p.b),
            y: nomes,
            type: "bar",
            orientation: "h",
            name: `Semana ${semanaB ?? "anterior"}`,
            marker: { color: COR_ESPERADO },
            text: ordenadas.map((p) => rotulo(p.b)),
            textposition: "outside",
            textfont: { color: TINTA, size: 11 },
            cliponaxis: false,
            hovertemplate: "%{y}<br>%{x:,} UA<extra>Semana anterior</extra>",
          },
        ]}
        layout={{
          ...layoutBranco,
          barmode: "group",
          xaxis: { title: { text: "Carga Interna (UA)" }, gridcolor: GRELHA, tickfont: { size: 11, color: TINTA_SUAVE }, zeroline: false },
          yaxis: { type: "category", automargin: true, tickfont: { size: 11, color: TINTA_SUAVE } },
          legend: { orientation: "h", y: 1.03, font: { color: TINTA_SUAVE } },
          margin: { l: 8, r: 64, t: 30, b: 44 },
          bargap: 0.3,
          bargroupgap: 0.15,
        }}
        altura={altura}
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

function SemDados() {
  return <p style={{ color: cores.textoSuave, fontSize: "0.85rem" }}>Sem dados suficientes.</p>;
}

function EstadoVazio({ mensagem, children }: { mensagem: string; children?: React.ReactNode }) {
  return (
    <div style={{ maxWidth: 600, margin: "80px auto", padding: "0 24px", textAlign: "center" }}>
      <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.95rem" }}>{mensagem}</p>
      {children}
    </div>
  );
}
