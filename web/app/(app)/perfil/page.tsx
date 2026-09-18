import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { PerfilJogadores } from "@/components/ui/PerfilJogadores";
import { espaco } from "@/lib/theme";
import type { PerfilResponse } from "@/lib/types";

async function obterPerfil(teamId: string, accessToken: string): Promise<PerfilResponse | null> {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/perfil`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function PerfilPage() {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;

  const { data: membro } = await supabase
    .from("team_members").select("team_id").eq("user_id", session.user.id).limit(1).single();
  if (!membro) return <EstadoVazio mensagem="Ainda não estás associado a nenhuma equipa." />;

  const dados = await obterPerfil(membro.team_id, session.access_token);

  return (
    <div>
      <PageHeader titulo="Perfil dos Jogadores" subtitulo="Pontos fortes e fracos por testes — STEN (1–10) vs posição" />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {dados ? (
          <PerfilJogadores dados={dados} />
        ) : (
          <EstadoVazio mensagem="Não foi possível carregar os perfis. Confirma que a API está a correr e que há testes importados." />
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
