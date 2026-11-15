import { Suspense } from "react";
import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { EpocaVista } from "@/components/planeamento/EpocaVista";
import { Microciclos } from "@/components/planeamento/Microciclos";
import { obterEquipaAtiva } from "@/lib/equipa-ativa-servidor";
import { espaco } from "@/lib/theme";
import { obterTr } from "@/lib/i18n/servidor";

/** Planear · Época — a vista da época (fases, jogos, planeado vs realizado)
 * e, por baixo, os microciclos para criar e editar (antes eram duas páginas:
 * «Planeamento» e «Planeamento · Época»). */
export default async function PlaneamentoEpocaPage() {
  const tr = await obterTr();
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;
  const { data: membro } = await obterEquipaAtiva(supabase, session.user.id);
  return (
    <div>
      <PageHeader titulo={tr("Planear · Época e microciclos")} subtitulo={tr("Fases, jogos e carga planeada vs realizada semana a semana; por baixo, os microciclos para criar e editar")} />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px`, display: "flex", flexDirection: "column", gap: espaco.xxl }}>
        {membro ? (
          <>
            <EpocaVista teamId={membro.team_id} />
            <Suspense>
              <Microciclos teamId={membro.team_id} semEvolucao />
            </Suspense>
          </>
        ) : <p>{tr("Ainda não estás associado a nenhuma equipa.")}</p>}
      </div>
    </div>
  );
}
