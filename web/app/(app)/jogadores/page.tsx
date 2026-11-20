import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { KpiTile } from "@/components/ui/KpiTile";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { cores, espaco, raio, letra, COR_DIA_MD } from "@/lib/theme";
import type { JogadorResponse } from "@/lib/types";

import { SecaoTitulo, EstadoVazio } from "@/components/ui/base";
import { EvolucaoSemanal } from "@/components/ui/EvolucaoSemanal";
import { obterEquipaAtiva } from "@/lib/equipa-ativa-servidor";
import { obterTr, obterLingua } from "@/lib/i18n/servidor";
import Link from "next/link";
import { FichaAtletaView } from "@/components/academia/FichaAtleta";
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
  searchParams: Promise<{ nome?: string; jogador?: string; microciclo?: string; dia_md?: string; vista?: string }>;
}) {
  const tr = await obterTr();
  // O jogador vem da barra de filtros global (?jogador=); ?nome= mantém-se por
  // retrocompatibilidade com links antigos.
  const { nome, jogador, microciclo, dia_md, vista } = await searchParams;
  const separador = vista === "ficha" ? "ficha" : "carga";
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
    return <EstadoVazio acao={{ href: "/upload", label: tr("Importar GPS") }} mensagem={tr("Ainda não há dados carregados para esta equipa.")} />;
  }

  const kpis = dados.kpis!;

  return (
    <div>
      <PageHeader
        titulo={tr("Jogador · {0}", [dados.jogador ?? ""])}
        subtitulo={tr("{0} · {1} sessões registadas · escolhe o jogador na barra de filtros", [dados.posicao ?? "—", kpis.sessoes_total])}
      />

      {/* Ficha única do jogador: carga/velocidade (GPS) e testes/crescimento (Academia). */}
      <nav style={{ display: "flex", gap: 4, padding: `0 ${espaco.xxl}px`, borderBottom: `1px solid ${cores.borda}` }}>
        {([["carga", tr("Carga e velocidade")], ["ficha", tr("Testes, crescimento e maturação")]] as const).map(([k, label]) => {
          const q = new URLSearchParams({ ...(dados.jogador ? { jogador: dados.jogador } : {}), ...(k === "ficha" ? { vista: "ficha" } : {}) });
          const ativo = separador === k;
          return (
            <Link key={k} href={`/jogadores?${q}`} aria-current={ativo ? "page" : undefined}
              style={{ padding: "12px 12px", fontSize: letra.texto, fontWeight: ativo ? 650 : 500, textDecoration: "none",
                color: ativo ? cores.textoForte : cores.textoSuave, borderBottom: `2px solid ${ativo ? cores.acento : "transparent"}`, marginBottom: -1 }}>
              {label}
            </Link>
          );
        })}
      </nav>

      {separador === "ficha" ? (
        <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
          {dados.atleta_id ? (
            <FichaAtletaView atletaId={dados.atleta_id} embutida />
          ) : (
            <EstadoVazio mensagem={tr("Este jogador ainda não tem ficha na Academia. Adiciona-o em Academia (a ligação é feita pelo nome) para veres aqui os testes, o crescimento e a maturação.")} />
          )}
        </div>
      ) : (
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: espaco.md, marginBottom: espaco.xxl }}>
          <KpiTile label={tr("Carga Interna")} valor={kpis.carga_interna_media ?? "—"} unidade="UA" subLabel={tr("média de todas as sessões")} cor={cores.cargaInterna} />
          <KpiTile label={tr("Carga da semana")} valor={kpis.semana_vs_normal == null ? "—" : `${kpis.semana_vs_normal > 0 ? "+" : ""}${kpis.semana_vs_normal}`} unidade="%"
            subLabel={kpis.semana_vs_normal == null ? tr("precisa de 4 semanas de histórico") : tr("vs o normal dele (últimas {0} semanas)", [kpis.semana_normal_n])} cor={cores.distanciaTotal} />
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
            <p style={{ color: cores.textoSuave, fontSize: letra.pequeno, margin: `0 0 ${espaco.md}px` }}>
              {tr("Cada barra é a velocidade máxima dessa sessão face ao recorde da época (")}{dados.vel_max_recorde ?? "—"} {tr("km/h). A linha a tracejado marca os 90% — abaixo disso houve pouco estímulo de velocidade.")}</p>
            <GraficoVmaxPct pontos={dados.evolucao_vmax} />
          </div>
        )}
      </div>
      )}
    </div>
  );
}

// Ordem canónica dos dias do microciclo (igual a utils/calculos.DIAS_MD_ORDEM).
const DIAS_MD_ORDEM = ["MD-5", "MD-4", "MD-3", "MD-2", "MD-1", "MD", "MD+1", "MD+2"];

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
      <p style={{ fontSize: letra.pequeno, color: cores.textoSuave, marginTop: espaco.sm }}>
        {tr("Cada cor é um dia do microciclo. Barras acima da linha dos 90% = a sessão puxou por velocidade perto do pico da época.")}</p>
    </div>
  );
}


