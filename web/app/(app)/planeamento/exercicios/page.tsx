import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { ExerciciosBiblioteca } from "@/components/planeamento/ExerciciosBiblioteca";
import { obterEquipaAtiva } from "@/lib/equipa-ativa-servidor";
import { espaco } from "@/lib/theme";
import { obterTr } from "@/lib/i18n/servidor";

export default async function PlaneamentoExerciciosPage() {
  const tr = await obterTr();
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;
  const { data: membro } = await obterEquipaAtiva(supabase, session.user.id);
  return (
    <div>
      <PageHeader titulo={tr("Planeamento · Exercícios")} subtitulo={tr("Biblioteca da academia com a carga típica de cada exercício — para planear a sessão a partir dos exercícios")} />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        <ExerciciosBiblioteca teamId={membro?.team_id ?? null} />
      </div>
    </div>
  );
}
