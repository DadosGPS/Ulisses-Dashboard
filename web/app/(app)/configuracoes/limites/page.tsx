import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { EditorLimites, type Limites } from "@/components/ui/EditorLimites";
import { cores, espaco } from "@/lib/theme";

async function obterLimites(teamId: string, accessToken: string): Promise<Limites> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/configuracoes/limites`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Falha (${res.status}).`);
  return res.json();
}

export default async function ConfigLimitesPage() {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;

  const { data: membro } = await supabase.from("team_members").select("team_id").eq("user_id", session.user.id).limit(1).single();
  if (!membro) return <EstadoVazio mensagem="Ainda não estás associado a nenhuma equipa." />;

  let limites: Limites;
  try {
    limites = await obterLimites(membro.team_id, session.access_token);
  } catch {
    return <EstadoVazio mensagem="Não foi possível ligar à API." />;
  }

  return (
    <div>
      <PageHeader titulo="Definições · Limites e Alertas" subtitulo="Limiares que disparam os alertas do dashboard" />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        <p style={{ color: cores.textoSuave, fontSize: "0.85rem", maxWidth: 640, margin: `0 0 ${espaco.lg}px` }}>
          Ajusta os limiares à realidade da tua equipa. Cada métrica dispara <strong>Atenção</strong> a partir do primeiro valor e <strong>Atenção alta</strong> a partir do segundo. Os alertas são pistas de monitorização, não diagnósticos.
        </p>
        <EditorLimites teamId={membro.team_id} iniciais={limites} />
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
