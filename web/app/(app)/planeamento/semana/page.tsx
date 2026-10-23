import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { SemanaJogadores } from "@/components/planeamento/SemanaJogadores";
import { obterEquipaAtiva } from "@/lib/equipa-ativa-servidor";
import { espaco } from "@/lib/theme";
import { obterTr } from "@/lib/i18n/servidor";

export default async function PlaneamentoSemanaPage() {
  const tr = await obterTr();
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;
  const { data: membro } = await obterEquipaAtiva(supabase, session.user.id);
  return (
    <div>
      <PageHeader titulo={tr("Planeamento · Semana por jogador")} subtitulo={tr("Quanto falta a cada jogador para o objetivo da semana, e quem precisa de compensação depois do jogo")} />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {membro ? <SemanaJogadores teamId={membro.team_id} /> : <p>{tr("Ainda não estás associado a nenhuma equipa.")}</p>}
      </div>
    </div>
  );
}
