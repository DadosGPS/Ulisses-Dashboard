import { Suspense } from "react";
import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { Microciclos } from "@/components/planeamento/Microciclos";
import { obterEquipaAtiva } from "@/lib/equipa-ativa-servidor";
import { espaco } from "@/lib/theme";

export default async function PlaneamentoMicrociclosPage() {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;
  const { data: membro } = await obterEquipaAtiva(supabase, session.user.id);

  return (
    <div>
      <PageHeader titulo="Planeamento" subtitulo="Microciclos da época — datas, perfil e fator semanal face à referência de jogo" />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {membro ? (
          <Suspense>
            <Microciclos teamId={membro.team_id} />
          </Suspense>
        ) : (
          <p>Ainda não estás associado a nenhuma equipa.</p>
        )}
      </div>
    </div>
  );
}
