import { createClient } from "@/lib/supabase/server";
import { obterEquipaAtiva } from "@/lib/equipa-ativa-servidor";
import { PainelHoje } from "@/components/hoje/PainelHoje";
import { obterTr } from "@/lib/i18n/servidor";
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
  return <PainelHoje teamId={membro.team_id} dataInicial={data} />;
}
