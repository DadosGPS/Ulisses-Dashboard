import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  ComparacaoJogadores,
  type JogadorResumo,
  type MetricaDef,
} from "@/components/ui/ComparacaoJogadores";
import { cores, espaco } from "@/lib/theme";

interface ComparacaoResponse {
  tem_dados: boolean;
  metricas: MetricaDef[];
  jogadores: JogadorResumo[];
  benchmark: Record<string, number | null>;
}

async function obterDados(teamId: string, accessToken: string, f: { microciclo?: string; dia_md?: string }): Promise<ComparacaoResponse> {
  const url = new URL(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/comparacao/jogadores`);
  if (f.microciclo) url.searchParams.set("microciclo", f.microciclo);
  if (f.dia_md) url.searchParams.set("dia_md", f.dia_md);
  const res = await fetch(url, { headers: { Authorization: `Bearer ${accessToken}` }, cache: "no-store" });
  if (!res.ok) throw new Error(`Falha (${res.status}).`);
  return res.json();
}

export default async function ComparacaoPage({
  searchParams,
}: {
  searchParams: Promise<{ microciclo?: string; dia_md?: string }>;
}) {
  const { microciclo, dia_md } = await searchParams;
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

  let dados: ComparacaoResponse;
  try {
    dados = await obterDados(membro.team_id, session.access_token, { microciclo, dia_md });
  } catch {
    return <EstadoVazio mensagem="Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr." />;
  }

  return (
    <div>
      <PageHeader
        titulo="Comparação de Jogadores"
        subtitulo="Compara até 4 jogadores lado a lado, face à média da equipa"
      />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {!dados.tem_dados || dados.jogadores.length === 0 ? (
          <EstadoVazio mensagem="Ainda não há dados carregados para comparar jogadores." />
        ) : (
          <ComparacaoJogadores metricas={dados.metricas} jogadores={dados.jogadores} benchmark={dados.benchmark} />
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
