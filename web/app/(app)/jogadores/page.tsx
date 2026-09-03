import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { KpiTile } from "@/components/ui/KpiTile";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { alphaHex, cores, espaco, raio } from "@/lib/theme";
import type { JogadorResponse, SessaoJogador } from "@/lib/types";

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
    headers: { Authorization: `Bearer ${accessToken}` },
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
  // O jogador vem da barra de filtros global (?jogador=); ?nome= mantém-se por
  // retrocompatibilidade com links antigos.
  const { nome, jogador, microciclo, dia_md } = await searchParams;
  const nomeAlvo = jogador ?? nome;

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

  let dados: JogadorResponse;
  try {
    dados = await obterJogador(membro.team_id, session.access_token, nomeAlvo, microciclo, dia_md);
  } catch {
    return <EstadoVazio mensagem="Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr." />;
  }

  if (!dados.jogador || dados.jogadores_disponiveis.length === 0) {
    return <EstadoVazio mensagem="Ainda não há dados carregados para esta equipa." />;
  }

  const kpis = dados.kpis!;

  return (
    <div>
      <PageHeader
        titulo="Jogadores"
        subtitulo={`${dados.jogador ?? ""} · ${dados.posicao ?? "—"} · ${kpis.sessoes_total} sessões registadas`}
      />

      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: espaco.md, marginBottom: espaco.xxl }}>
          <KpiTile label="Carga Interna" valor={kpis.carga_interna_media ?? "—"} unidade="UA" subLabel="média de todas as sessões" cor={cores.cargaInterna} />
          <KpiTile label="ACWR Atual" valor={kpis.acwr_atual ?? "—"} unidade="" subLabel="0.8–1.3 = zona segura" cor={cores.distanciaTotal} />
          <KpiTile label="Hooper Index" valor={kpis.hooper_medio ?? "—"} unidade="/20" subLabel="média de todas as sessões" cor={cores.hsr} />
          <KpiTile
            label="Vel. Máx Recorde"
            valor={kpis.vel_max_recorde ?? "—"}
            unidade="km/h"
            subLabel={
              kpis.vel_max_pct_recorde !== null && kpis.vel_max_pct_recorde !== undefined ? (
                <span style={{ color: kpis.vel_max_pct_recorde < 90 ? cores.perigo : undefined }}>
                  últimas 3 sessões: {kpis.vel_max_pct_recorde}% do recorde
                </span>
              ) : (
                "melhor registo"
              )
            }
            cor={cores.velMax}
          />
        </div>

        {dados.evolucao_vmax && dados.evolucao_vmax.length > 0 && (
          <div style={{ marginBottom: espaco.xxl }}>
            <SecaoTitulo>🏃‍♂️💨 Vmax por sessão — % do recorde da época</SecaoTitulo>
            <p style={{ color: cores.textoSuave, fontSize: "0.78rem", margin: `0 0 ${espaco.md}px` }}>
              Cada barra é a velocidade máxima dessa sessão face ao recorde da época ({dados.vel_max_recorde ?? "—"} km/h). A linha a tracejado marca os 90% — abaixo disso houve pouco estímulo de velocidade.
            </p>
            <GraficoVmaxPct pontos={dados.evolucao_vmax} />
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: espaco.lg, marginBottom: espaco.xxl }}>
          <div>
            <SecaoTitulo>📈 Evolução da Carga Interna</SecaoTitulo>
            <Cartao>
              {dados.evolucao_carga && dados.evolucao_carga.length > 0 ? (
                <PlotlyChart
                  data={[
                    {
                      x: dados.evolucao_carga.map((p) => p.data),
                      y: dados.evolucao_carga.map((p) => p.carga_interna),
                      type: "scatter",
                      mode: "lines",
                      line: { color: cores.cargaInterna, width: 2 },
                      fill: "tozeroy",
                      fillcolor: "rgba(230,57,70,0.06)",
                      hovertemplate: "%{x}<br>Carga Interna: %{y} UA<extra></extra>",
                    },
                  ]}
                  layout={{
                    xaxis: { title: { text: "Data" } },
                    yaxis: { title: { text: "Carga Interna (UA)" } },
                  }}
                  altura={240}
                />
              ) : (
                <SemDados />
              )}
            </Cartao>
          </div>

          <div>
            <SecaoTitulo>🚦 Evolução do ACWR</SecaoTitulo>
            <Cartao>
              {dados.evolucao_acwr && dados.evolucao_acwr.length > 0 ? (
                <PlotlyChart
                  data={[
                    {
                      x: dados.evolucao_acwr.map((p) => p.data),
                      y: dados.evolucao_acwr.map((p) => p.acwr),
                      type: "scatter",
                      mode: "lines",
                      name: "ACWR",
                      line: { color: cores.distanciaTotal, width: 2 },
                      showlegend: false,
                      hovertemplate: "%{x}<br>ACWR: %{y:.2f}<extra></extra>",
                    },
                    // Zona segura 0.8–1.3, para dar contexto visual ao traçado.
                    {
                      x: dados.evolucao_acwr.map((p) => p.data),
                      y: dados.evolucao_acwr.map(() => 1.3),
                      type: "scatter",
                      mode: "lines",
                      name: "Limite 1.3",
                      line: { color: "rgba(245,158,11,0.4)", width: 1, dash: "dot" },
                      hoverinfo: "skip",
                      showlegend: false,
                    },
                  ]}
                  layout={{
                    xaxis: { title: { text: "Data" } },
                    yaxis: { title: { text: "ACWR" } },
                    annotations: [
                      {
                        x: 1,
                        xref: "paper",
                        y: 1.3,
                        yref: "y",
                        text: "limite 1.3",
                        showarrow: false,
                        xanchor: "right",
                        yanchor: "bottom",
                        font: { size: 9, color: "rgba(245,158,11,0.7)" },
                      },
                    ],
                  }}
                  altura={240}
                />
              ) : (
                <SemDados />
              )}
            </Cartao>
          </div>
        </div>

        {dados.metricas_externas && dados.metricas_externas.length > 0 && (
          <div style={{ marginBottom: espaco.xxl }}>
            <SecaoTitulo>🛰️ Carga Externa — últimas sessões</SecaoTitulo>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: espaco.lg }}>
              {dados.metricas_externas.map((m) => (
                <GraficoExternaJogador key={m.chave} metrica={m} pontos={dados.evolucao_externa?.[m.chave] ?? []} />
              ))}
            </div>
          </div>
        )}

        <SecaoTitulo>📋 Sessões Recentes</SecaoTitulo>
        <TabelaSessoes sessoes={dados.sessoes_recentes ?? []} />
      </div>
    </div>
  );
}

// Colunas numéricas coloridas tipo mapa de calor — mesma cor por métrica usada
// no resto da app (LoadProfileTable em /equipa), para consistência visual.
const COLUNAS_METRICA: { chave: keyof SessaoJogador; label: string; cor: string; casas?: number }[] = [
  { chave: "carga_interna", label: "Carga Interna", cor: cores.cargaInterna },
  { chave: "distancia_total_m", label: "Dist. Total (m)", cor: cores.distanciaTotal },
  { chave: "hsr_m", label: "HSR (m)", cor: cores.hsr },
  { chave: "sprint_m", label: "Sprint (m)", cor: cores.sprint },
  { chave: "vel_max_kmh", label: "Vel. Máx (km/h)", cor: cores.velMax, casas: 1 },
  { chave: "hooper_index", label: "Hooper", cor: cores.info },
];

function TabelaSessoes({ sessoes }: { sessoes: NonNullable<JogadorResponse["sessoes_recentes"]> }) {
  if (sessoes.length === 0) return <SemDados />;

  const ranges = Object.fromEntries(
    COLUNAS_METRICA.map((c) => {
      const vals = sessoes.map((s) => s[c.chave]).filter((v): v is number => typeof v === "number");
      return [c.chave, vals.length ? [Math.min(...vals), Math.max(...vals)] : [0, 1]];
    })
  ) as Record<string, [number, number]>;

  return (
    <div style={{ overflowX: "auto", border: `1px solid ${cores.borda}`, borderRadius: raio.md, background: cores.bgCartao }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontVariantNumeric: "tabular-nums" }}>
        <thead>
          <tr style={{ background: "rgba(255,255,255,0.04)" }}>
            <th style={thSessoesStyle("left")}>Data</th>
            <th style={thSessoesStyle("left")}>Tipo</th>
            <th style={thSessoesStyle("left")}>Dia MD</th>
            {COLUNAS_METRICA.map((c) => (
              <th key={c.chave} style={thSessoesStyle("center")}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sessoes.map((s, i) => (
            <tr key={i} style={{ borderTop: `1px solid ${cores.borda}` }}>
              <td style={tdTextoStyle}>{s.data ?? "—"}</td>
              <td style={tdTextoStyle}>{s.tipo ?? "—"}</td>
              <td style={tdTextoStyle}>{s.dia_md ?? "—"}</td>
              {COLUNAS_METRICA.map((c) => {
                const v = s[c.chave];
                if (typeof v !== "number") {
                  return (
                    <td key={c.chave} style={{ padding: "6px 8px", textAlign: "center", color: cores.textoFraco }}>
                      —
                    </td>
                  );
                }
                const [lo, hi] = ranges[c.chave];
                const pct = hi > lo ? (v - lo) / (hi - lo) : 0.5;
                const alpha = 0.18 + pct * 0.55;
                return (
                  <td key={c.chave} style={{ padding: "6px 8px", textAlign: "center" }}>
                    <span
                      style={{
                        display: "inline-block",
                        minWidth: 58,
                        padding: "5px 10px",
                        borderRadius: 14,
                        background: `${c.cor}${alphaHex(alpha)}`,
                        color: "white",
                        fontWeight: 700,
                        fontSize: "0.75rem",
                      }}
                    >
                      {v.toLocaleString("pt-PT", { maximumFractionDigits: c.casas ?? 0 })}
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function thSessoesStyle(align: "left" | "center"): React.CSSProperties {
  return { padding: "9px 12px", fontSize: "0.62rem", letterSpacing: "0.06em", textTransform: "uppercase", color: cores.textoSuave, textAlign: align, whiteSpace: "nowrap" };
}

const tdTextoStyle: React.CSSProperties = { padding: "8px 12px", fontSize: "0.78rem", color: "rgba(255,255,255,0.82)", whiteSpace: "nowrap" };

function Cartao({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
      {children}
    </div>
  );
}

function GraficoExternaJogador({
  metrica,
  pontos,
}: {
  metrica: { chave: string; label: string; unidade: string; cor: string; casas: number };
  pontos: { data: string; valor: number }[];
}) {
  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
      <div className="font-display" style={{ fontSize: "0.86rem", fontWeight: 700, color: "white", marginBottom: espaco.sm }}>
        {metrica.label} <span style={{ color: cores.textoSuave, fontWeight: 500 }}>({metrica.unidade})</span>
      </div>
      {pontos.length > 0 ? (
        <PlotlyChart
          data={[
            {
              x: pontos.map((p) => p.data),
              y: pontos.map((p) => p.valor),
              type: "bar",
              marker: { color: metrica.cor },
              hovertemplate: `%{x|%d/%m}<br>${metrica.label}: %{y} ${metrica.unidade}<extra></extra>`,
            },
          ]}
          layout={{
            xaxis: { type: "date", title: { text: "" } },
            yaxis: { title: { text: metrica.unidade } },
            margin: { l: 44, r: 16, t: 12, b: 40 },
          }}
          altura={200}
        />
      ) : (
        <p style={{ color: cores.textoSuave, fontSize: "0.85rem", padding: `${espaco.md}px 0` }}>Sem dados.</p>
      )}
    </div>
  );
}

function corVmax(pct: number): string {
  if (pct >= 95) return cores.sucesso;
  if (pct >= 85) return cores.velMax;
  if (pct >= 75) return cores.atencao;
  return cores.info;
}

function GraficoVmaxPct({ pontos }: { pontos: { data: string; tipo: string | null; kmh: number; pct: number }[] }) {
  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
      <PlotlyChart
        titulo="Vmax por sessão — % do recorde"
        data={[
          {
            x: pontos.map((p) => p.data),
            y: pontos.map((p) => p.pct),
            type: "bar",
            marker: { color: pontos.map((p) => corVmax(p.pct)) },
            customdata: pontos.map((p) => [p.kmh, p.tipo ?? "—"]),
            hovertemplate: "%{x|%d/%m/%Y}<br>%{y}% do recorde<br>%{customdata[0]} km/h · %{customdata[1]}<extra></extra>",
          },
        ]}
        layout={{
          xaxis: { type: "date", title: { text: "" } },
          yaxis: { title: { text: "% do recorde" }, ticksuffix: "%", range: [0, 110] },
          shapes: [
            { type: "line", xref: "paper", x0: 0, x1: 1, y0: 90, y1: 90, line: { color: "rgba(34,197,94,0.6)", width: 1, dash: "dash" } },
          ],
          annotations: [
            { x: 1, xref: "paper", y: 90, yref: "y", text: "90%", showarrow: false, xanchor: "right", yanchor: "bottom", font: { size: 9, color: "rgba(34,197,94,0.8)" } },
          ],
        }}
        altura={260}
      />
      <div style={{ display: "flex", gap: espaco.lg, flexWrap: "wrap", marginTop: espaco.sm, fontSize: "0.72rem", color: cores.textoSuave }}>
        <span><span style={{ color: cores.sucesso }}>●</span> ≥95% pico</span>
        <span><span style={{ color: cores.velMax }}>●</span> 85–95% bom estímulo</span>
        <span><span style={{ color: cores.atencao }}>●</span> 75–85% moderado</span>
        <span><span style={{ color: cores.info }}>●</span> &lt;75% baixo</span>
      </div>
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
  return <p style={{ color: cores.textoSuave, fontSize: "0.85rem", margin: 0 }}>Sem dados suficientes.</p>;
}

function EstadoVazio({ mensagem }: { mensagem: string }) {
  return (
    <div style={{ maxWidth: 600, margin: "80px auto", padding: "0 24px", textAlign: "center" }}>
      <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.95rem" }}>{mensagem}</p>
    </div>
  );
}
