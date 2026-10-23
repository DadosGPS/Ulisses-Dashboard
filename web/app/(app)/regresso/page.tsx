import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { RegressoJogo, type RtpResponse } from "@/components/ui/RegressoJogo";
import { espaco } from "@/lib/theme";

import { obterEquipaAtiva } from "@/lib/equipa-ativa-servidor";
import { obterTr, obterLingua } from "@/lib/i18n/servidor";
import { EstadoVazio } from "@/components/ui/base";
async function obterPlanos(teamId: string, accessToken: string): Promise<RtpResponse | null> {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/rtp`, {
      headers: { Authorization: `Bearer ${accessToken}`, "X-Lingua": await obterLingua() },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function RegressoPage() {
  const tr = await obterTr();
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;

  const { data: membro } = await obterEquipaAtiva(supabase, session.user.id);
  if (!membro) return <EstadoVazio mensagem={tr("Ainda não estás associado a nenhuma equipa.")} />;

  const dados = await obterPlanos(membro.team_id, session.access_token);

  return (
    <div>
      <PageHeader titulo={tr("Regresso ao Jogo")} subtitulo={tr("Progressão por etapas em % da exigência de jogo pré-lesão, acompanhada pelo GPS")} />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {dados ? (
          <RegressoJogo teamId={membro.team_id} dadosIniciais={dados} />
        ) : (
          <EstadoVazio mensagem={tr("Não foi possível carregar os planos. Confirma que a API está a correr.")} />
        )}
      </div>
    </div>
  );
}

