import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { FiltrosCargaExterna } from "@/components/ui/FiltrosCargaExterna";
import { LoadProfileTable, type ColunaCarga, type LinhaCarga } from "@/components/ui/LoadProfileTable";
import { PerfilCargaExternaGraficos } from "@/components/ui/PerfilCargaExternaGraficos";
import { cores, espaco, raio } from "@/lib/theme";

interface MetricaDef {
  chave: string;
  label: string;
  unidade: string;
  cor: string;
  casas: number;
}

interface KpiCarga {
  chave: string;
  label: string;
  unidade: string;
  cor: string;
  atual: number | null;
  baseline: number | null;
  delta_pct: number | null;
  estado: string;
  n_baseline: number;
}

interface JogadorCarga {
  jogador: string;
  posicao: string;
  valores: Record<string, number | null>;
  derivados: {
    dist_min: number | null;
    hsr_min: number | null;
    pct_hsr: number | null;
    pct_sprint: number | null;
  };
}

interface CargaExternaResponse {
  tem_dados: boolean;
  filtros_disponiveis: { tipos: string[]; posicoes: string[]; dias_md: string[]; microciclos: number[]; jogadores: string[] };
  filtros?: { tipo: string | null; posicao: string | null; dia_md: string | null };
  sessao_recente: string | null;
  metricas: MetricaDef[];
  kpis: KpiCarga[];
  jogadores: JogadorCarga[];
  evolucao: Record<string, { data: string; valor: number | null }[]>;
}

const ESTADO_UI: Record<string, { label: string; cor: string }> = {
  alto: { label: "Alto", cor: cores.cargaInterna },
  baixo: { label: "Baixo", cor: cores.info },
  normal: { label: "Normal", cor: cores.sucesso },
  insuficiente: { label: "Sem base", cor: cores.textoSuave },
};

async function obterCargaExterna(
  teamId: string,
  accessToken: string,
  filtros: { tipo?: string; posicao?: string; dia_md?: string; microciclo?: string; jogador?: string }
): Promise<CargaExternaResponse> {
  const url = new URL(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/carga-externa`);
  if (filtros.tipo) url.searchParams.set("tipo", filtros.tipo);
  if (filtros.posicao) url.searchParams.set("posicao", filtros.posicao);
  if (filtros.dia_md) url.searchParams.set("dia_md", filtros.dia_md);
  if (filtros.microciclo) url.searchParams.set("microciclo", filtros.microciclo);
  if (filtros.jogador) url.searchParams.set("jogador", filtros.jogador);
  const res = await fetch(url, { headers: { Authorization: `Bearer ${accessToken}` }, cache: "no-store" });
  if (!res.ok) throw new Error(`Falha ao carregar a carga externa (${res.status}).`);
  return res.json();
}

export default async function CargaExternaPage({
  searchParams,
}: {
  searchParams: Promise<{ tipo?: string; posicao?: string; dia_md?: string; microciclo?: string; jogador?: string }>;
}) {
  const { tipo, posicao, dia_md, microciclo, jogador } = await searchParams;

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

  if (!membro) return <EstadoVazio mensagem="Ainda não estás associado a nenhuma equipa." />;

  let dados: CargaExternaResponse;
  try {
    dados = await obterCargaExterna(membro.team_id, session.access_token, { tipo, posicao, dia_md, microciclo, jogador });
  } catch {
    return <EstadoVazio mensagem="Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr." />;
  }

  const filtros = (
    <FiltrosCargaExterna
      jogadores={dados.filtros_disponiveis?.jogadores ?? []}
      microciclos={dados.filtros_disponiveis?.microciclos ?? []}
      diasMd={dados.filtros_disponiveis?.dias_md ?? []}
      tipos={dados.filtros_disponiveis?.tipos ?? []}
      posicoes={dados.filtros_disponiveis?.posicoes ?? []}
      jogador={jogador ?? null}
      microciclo={microciclo ?? null}
      diaMd={dia_md ?? null}
      tipo={tipo ?? null}
      posicao={posicao ?? null}
    />
  );

  if (!dados.tem_dados) {
    return (
      <div>
        <PageHeader titulo="Carga Externa" subtitulo="Métricas GPS ao nível de equipa e jogador" />
        <EstadoVazio mensagem="Ainda não há dados de GPS carregados para esta equipa." />
      </div>
    );
  }

  const semResultados = dados.kpis.length === 0 && dados.jogadores.length === 0;

  // Tabela por jogador: métricas base + derivadas por minuto e percentuais.
  const colunasTabela: ColunaCarga[] = [
    ...dados.metricas.map((m) => ({ chave: m.chave, label: m.label, cor: m.cor, casas: m.casas })),
    { chave: "dist_min", label: "Dist/min", cor: cores.distanciaTotal, casas: 1 },
    { chave: "hsr_min", label: "HSR/min", cor: cores.hsr, casas: 1 },
    { chave: "pct_hsr", label: "% HSR", cor: cores.info, casas: 1 },
    { chave: "pct_sprint", label: "% Sprint", cor: cores.sprint, casas: 1 },
  ];
  const linhasTabela: LinhaCarga[] = dados.jogadores.map((j) => ({
    jogador: `${j.jogador}  ·  ${j.posicao}`,
    valores: { ...j.valores, ...j.derivados },
  }));
  // Barras por jogador — nome cru (respeita o Modo Privado no componente).
  const linhasBarras = dados.jogadores.map((j) => ({ jogador: j.jogador, valores: j.valores }));

  const dataLegivel = dados.sessao_recente
    ? new Date(dados.sessao_recente).toLocaleDateString("pt-PT", { day: "2-digit", month: "long", year: "numeric" })
    : "—";

  return (
    <div>
      <PageHeader
        titulo="Carga Externa"
        subtitulo={`Sessão mais recente: ${dataLegivel} · comparação vs baseline de 28 dias`}
        acoes={filtros}
      />

      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {semResultados ? (
          <EstadoVazio mensagem="Nenhuma sessão corresponde a estes filtros. Ajusta ou limpa os filtros." />
        ) : (
          <>
            {/* ── KPIs de equipa ─────────────────────────────── */}
            <SecaoTitulo>📊 Carga da Equipa — sessão recente vs baseline</SecaoTitulo>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
                gap: espaco.md,
                marginBottom: espaco.xxl,
              }}
            >
              {dados.kpis.map((k) => (
                <KpiCard key={k.chave} kpi={k} />
              ))}
            </div>

            {/* ── Barras por jogador (uma leitura de 3 segundos) ── */}
            <SecaoTitulo>🏃 Por Jogador — sessão mais recente</SecaoTitulo>
            <p style={{ color: cores.textoSuave, fontSize: "0.78rem", margin: `0 0 ${espaco.md}px` }}>
              Cada gráfico mostra todos os jogadores, ordenados. Um relance por métrica: quem carregou mais e menos.
            </p>
            <div style={{ marginBottom: espaco.xxl }}>
              <PerfilCargaExternaGraficos colunas={dados.metricas} linhas={linhasBarras} />
            </div>

            {/* ── Tabela detalhada (por-minuto, %HSR, %Sprint) ─── */}
            <SecaoTitulo>📋 Detalhe por Jogador</SecaoTitulo>
            <p style={{ color: cores.textoSuave, fontSize: "0.78rem", margin: `0 0 ${espaco.md}px` }}>
              Valores por-minuto e percentuais. Cor mais intensa = valor mais alto na coluna. O ranking é descritivo, não uma nota de qualidade.
            </p>
            <LoadProfileTable colunas={colunasTabela} linhas={linhasTabela} labelLinha="Jogador · Posição" />
          </>
        )}
      </div>
    </div>
  );
}

function KpiCard({ kpi }: { kpi: KpiCarga }) {
  const est = ESTADO_UI[kpi.estado] ?? ESTADO_UI.insuficiente;
  const subiu = (kpi.delta_pct ?? 0) >= 0;
  return (
    <div
      style={{
        background: cores.bgCartao,
        border: `1px solid ${cores.borda}`,
        borderLeft: `3px solid ${kpi.cor}`,
        borderRadius: raio.md,
        padding: espaco.lg,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: espaco.sm }}>
        <span style={{ fontSize: "0.72rem", letterSpacing: "0.04em", textTransform: "uppercase", color: cores.textoSuave }}>
          {kpi.label}
        </span>
        <span
          style={{
            fontSize: "0.62rem",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.04em",
            color: est.cor,
            background: `color-mix(in srgb, ${est.cor} 16%, transparent)`,
            padding: "2px 8px",
            borderRadius: 999,
          }}
        >
          {est.label}
        </span>
      </div>
      <div className="font-display" style={{ fontSize: "1.7rem", fontWeight: 800, color: "white", lineHeight: 1, fontVariantNumeric: "tabular-nums" }}>
        {kpi.atual !== null ? kpi.atual.toLocaleString("pt-PT") : "—"}
        <span style={{ fontSize: "0.8rem", fontWeight: 600, color: cores.textoSuave, marginLeft: 4 }}>{kpi.unidade}</span>
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: espaco.sm, marginTop: espaco.sm }}>
        {kpi.delta_pct !== null ? (
          <span style={{ fontSize: "0.82rem", fontWeight: 700, color: kpi.estado === "normal" ? cores.textoSuave : est.cor }}>
            {subiu ? "▲" : "▼"} {Math.abs(kpi.delta_pct).toFixed(1)}%
          </span>
        ) : (
          <span style={{ fontSize: "0.75rem", color: cores.textoFraco }}>sem histórico</span>
        )}
        <span style={{ fontSize: "0.72rem", color: cores.textoSuave }}>
          baseline {kpi.baseline !== null ? kpi.baseline.toLocaleString("pt-PT") : "—"} {kpi.unidade}
        </span>
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

function EstadoVazio({ mensagem }: { mensagem: string }) {
  return (
    <div style={{ maxWidth: 600, margin: "80px auto", padding: "0 24px", textAlign: "center" }}>
      <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.95rem" }}>{mensagem}</p>
    </div>
  );
}
