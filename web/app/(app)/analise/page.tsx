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

import { SecaoTitulo, EstadoVazio } from "@/components/ui/base";
import { obterEquipaAtiva } from "@/lib/equipa-ativa-servidor";
import { obterTr, obterLingua } from "@/lib/i18n/servidor";
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
    headers: { Authorization: `Bearer ${accessToken}`, "X-Lingua": await obterLingua() },
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
  const tr = await obterTr();
  const { microciclo, dia_md, jogador, comparar } = await searchParams;

  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) return null;

  const { data: membro } = await obterEquipaAtiva(supabase, session.user.id);

  if (!membro) {
    return <EstadoVazio mensagem={tr("Ainda não estás associado a nenhuma equipa.")} />;
  }

  let dados: AnaliseResponse;
  try {
    dados = await obterAnalise(membro.team_id, session.access_token, microciclo, dia_md, jogador, comparar);
  } catch {
    return <EstadoVazio mensagem={tr("Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr.")} />;
  }

  if (!dados.tem_dados) {
    return (
      <EstadoVazio acao={{ href: "/upload", label: tr("Importar GPS") }} mensagem={tr("Ainda não há dados carregados para esta equipa.")}>
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
          {tr("Carregar dados")}</Link>
      </EstadoVazio>
    );
  }

  const cargaLabel = dados.dia_md_selecionado
    ? tr("média de {0}", [dados.dia_md_selecionado])
    : tr("carga semanal total média");

  return (
    <div>
      <PageHeader
        titulo={tr("Análise")}
        subtitulo={[
          dados.jogador_selecionado ?? tr("Toda a equipa"),
          dados.microciclo_selecionado ? tr("Semana {0}", [dados.microciclo_selecionado]) : null,
          dados.microciclo_comparar ? tr("vs Semana {0}", [dados.microciclo_comparar]) : null,
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
            label={tr("Carga Interna")}
            valor={dados.carga_interna_media ?? "—"}
            unidade="UA"
            subLabel={cargaLabel}
            cor={cores.cargaInterna}
          />
          <KpiTile
            label={tr("Carga Máxima")}
            valor={dados.carga_maxima?.valor ?? "—"}
            unidade="UA"
            subLabel={dados.carga_maxima ? <NomeJogador nome={dados.carga_maxima.jogador} /> : "—"}
            cor={cores.perigo}
          />
          <KpiTile
            label={tr("Carga Mínima")}
            valor={dados.carga_minima?.valor ?? "—"}
            unidade="UA"
            subLabel={dados.carga_minima ? <NomeJogador nome={dados.carga_minima.jogador} /> : "—"}
            cor={cores.info}
          />
          <KpiTile
            label={tr("Monotonia / Strain")}
            valor={dados.monotonia_media ?? "—"}
            unidade={dados.strain_medio ? tr("· Strain {0}", [dados.strain_medio.toLocaleString(tr.loc)]) : ""}
            subLabel={tr("médias da equipa · semana completa")}
            cor={cores.destaque}
          />
        </div>

        <div style={{ marginBottom: espaco.xxl }}>
          <SecaoTitulo>{tr("RPE por Dia · atingido vs esperado")}</SecaoTitulo>
          <GraficoRpeDia
            pseReal={dados.pse_por_dia}
            pseEsperada={dados.pse_esperada_por_dia}
          />
        </div>

        {dados.comparacao && (
          <div style={{ marginBottom: espaco.xxl }}>
            <SecaoTitulo>{tr("Comparação de Microciclos")}</SecaoTitulo>
            <ComparacaoMicrociclos a={dados.comparacao.a} b={dados.comparacao.b} />
          </div>
        )}

        {dados.comparacao && dados.comparacao.por_jogador.length > 0 && (
          <div style={{ marginBottom: espaco.xxl }}>
            <SecaoTitulo>
              {tr("Carga por Jogador · Semana")}{" "}{dados.microciclo_selecionado} {tr("vs")}{" "}{dados.microciclo_comparar}
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
            <SecaoTitulo>{tr("Ranking de Atletas por Carga")}</SecaoTitulo>
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
const TINTA = cores.texto;
const TINTA_SUAVE = cores.textoSuave;
const GRELHA = cores.borda;

// Base de layout para gráficos de relatório em fundo branco — sobrepõe-se ao
// plotlyLayoutBase (que é escuro) para os gráficos ficarem prontos a colar em
// documentos/relatórios.
const layoutBranco = {
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: { family: "Inter, Segoe UI, Arial, sans-serif", color: TINTA },
};

// Cartão branco que envolve cada gráfico de relatório.
const cartaoBranco: React.CSSProperties = {
  background: cores.bgCartao,
  border: `1px solid ${cores.borda}`,
  borderRadius: raio.md,
  padding: espaco.md,
};

// RPE por dia: barras = RPE atingido, linha = RPE esperado (planeado). Eixo
// único (PSE /10), com os valores da PSE nas etiquetas — pronto para relatório.
async function GraficoRpeDia({
  pseReal,
  pseEsperada,
}: {
  pseReal: { dia_md: string; pse_media: number }[];
  pseEsperada: { dia_md: string; pse_esperada: number }[];
}) {
  const tr = await obterTr();
  if (pseReal.length === 0 && pseEsperada.length === 0) return <SemDados />;
  const dias = (pseReal.length ? pseReal : pseEsperada).map((d) => d.dia_md);
  const realMap = new Map(pseReal.map((d) => [d.dia_md, d.pse_media]));
  const espMap = new Map(pseEsperada.map((d) => [d.dia_md, d.pse_esperada]));
  const atingido = dias.map((d) => realMap.get(d) ?? null);
  const esperado = dias.map((d) => espMap.get(d) ?? null);
  const rotulo = (v: number | null) => (v == null ? "" : v.toLocaleString(tr.loc));

  const data: Data[] = [
    {
      x: dias,
      y: atingido,
      type: "bar",
      name: tr("RPE atingido"),
      marker: { color: COR_ATINGIDO },
      text: atingido.map(rotulo),
      textposition: "outside",
      textfont: { color: TINTA, size: 13 },
      cliponaxis: false,
      hovertemplate: tr("%{x}<br>RPE atingido %{y}<extra></extra>"),
    },
  ];
  if (esperado.some((v) => v !== null)) {
    data.push({
      x: dias,
      y: esperado,
      type: "scatter",
      mode: "text+lines+markers",
      name: tr("RPE esperado"),
      line: { color: COR_ESPERADO, width: 3 },
      marker: { size: 9, color: COR_ESPERADO },
      text: esperado.map(rotulo),
      textposition: "top center",
      textfont: { color: COR_ESPERADO, size: 12 },
      connectgaps: true,
      hovertemplate: tr("%{x}<br>RPE esperado %{y}<extra></extra>"),
    });
  }

  return (
    <div style={cartaoBranco}>
      <PlotlyChart
        titulo={tr("RPE por dia — atingido vs esperado")}
        data={data}
        layout={{
          ...layoutBranco,
          barmode: "group",
          xaxis: { type: "category", categoryorder: "array", categoryarray: dias, tickfont: { size: 12, color: TINTA_SUAVE }, linecolor: cores.bordaForte },
          yaxis: { title: { text: tr("PSE (/10)") }, range: [0, 10], gridcolor: GRELHA, tickfont: { size: 11, color: TINTA_SUAVE }, zeroline: false },
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
async function GraficoCargaPorJogador({
  porJogador,
  semanaA,
  semanaB,
}: {
  porJogador: { jogador: string; a: number; b: number }[];
  semanaA: number | null;
  semanaB: number | null;
}) {
  const tr = await obterTr();
  if (porJogador.length === 0) return <SemDados />;
  // Em barras horizontais o Plotly desenha o 1.º item em baixo — ordenar
  // ascendente pela semana atual põe o maior no topo.
  const ordenadas = [...porJogador].sort((a, b) => a.a - b.a);
  const nomes = ordenadas.map((p) => p.jogador);
  const rotulo = (v: number) => (v ? v.toLocaleString(tr.loc) : "");
  const altura = Math.max(300, ordenadas.length * 44 + 90);

  return (
    <div style={cartaoBranco}>
      <PlotlyChart
        titulo={tr("Carga por jogador — Semana {0} vs {1}", [semanaA ?? "", semanaB ?? ""])}
        data={[
          {
            x: ordenadas.map((p) => p.a),
            y: nomes,
            type: "bar",
            orientation: "h",
            name: tr("Semana {0}", [semanaA ?? "atual"]),
            marker: { color: COR_ATINGIDO },
            text: ordenadas.map((p) => rotulo(p.a)),
            textposition: "outside",
            textfont: { color: TINTA, size: 11 },
            cliponaxis: false,
            hovertemplate: tr("%{y}<br>%{x:,} UA<extra>Semana atual</extra>"),
          },
          {
            x: ordenadas.map((p) => p.b),
            y: nomes,
            type: "bar",
            orientation: "h",
            name: tr("Semana {0}", [semanaB ?? "anterior"]),
            marker: { color: COR_ESPERADO },
            text: ordenadas.map((p) => rotulo(p.b)),
            textposition: "outside",
            textfont: { color: TINTA, size: 11 },
            cliponaxis: false,
            hovertemplate: tr("%{y}<br>%{x:,} UA<extra>Semana anterior</extra>"),
          },
        ]}
        layout={{
          ...layoutBranco,
          barmode: "group",
          xaxis: { title: { text: tr("Carga Interna (UA)") }, gridcolor: GRELHA, tickfont: { size: 11, color: TINTA_SUAVE }, zeroline: false },
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


async function SemDados() {
  const tr = await obterTr();
  return <p style={{ color: cores.textoSuave, fontSize: "0.85rem" }}>{tr("Sem dados suficientes.")}</p>;
}

