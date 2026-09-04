import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { EditorJogadores } from "@/components/ui/EditorJogadores";
import { EstadoAtletas } from "@/components/ui/EstadoAtletas";
import { cores, espaco } from "@/lib/theme";
import type { EstadoJogador } from "@/lib/types";

interface ConfigResponse {
  jogadores: EstadoJogador[];
}

async function obterConfig(teamId: string, accessToken: string): Promise<ConfigResponse> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/configuracoes`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Falha (${res.status}).`);
  return res.json();
}

export default async function ConfigJogadoresPage() {
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
      <PageHeader titulo="Definições · Jogadores" subtitulo="Adicionar, editar e gerir o plantel e a disponibilidade" />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        <EditorJogadores teamId={membro.team_id} jogadoresIniciais={dados.jogadores} />

        <h2 className="font-display" style={{ fontSize: "1rem", fontWeight: 600, color: "white", margin: `${espaco.xxl}px 0 ${espaco.md}px` }}>
          🩺 Disponibilidade / Estado
        </h2>
        <EstadoAtletas teamId={membro.team_id} estadosIniciais={dados.jogadores} />
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
