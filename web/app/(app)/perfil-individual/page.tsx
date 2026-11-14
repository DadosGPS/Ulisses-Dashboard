import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { PerfilIndividual, type PerfilIndividualResponse } from "@/components/ui/PerfilIndividual";
import { espaco } from "@/lib/theme";
import { obterEquipaAtiva } from "@/lib/equipa-ativa-servidor";
import { obterTr, obterLingua } from "@/lib/i18n/servidor";
import { EstadoVazio } from "@/components/ui/base";

async function obter(teamId: string, accessToken: string, dias: string): Promise<PerfilIndividualResponse | null> {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/perfil-individual?dias=${dias}`, {
      headers: { Authorization: `Bearer ${accessToken}`, "X-Lingua": await obterLingua() },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function PerfilIndividualPage({ searchParams }: { searchParams: Promise<{ dias?: string }> }) {
  const tr = await obterTr();
  const { dias } = await searchParams;
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;
  const { data: membro } = await obterEquipaAtiva(supabase, session.user.id);
  if (!membro) return <EstadoVazio mensagem={tr("Ainda não estás associado a nenhuma equipa.")} />;

  const dados = await obter(membro.team_id, session.access_token, dias && /^(0|7|28)$/.test(dias) ? dias : "28");

  return (
    <div>
      <PageHeader titulo={tr("Perfil individual")} subtitulo={tr("Velocidade, zonas relativas e acelerações face às capacidades de cada jogador")} />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {dados ? <PerfilIndividual dados={dados} /> : (
          <EstadoVazio mensagem={tr("Não foi possível carregar o perfil individual. Confirma que a API está a correr e que há sessões importadas.")} />
        )}
      </div>
    </div>
  );
}
