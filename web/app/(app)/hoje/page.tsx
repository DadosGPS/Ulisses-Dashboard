import { createClient } from "@/lib/supabase/server";
import { obterEquipaAtiva } from "@/lib/equipa-ativa-servidor";
import { PainelHoje } from "@/components/hoje/PainelHoje";
import { obterTr, obterLingua } from "@/lib/i18n/servidor";
import { cores } from "@/lib/theme";

export default async function HojePage({ searchParams }: { searchParams: Promise<{ data?: string }> }) {
  const tr = await obterTr();
  const { data } = await searchParams;
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;
  const { data: membro } = await obterEquipaAtiva(supabase, session.user.id);
  if (!membro) {
    return <p style={{ padding: 48, color: cores.textoSuave }}>{tr("Ainda não estás associado a nenhuma equipa.")}</p>;
  }
  // Primeira carga no servidor (como as outras páginas): o ecrã chega já com
  // as tarefas; o cliente só volta a pedir ao mudar de dia ou depois de agir.
  let inicial = null;
  try {
    const q = data && /^\d{4}-\d{2}-\d{2}$/.test(data) ? `?data=${data}` : "";
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${membro.team_id}/hoje${q}`, {
      headers: { Authorization: `Bearer ${session.access_token}`, "X-Lingua": await obterLingua() },
      cache: "no-store",
    });
    if (res.ok) inicial = await res.json();
  } catch { /* o cliente tenta outra vez */ }
  return <PainelHoje teamId={membro.team_id} dataInicial={data} inicial={inicial} />;
}
