import { Suspense } from "react";
import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { Sessoes } from "@/components/planeamento/Sessoes";
import { PseEsperadaVsReal } from "@/components/ui/PseEsperadaVsReal";
import { CargaExternaPlaneadaVsReal } from "@/components/ui/CargaExternaPlaneadaVsReal";
import { SecaoTitulo } from "@/components/ui/base";
import { obterEquipaAtiva } from "@/lib/equipa-ativa-servidor";
import { espaco } from "@/lib/theme";
import type { CargaSemanaResponse, PseSemanaResponse } from "@/lib/types";

async function obter<T>(url: string, token: string): Promise<T | null> {
  try {
    const r = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${url}`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" });
    return r.ok ? r.json() : null;
  } catch {
    return null;
  }
}

export default async function PlaneamentoSessoesPage() {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;
  const { data: membro } = await obterEquipaAtiva(supabase, session.user.id);
  if (!membro) return <p style={{ padding: espaco.xxl }}>Ainda não estás associado a nenhuma equipa.</p>;

  const [pseSemana, cargaSemana] = await Promise.all([
    obter<PseSemanaResponse>(`/api/teams/${membro.team_id}/planeamento/pse-semana`, session.access_token),
    obter<CargaSemanaResponse>(`/api/teams/${membro.team_id}/planeamento/carga-semana`, session.access_token),
  ]);

  return (
    <div>
      <PageHeader titulo="Planeamento das sessões" subtitulo="Dia a dia do microciclo — tipo, dia MD, PSE, duração e carga externa planeadas vs realizadas" />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px`, display: "flex", flexDirection: "column", gap: espaco.xxl }}>
        <Suspense>
          <Sessoes teamId={membro.team_id} />
        </Suspense>

        {pseSemana?.tem_dados && (
          <div>
            <SecaoTitulo>PSE esperada vs real por dia MD</SecaoTitulo>
            <PseEsperadaVsReal teamId={membro.team_id} dadosIniciais={pseSemana} />
          </div>
        )}
        {cargaSemana?.tem_dados && (
          <div>
            <SecaoTitulo>Carga externa — planeado vs real por dia MD</SecaoTitulo>
            <CargaExternaPlaneadaVsReal teamId={membro.team_id} dadosIniciais={cargaSemana} />
          </div>
        )}
      </div>
    </div>
  );
}
