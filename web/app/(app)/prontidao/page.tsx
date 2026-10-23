import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { ProntidaoPainel, type ProntidaoResponse } from "@/components/ui/ProntidaoPainel";
import { espaco } from "@/lib/theme";

import { obterEquipaAtiva } from "@/lib/equipa-ativa-servidor";
import { obterTr, obterLingua } from "@/lib/i18n/servidor";
import { EstadoVazio } from "@/components/ui/base";
async function obterProntidao(teamId: string, accessToken: string): Promise<ProntidaoResponse | null> {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/prontidao`, {
      headers: { Authorization: `Bearer ${accessToken}`, "X-Lingua": await obterLingua() },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function ProntidaoPage() {
  const tr = await obterTr();
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;

  const { data: membro } = await obterEquipaAtiva(supabase, session.user.id);
  if (!membro) return <EstadoVazio mensagem={tr("Ainda não estás associado a nenhuma equipa.")} />;

  const dados = await obterProntidao(membro.team_id, session.access_token);

  return (
    <div>
      <PageHeader titulo={tr("Prontidão")} subtitulo={tr("CMJ e bem-estar face à média do próprio jogador, com o ACWR diário e a sua tendência")} />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {dados && dados.tem_dados ? (
          <ProntidaoPainel dados={dados} />
        ) : (
          <EstadoVazio mensagem={dados?.motivo ?? tr("Não foi possível carregar a prontidão. Confirma que a API está a correr e que há sessões importadas.")} />
        )}
      </div>
    </div>
  );
}

