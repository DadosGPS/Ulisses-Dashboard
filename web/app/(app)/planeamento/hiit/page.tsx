import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { CalculadoraHiit } from "@/components/planeamento/CalculadoraHiit";
import { obterEquipaAtiva } from "@/lib/equipa-ativa-servidor";
import { espaco } from "@/lib/theme";
import type { VelocidadeResponse } from "@/lib/types";
import { obterTr, obterLingua } from "@/lib/i18n/servidor";
import { EstadoVazio } from "@/components/ui/base";

async function obterVelocidade(teamId: string, accessToken: string): Promise<VelocidadeResponse | null> {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/velocidade`, {
      headers: { Authorization: `Bearer ${accessToken}`, "X-Lingua": await obterLingua() },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

/** Calculadora de HIIT: distâncias individuais a partir da MSS (modo HSR) ou
 * da MAS (modo % MAS) de cada jogador. Os dados vêm da página Velocidade. */
export default async function PlaneamentoHiitPage() {
  const tr = await obterTr();
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;
  const { data: membro } = await obterEquipaAtiva(supabase, session.user.id);
  if (!membro) return <EstadoVazio mensagem={tr("Ainda não estás associado a nenhuma equipa.")} />;

  const dados = await obterVelocidade(membro.team_id, session.access_token);

  return (
    <div>
      <PageHeader
        titulo={tr("Planear · Calculadora HIIT")}
        subtitulo={tr("Distância e tempo de cada jogador a partir da sua velocidade máxima (HSR) ou da sua MAS")}
      />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {dados ? (
          <CalculadoraHiit dados={dados} />
        ) : (
          <EstadoVazio mensagem={tr("Não foi possível carregar a velocidade dos jogadores. Confirma que há sessões de GPS importadas.")} />
        )}
      </div>
    </div>
  );
}
