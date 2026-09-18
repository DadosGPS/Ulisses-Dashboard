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
          <SecaoTitulo>📊 Carga & PSE por Dia</SecaoTitulo>
          <GraficoCargaPse
            carga={dados.carga_por_dia}
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
            <RankingCargaGrafico linhas={dados.ranking_carga} label={cargaLabel} unidade="UA" cor={cores.cargaInterna} />
          </>
        )}
      </div>
    </div>
  );
}

// Gráfico combinado: Carga (barras, eixo esquerdo) + PSE real e PSE esperada
// (linhas, eixo direito /10) — junta os dois gráficos antigos num só.
function GraficoCargaPse({
  carga,
  pseReal,
  pseEsperada,
}: {
  carga: { dia_md: string; carga_media: number }[];
  pseReal: { dia_md: string; pse_media: number }[];
  pseEsperada: { dia_md: string; pse_esperada: number }[];
}) {
  if (carga.length === 0) return <SemDados />;
  const dias = carga.map((d) => d.dia_md);
  const cargaVals = carga.map((d) => d.carga_media);
  const realMap = new Map(pseReal.map((d) => [d.dia_md, d.pse_media]));
  const espMap = new Map(pseEsperada.map((d) => [d.dia_md, d.pse_esperada]));
  const real = dias.map((d) => realMap.get(d) ?? null);
  const esp = dias.map((d) => espMap.get(d) ?? null);

  const data: Data[] = [
    {
      x: dias,
      y: cargaVals,
      type: "bar",
      name: "Carga Interna",
      marker: { color: cores.cargaInterna },
      text: cargaVals.map((v) => v.toLocaleString("pt-PT")),
      textposition: "outside",
      hovertemplate: "%{x}<br>%{y} UA<extra>Carga</extra>",
    },
    {
      x: dias,
      y: real,
      type: "scatter",
      mode: "lines+markers",
      name: "PSE real",
      yaxis: "y2",
      line: { color: cores.info, width: 3 },
      connectgaps: true,
      hovertemplate: "%{x}<br>PSE real %{y}<extra></extra>",
    },
  ];
  if (esp.some((v) => v !== null)) {
    data.push({
      x: dias,
      y: esp,
      type: "scatter",
      mode: "lines+markers",
      name: "PSE esperada",
      yaxis: "y2",
      line: { color: cores.atencao, width: 2, dash: "dash" },
      connectgaps: true,
      hovertemplate: "%{x}<br>PSE esperada %{y}<extra></extra>",
    });
  }

  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
      <PlotlyChart
        data={data}
        layout={{
          xaxis: { type: "category", categoryorder: "array", categoryarray: dias },
          yaxis: { title: { text: "Carga (UA)" } },
          yaxis2: { title: { text: "PSE (/10)" }, overlaying: "y", side: "right", range: [0, 10], showgrid: false },
          legend: { orientation: "h", y: 1.18 },
          margin: { l: 48, r: 48, t: 34, b: 36 },
        }}
        altura={260}
      />
    </div>
  );
}

// Comparação da Carga Interna por jogador entre duas semanas (barras agrupadas).
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
  const jogadores = porJogador.map((p) => p.jogador);

  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
      <PlotlyChart
        data={[
          {
            x: jogadores,
            y: porJogador.map((p) => p.a),
            type: "bar",
            name: `Semana ${semanaA ?? "atual"}`,
            marker: { color: cores.cargaInterna },
            hovertemplate: "%{x}<br>%{y} UA<extra>Semana atual</extra>",
          },
          {
            x: jogadores,
            y: porJogador.map((p) => p.b),
            type: "bar",
            name: `Semana ${semanaB ?? "anterior"}`,
            marker: { color: cores.info },
            hovertemplate: "%{x}<br>%{y} UA<extra>Semana anterior</extra>",
          },
        ]}
        layout={{
          barmode: "group",
          xaxis: { type: "category", tickangle: -40 },
          yaxis: { title: { text: "Carga Interna (UA)" } },
          legend: { orientation: "h", y: 1.12 },
          margin: { l: 54, r: 16, t: 30, b: 96 },
        }}
        altura={340}
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
