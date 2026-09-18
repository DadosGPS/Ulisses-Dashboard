import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { LesoesGestao } from "@/components/ui/LesoesGestao";
import { espaco } from "@/lib/theme";
import type { LesoesResponse } from "@/lib/types";

async function obterLesoes(teamId: string, accessToken: string): Promise<LesoesResponse | null> {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/lesoes`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function LesoesPage() {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;

  const { data: membro } = await supabase
    .from("team_members").select("team_id").eq("user_id", session.user.id).limit(1).single();
  if (!membro) return <EstadoVazio mensagem="Ainda não estás associado a nenhuma equipa." />;

  const dados = await obterLesoes(membro.team_id, session.access_token);

  return (
    <div>
      <PageHeader titulo="Lesões e Disponibilidade" subtitulo="Histórico de lesões, body map e calendário de disponibilidade" />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {dados && dados.tem_dados ? (
          <LesoesGestao teamId={membro.team_id} dadosIniciais={dados} />
        ) : (
          <EstadoVazio mensagem="Sem jogadores. Importa dados da equipa primeiro (ou a API está indisponível)." />
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
