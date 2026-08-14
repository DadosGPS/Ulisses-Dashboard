import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { LoadProfileTable, type ColunaCarga, type LinhaCarga } from "@/components/ui/LoadProfileTable";
import { JogadorSelector } from "@/components/ui/JogadorSelector";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { PseEsperadaVsReal } from "@/components/ui/PseEsperadaVsReal";
import { cores, espaco, raio } from "@/lib/theme";
import type { PlaneamentoResponse, PseSemanaResponse } from "@/lib/types";

const CORES_METRICA: Record<string, string> = {
  "Distância Total (m)": cores.distanciaTotal,
  "HSR (m)": cores.hsr,
  "Sprint (m)": cores.sprint,
  "Acc (n)": cores.acc,
  "Dcc (n)": cores.dcc,
  "Carga Interna": cores.cargaInterna,
};

async function obterPlaneamento(teamId: string, accessToken: string, jogador?: string): Promise<PlaneamentoResponse> {
  const url = new URL(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/planeamento`);
  if (jogador) url.searchParams.set("jogador", jogador);
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Falha ao carregar o planeamento (${res.status}).`);
  return res.json();
}

async function obterPseSemana(teamId: string, accessToken: string): Promise<PseSemanaResponse | null> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/planeamento/pse-semana`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
  if (!res.ok) return null;
  return res.json();
}

export default async function PlaneamentoPage({
  searchParams,
}: {
  searchParams: Promise<{ jogador?: string }>;
}) {
  const { jogador } = await searchParams;

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

  let dados: PlaneamentoResponse;
  try {
    dados = await obterPlaneamento(membro.team_id, session.access_token, jogador);
  } catch {
    return <EstadoVazio mensagem="Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr." />;
  }

  if (!dados.tem_dados) {
    return <EstadoVazio mensagem="Ainda não há dados carregados para esta equipa." />;
  }

  const pseSemana = await obterPseSemana(membro.team_id, session.access_token);

  if (!dados.tem_jogos) {
    return (
      <EstadoVazio mensagem='Ainda não há sessões marcadas como "Jogo" nos dados — a comparação Treino vs Jogo precisa de pelo menos um jogo registado.' />
    );
  }

  const colunas: ColunaCarga[] = dados.metricas.map((m) => ({
    chave: m,
    label: m.replace(" (m)", "").replace(" (n)", ""),
    cor: CORES_METRICA[m] ?? cores.distanciaTotal,
    casas: 0,
  }));

  const linhas: LinhaCarga[] = dados.dias.map((d) => ({
    jogador: d.dia_md,
    valores: Object.fromEntries(dados.metricas.map((m) => [m, d.valores[m] ?? null])),
  }));

  return (
    <div>
      <PageHeader
        titulo="Planeamento"
        subtitulo={
          dados.individual
            ? "Treino vs Jogo — intensidade de cada dia, em % da referência de jogo DESTE jogador"
            : "Treino vs Jogo — intensidade de cada dia do microciclo, em % da referência de jogo da equipa"
        }
        acoes={
          <JogadorSelector
            jogadores={dados.jogadores_disponiveis}
            atual={dados.jogador_selecionado}
            basePath="/planeamento"
            paramName="jogador"
            opcaoEquipa
          />
        }
      />

      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {dados.jogador_selecionado && !dados.individual && (
          <p style={{ color: cores.atencao, fontSize: "0.78rem", marginBottom: espaco.md }}>
            Este jogador ainda não tem jogos registados — a mostrar a referência da equipa toda.
          </p>
        )}

        <SecaoTitulo>⚽ Referência de Jogo (média por sessão)</SecaoTitulo>
        <div style={{ display: "grid", gridTemplateColumns: `repeat(${dados.metricas.length}, 1fr)`, gap: espaco.md, marginBottom: espaco.xxl }}>
          {dados.metricas.map((m) => (
            <div
              key={m}
              style={{
                background: cores.bgCartao,
                border: `1px solid ${cores.borda}`,
                borderTop: `2px solid ${CORES_METRICA[m] ?? cores.distanciaTotal}`,
                borderRadius: raio.md,
                padding: espaco.md,
              }}
            >
              <div style={{ fontSize: "0.64rem", color: cores.textoSuave, letterSpacing: "0.06em", textTransform: "uppercase", fontWeight: 600, marginBottom: 4 }}>
                {m.replace(" (m)", "").replace(" (n)", "")}
              </div>
              <div className="font-display" style={{ fontSize: "1.3rem", fontWeight: 700, color: "white" }}>
                {dados.referencia[m]?.toLocaleString("pt-PT") ?? "—"}
              </div>
            </div>
          ))}
        </div>

        <SecaoTitulo>📅 Intensidade por Dia do Microciclo (% vs Jogo)</SecaoTitulo>
        <p style={{ color: cores.textoSuave, fontSize: "0.8rem", marginTop: -8, marginBottom: espaco.md, maxWidth: 640 }}>
          Cor mais intensa = valor mais próximo da intensidade de jogo nesse dia. Dias de tapering (MD-1) e recuperação
          (MD+1/MD+2) são naturalmente mais claros — isso é esperado, não um alerta.
        </p>
        <LoadProfileTable colunas={colunas} linhas={linhas} labelLinha="Dia MD" />

        {pseSemana && (
          <div style={{ marginTop: espaco.xxl }}>
            <SecaoTitulo>🎯 PSE Esperada vs Real</SecaoTitulo>
            <PseEsperadaVsReal teamId={membro.team_id} dadosIniciais={pseSemana} />
          </div>
        )}

        {dados.evolucao_semanal.length > 0 && (
          <div style={{ marginTop: espaco.xxl }}>
            <SecaoTitulo>📉 Evolução Semanal (% vs Jogo)</SecaoTitulo>
            <p style={{ color: cores.textoSuave, fontSize: "0.8rem", marginTop: -8, marginBottom: espaco.md, maxWidth: 640 }}>
              Soma de toda a semana de treino em % de um jogo (ex: 300% = equivalente a 3 jogos de distância nessa
              semana) — útil para confirmar se um deload planeado baixou mesmo a carga face à semana anterior.
            </p>

            <ComparacaoUltimaSemana dados={dados} />

            <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md, marginTop: espaco.md }}>
              <PlotlyChart
                data={dados.metricas.map((m) => ({
                  x: dados.evolucao_semanal.map((e) => `MC ${e.microciclo}`),
                  y: dados.evolucao_semanal.map((e) => e.valores[m] ?? null),
                  type: "scatter",
                  mode: "lines",
                  name: m.replace(" (m)", "").replace(" (n)", ""),
                  line: { color: CORES_METRICA[m] ?? cores.distanciaTotal, width: 2 },
                  connectgaps: false,
                  hovertemplate: "%{x}<br>%{fullData.name}: %{y}%<extra></extra>",
                }))}
                layout={{
                  legend: { orientation: "h", y: -0.2 },
                  xaxis: { title: { text: "Microciclo" } },
                  yaxis: { title: { text: "% de 1 jogo" } },
                }}
                altura={280}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function ComparacaoUltimaSemana({ dados }: { dados: PlaneamentoResponse }) {
  const semanas = dados.evolucao_semanal;
  if (semanas.length < 2) return null;
  const atual = semanas[semanas.length - 1];
  const anterior = semanas[semanas.length - 2];

  return (
    <div style={{ display: "grid", gridTemplateColumns: `repeat(${dados.metricas.length}, 1fr)`, gap: espaco.md }}>
      {dados.metricas.map((m) => {
        const v = atual.valores[m];
        const vAnt = anterior.valores[m];
        if (v === undefined || vAnt === undefined) {
          return (
            <div key={m} style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
              <div style={{ fontSize: "0.62rem", color: cores.textoSuave, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>
                {m.replace(" (m)", "").replace(" (n)", "")}
              </div>
              <div style={{ color: cores.textoFraco, fontSize: "0.85rem" }}>—</div>
            </div>
          );
        }
        const desceu = v < vAnt;
        const delta = v - vAnt;
        return (
          <div key={m} style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
            <div style={{ fontSize: "0.62rem", color: cores.textoSuave, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>
              {m.replace(" (m)", "").replace(" (n)", "")} · MC {atual.microciclo}
            </div>
            <div className="font-display" style={{ fontSize: "1.2rem", fontWeight: 700, color: "white" }}>
              {v}%
            </div>
            <div style={{ fontSize: "0.72rem", fontWeight: 600, color: desceu ? cores.info : cores.atencao }}>
              {desceu ? "▼" : "▲"} {Math.abs(delta).toFixed(0)}pp vs MC {anterior.microciclo}
            </div>
          </div>
        );
      })}
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
