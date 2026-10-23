import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { LesoesGestao } from "@/components/ui/LesoesGestao";
import { espaco } from "@/lib/theme";
import type { LesoesResponse } from "@/lib/types";

import { obterEquipaAtiva } from "@/lib/equipa-ativa-servidor";
import { obterTr, obterLingua } from "@/lib/i18n/servidor";
import { EstadoVazio } from "@/components/ui/base";
async function obterLesoes(teamId: string, accessToken: string): Promise<LesoesResponse | null> {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/lesoes`, {
      headers: { Authorization: `Bearer ${accessToken}`, "X-Lingua": await obterLingua() },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function LesoesPage() {
  const tr = await obterTr();
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;

  const { data: membro } = await obterEquipaAtiva(supabase, session.user.id);
  if (!membro) return <EstadoVazio mensagem={tr("Ainda não estás associado a nenhuma equipa.")} />;

  const dados = await obterLesoes(membro.team_id, session.access_token);

  return (
    <div>
      <PageHeader titulo={tr("Lesões e Disponibilidade")} subtitulo={tr("Histórico de lesões, body map e calendário de disponibilidade")} />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {dados && dados.tem_dados ? (
          <LesoesGestao teamId={membro.team_id} dadosIniciais={dados} />
        ) : (
          <EstadoVazio mensagem={tr("Sem jogadores. Importa dados da equipa primeiro (ou a API está indisponível).")} />
        )}
      </div>
    </div>
  );
}

