import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { EpocaVista } from "@/components/planeamento/EpocaVista";
import { obterEquipaAtiva } from "@/lib/equipa-ativa-servidor";
import { espaco } from "@/lib/theme";
import { obterTr } from "@/lib/i18n/servidor";

export default async function PlaneamentoEpocaPage() {
  const tr = await obterTr();
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;
  const { data: membro } = await obterEquipaAtiva(supabase, session.user.id);
  return (
    <div>
      <PageHeader titulo={tr("Planeamento · Época")} subtitulo={tr("Fases, microciclos e jogos da época, com a carga planeada vs realizada semana a semana")} />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {membro ? <EpocaVista teamId={membro.team_id} /> : <p>{tr("Ainda não estás associado a nenhuma equipa.")}</p>}
      </div>
    </div>
  );
}
