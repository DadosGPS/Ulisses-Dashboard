import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { ProntidaoPainel, type ProntidaoResponse } from "@/components/ui/ProntidaoPainel";
import { espaco } from "@/lib/theme";

async function obterProntidao(teamId: string, accessToken: string): Promise<ProntidaoResponse | null> {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/prontidao`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function ProntidaoPage() {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;

  const { data: membro } = await supabase
    .from("team_members").select("team_id").eq("user_id", session.user.id).limit(1).single();
  if (!membro) return <EstadoVazio mensagem="Ainda não estás associado a nenhuma equipa." />;

  const dados = await obterProntidao(membro.team_id, session.access_token);

  return (
    <div>
      <PageHeader titulo="Prontidão" subtitulo="CMJ e bem-estar face à média do próprio jogador, com o ACWR diário e a sua tendência" />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {dados && dados.tem_dados ? (
          <ProntidaoPainel dados={dados} />
        ) : (
          <EstadoVazio mensagem={dados?.motivo ?? "Não foi possível carregar a prontidão. Confirma que a API está a correr e que há sessões importadas."} />
        )}
      </div>
    </div>
  );
}

function EstadoVazio({ mensagem }: { mensagem: string }) {
  return (
    <div style={{ maxWidth: 600, margin: "80px auto", padding: "0 24px", textAlign: "center" }}>
      <p style={{ color: "rgb(var(--ink) / 0.6)", fontSize: "0.95rem" }}>{mensagem}</p>
    </div>
  );
}
