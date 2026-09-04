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

        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: espaco.md, marginBottom: espaco.xxl }}>
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

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: espaco.lg, marginBottom: espaco.xxl }}>
          <div>
            <SecaoTitulo>📊 Carga Média por Dia</SecaoTitulo>
            <GraficoPorDia linhas={dados.carga_por_dia.map((d) => ({ dia: d.dia_md, valor: d.carga_media }))} unidade="UA" cor={cores.cargaInterna} />
          </div>
          <div>
            <SecaoTitulo>🗣️ PSE Média por Dia</SecaoTitulo>
            <GraficoPorDia linhas={dados.pse_por_dia.map((d) => ({ dia: d.dia_md, valor: d.pse_media }))} unidade="/10" cor={cores.hsr} />
          </div>
        </div>

        {dados.comparacao && (
          <div style={{ marginBottom: espaco.xxl }}>
            <SecaoTitulo>⚖️ Comparação de Microciclos</SecaoTitulo>
            <ComparacaoMicrociclos a={dados.comparacao.a} b={dados.comparacao.b} />
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

function GraficoPorDia({ linhas, unidade, cor }: { linhas: { dia: string; valor: number }[]; unidade: string; cor: string }) {
  if (linhas.length === 0) return <SemDados />;
  const dias = linhas.map((l) => l.dia);
  const valores = linhas.map((l) => l.valor);

  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
      <PlotlyChart
        data={[
          {
            x: dias,
            y: valores,
            type: "bar",
            marker: { color: cor },
            text: valores.map((v) => v.toLocaleString("pt-PT")),
            textposition: "outside",
            hovertemplate: `%{x}<br>%{y} ${unidade}<extra></extra>`,
          },
        ]}
        layout={{
          xaxis: { type: "category", categoryorder: "array", categoryarray: dias },
          yaxis: { title: { text: unidade } },
          margin: { l: 44, r: 16, t: 24, b: 36 },
        }}
        altura={230}
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
