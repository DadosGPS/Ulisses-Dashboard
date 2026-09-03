import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { TendenciasView, type MetricaDef } from "@/components/ui/TendenciasView";
import { cores, espaco } from "@/lib/theme";

interface CargaExternaResponse {
  tem_dados: boolean;
  metricas: MetricaDef[];
  evolucao: Record<string, { data: string; valor: number | null }[]>;
}

async function obterDados(
  teamId: string,
  accessToken: string,
  filtros: { jogador?: string; microciclo?: string; dia_md?: string }
): Promise<CargaExternaResponse> {
  const url = new URL(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/carga-externa`);
  if (filtros.jogador) url.searchParams.set("jogador", filtros.jogador);
  if (filtros.microciclo) url.searchParams.set("microciclo", filtros.microciclo);
  if (filtros.dia_md) url.searchParams.set("dia_md", filtros.dia_md);
  const res = await fetch(url, { headers: { Authorization: `Bearer ${accessToken}` }, cache: "no-store" });
  if (!res.ok) throw new Error(`Falha (${res.status}).`);
  return res.json();
}

export default async function TendenciasPage({
  searchParams,
}: {
  searchParams: Promise<{ jogador?: string; microciclo?: string; dia_md?: string }>;
}) {
  const { jogador, microciclo, dia_md } = await searchParams;
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
    dados = await obterDados(membro.team_id, session.access_token, { jogador, microciclo, dia_md });
  } catch {
    return <EstadoVazio mensagem="Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr." />;
  }

  const temEvolucao = dados.tem_dados && dados.metricas.some((m) => (dados.evolucao[m.chave] ?? []).length > 1);

  return (
    <div>
      <PageHeader
        titulo="Tendências"
        subtitulo="Evolução por métrica, média móvel e variação semanal (carga externa)"
      />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {temEvolucao ? (
          <TendenciasView metricas={dados.metricas} evolucao={dados.evolucao} />
        ) : (
          <EstadoVazio mensagem="Ainda não há histórico suficiente para calcular tendências." />
        )}
      </div>
    </div>
  );
}

function EstadoVazio({ mensagem }: { mensagem: string }) {
  return (
    <div style={{ maxWidth: 600, margin: "80px auto", padding: "0 24px", textAlign: "center" }}>
      <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.95rem" }}>{mensagem}</p>
    </div>
  );
}
