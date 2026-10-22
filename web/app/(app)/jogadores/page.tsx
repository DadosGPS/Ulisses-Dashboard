import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { KpiTile } from "@/components/ui/KpiTile";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { cores, espaco, raio } from "@/lib/theme";
import type { JogadorResponse } from "@/lib/types";

import { SecaoTitulo } from "@/components/ui/base";
import { EvolucaoSemanal } from "@/components/ui/EvolucaoSemanal";
import { obterEquipaAtiva } from "@/lib/equipa-ativa-servidor";
import { obterTr, obterLingua } from "@/lib/i18n/servidor";
async function obterJogador(
  teamId: string,
  accessToken: string,
  nome?: string,
  microciclo?: string,
  diaMd?: string
): Promise<JogadorResponse> {
  const url = new URL(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/jogador`);
  if (nome) url.searchParams.set("nome", nome);
  if (microciclo) url.searchParams.set("microciclo", microciclo);
  if (diaMd) url.searchParams.set("dia_md", diaMd);
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${accessToken}`, "X-Lingua": await obterLingua() },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Falha ao carregar o jogador (${res.status}).`);
  return res.json();
}

export default async function JogadoresPage({
  searchParams,
}: {
  searchParams: Promise<{ nome?: string; jogador?: string; microciclo?: string; dia_md?: string }>;
}) {
  const tr = await obterTr();
  // O jogador vem da barra de filtros global (?jogador=); ?nome= mantém-se por
  // retrocompatibilidade com links antigos.
  const { nome, jogador, microciclo, dia_md } = await searchParams;
  const nomeAlvo = jogador ?? nome;

  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) return null;

  const { data: membro } = await obterEquipaAtiva(supabase, session.user.id);

  if (!membro) {
    return <EstadoVazio mensagem={tr("Ainda não estás associado a nenhuma equipa.")} />;
  }

  let dados: JogadorResponse;
  try {
    dados = await obterJogador(membro.team_id, session.access_token, nomeAlvo, microciclo, dia_md);
  } catch {
    return <EstadoVazio mensagem={tr("Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr.")} />;
  }

  if (!dados.jogador || dados.jogadores_disponiveis.length === 0) {
    return <EstadoVazio mensagem={tr("Ainda não há dados carregados para esta equipa.")} />;
  }

  const kpis = dados.kpis!;

  return (
    <div>
      <PageHeader
        titulo={tr("Jogadores")}
        subtitulo={tr("{0} · {1} · {2} sessões registadas", [dados.jogador ?? "", dados.posicao ?? "—", kpis.sessoes_total])}
      />

      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: espaco.md, marginBottom: espaco.xxl }}>
          <KpiTile label={tr("Carga Interna")} valor={kpis.carga_interna_media ?? "—"} unidade="UA" subLabel={tr("média de todas as sessões")} cor={cores.cargaInterna} />
          <KpiTile label={tr("ACWR Atual")} valor={kpis.acwr_atual ?? "—"} unidade="" subLabel={tr("0.8–1.3 = zona segura")} cor={cores.distanciaTotal} />
          <KpiTile label={tr("Hooper Index")} valor={kpis.hooper_medio ?? "—"} unidade="/20" subLabel={tr("média de todas as sessões")} cor={cores.hsr} />
          <KpiTile
            label={tr("Vel. Máx Recorde")}
            valor={kpis.vel_max_recorde ?? "—"}
            unidade={tr("km/h")}
            subLabel={
              kpis.vel_max_pct_recorde !== null && kpis.vel_max_pct_recorde !== undefined ? (
                <span style={{ color: kpis.vel_max_pct_recorde < 90 ? cores.perigo : undefined }}>
                  {tr("últimas 3 sessões:")}{" "}{kpis.vel_max_pct_recorde}{tr("% do recorde")}</span>
              ) : (
                tr("melhor registo")
              )
            }
            cor={cores.velMax}
          />
        </div>

        <EvolucaoSemanal teamId={membro.team_id} jogador={dados.jogador} />

        {dados.evolucao_vmax && dados.evolucao_vmax.length > 0 && (
          <div style={{ marginBottom: espaco.xxl }}>
            <SecaoTitulo>{tr("Vmax por sessão — % do recorde da época")}</SecaoTitulo>
            <p style={{ color: cores.textoSuave, fontSize: "0.78rem", margin: `0 0 ${espaco.md}px` }}>
              {tr("Cada barra é a velocidade máxima dessa sessão face ao recorde da época (")}{dados.vel_max_recorde ?? "—"} {tr("km/h). A linha a tracejado marca os 90% — abaixo disso houve pouco estímulo de velocidade.")}</p>
            <GraficoVmaxPct pontos={dados.evolucao_vmax} />
          </div>
        )}
      </div>
    </div>
  );
}

// Ordem canónica dos dias do microciclo (igual a utils/calculos.DIAS_MD_ORDEM).
const DIAS_MD_ORDEM = ["MD-5", "MD-4", "MD-3", "MD-2", "MD-1", "MD", "MD+1", "MD+2"];
// Cor por Dia MD — o dia de jogo (MD) destaca-se; quanto mais longe do jogo,
// mais frio. Assim vê-se logo se o estímulo de velocidade vem dos dias certos.
const COR_DIA_MD: Record<string, string> = {
  "MD-5": "#64748b",
  "MD-4": "#3498db",
  "MD-3": "#22c55e",
  "MD-2": "#f59e0b",
  "MD-1": "#f97316",
  MD: "#e63946",
  "MD+1": "#7c3aed",
  "MD+2": "#a855f7",
};

type PontoVmax = { data: string; tipo: string | null; dia_md: string | null; kmh: number; pct: number };

/** Vmax por sessão como % do recorde da época, AGRUPADO por Dia MD: cada série
 * é um dia do microciclo (MD-3, MD-1, MD…), o que torna explícito de que dias
 * vem — ou falta — o estímulo de velocidade. A linha a tracejado marca os 90%. */
async function GraficoVmaxPct({ pontos }: { pontos: PontoVmax[] }) {
  const tr = await obterTr();
  // Agrupar por Dia MD, respeitando a ordem canónica; dias fora da lista (ou
  // sem Dia MD) vão para o fim, para não perder sessões.
  const presentes = Array.from(new Set(pontos.map((p) => p.dia_md ?? "Sem dia")));
  const ordenados = [
    ...DIAS_MD_ORDEM.filter((d) => presentes.includes(d)),
    ...presentes.filter((d) => !DIAS_MD_ORDEM.includes(d)),
  ];

  const series = ordenados.map((dia) => {
    const doDia = pontos.filter((p) => (p.dia_md ?? "Sem dia") === dia);
    return {
      x: doDia.map((p) => p.data),
      y: doDia.map((p) => p.pct),
      type: "bar" as const,
      name: dia,
      marker: { color: COR_DIA_MD[dia] ?? cores.textoSuave },
      customdata: doDia.map((p) => [p.kmh, p.tipo ?? "—"]),
      hovertemplate: tr("%{x|%d/%m/%Y} · {0}<br>%{y}% do recorde<br>%{customdata[0]} km/h · %{customdata[1]}<extra></extra>", [dia]),
    };
  });

  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
      <PlotlyChart
        titulo={tr("Vmax por sessão — % do recorde, por Dia MD")}
        data={series}
        layout={{
          barmode: "group",
          legend: { orientation: "h", y: -0.2, font: { size: 10 } },
          xaxis: { type: "date", title: { text: "" } },
          yaxis: { title: { text: tr("% do recorde") }, ticksuffix: "%", range: [0, 110] },
          shapes: [
            { type: "line", xref: "paper", x0: 0, x1: 1, y0: 90, y1: 90, line: { color: "rgba(34,197,94,0.6)", width: 1, dash: "dash" } },
          ],
          annotations: [
            { x: 1, xref: "paper", y: 90, yref: "y", text: tr("90% do recorde"), showarrow: false, xanchor: "right", yanchor: "bottom", font: { size: 9, color: "rgba(34,197,94,0.8)" } },
          ],
        }}
        altura={280}
      />
      <p style={{ fontSize: "0.72rem", color: cores.textoSuave, marginTop: espaco.sm }}>
        {tr("Cada cor é um dia do microciclo. Barras acima da linha dos 90% = a sessão puxou por velocidade perto do pico da época.")}</p>
    </div>
  );
}


function EstadoVazio({ mensagem }: { mensagem: string }) {
  return (
    <div style={{ maxWidth: 600, margin: "80px auto", padding: "0 24px", textAlign: "center" }}>
      <p style={{ color: "rgb(var(--ink) / 0.6)", fontSize: "0.95rem" }}>{mensagem}</p>
    </div>
  );
}
