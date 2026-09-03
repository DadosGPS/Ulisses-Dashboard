import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { EditorEquipa } from "@/components/ui/EditorEquipa";
import { cores, espaco } from "@/lib/theme";

interface ConfigResponse {
  equipa: { nome: string; desporto: string };
}

async function obterConfig(teamId: string, accessToken: string): Promise<ConfigResponse> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/configuracoes`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Falha (${res.status}).`);
  return res.json();
}

export default async function ConfigEquipaPage() {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;

  const { data: membro } = await supabase
    .from("team_members")
    .select("team_id")
    .eq("user_id", session.user.id)
    .limit(1)
    .single();
  if (!membro) return <EstadoVazio mensagem="Ainda não estás associado a nenhuma equipa." />;

  let dados: ConfigResponse;
  try {
    dados = await obterConfig(membro.team_id, session.access_token);
  } catch {
    return <EstadoVazio mensagem="Não foi possível ligar à API." />;
  }

  return (
    <div>
      <PageHeader titulo="Definições · Equipa" subtitulo="Nome e desporto da equipa" />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        <EditorEquipa teamId={membro.team_id} nomeInicial={dados.equipa.nome} desportoInicial={dados.equipa.desporto} />
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
