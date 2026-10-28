import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { EditorLimites, type Limites } from "@/components/ui/EditorLimites";
import { ResumoDecisoes } from "@/components/ui/ResumoDecisoes";
import { cores, espaco } from "@/lib/theme";

import { obterEquipaAtiva } from "@/lib/equipa-ativa-servidor";
import { obterTr, obterLingua } from "@/lib/i18n/servidor";
import { EstadoVazio } from "@/components/ui/base";
async function obterLimites(teamId: string, accessToken: string): Promise<Limites> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/configuracoes/limites`, {
    headers: { Authorization: `Bearer ${accessToken}`, "X-Lingua": await obterLingua() },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Falha (${res.status}).`);
  return res.json();
}

export default async function ConfigLimitesPage() {
  const tr = await obterTr();
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;

  const { data: membro } = await obterEquipaAtiva(supabase, session.user.id);
  if (!membro) return <EstadoVazio mensagem={tr("Ainda não estás associado a nenhuma equipa.")} />;

  let limites: Limites;
  try {
    limites = await obterLimites(membro.team_id, session.access_token);
  } catch {
    return <EstadoVazio mensagem={tr("Não foi possível ligar à API.")} />;
  }

  return (
    <div>
      <PageHeader titulo={tr("Definições · Limites e Alertas")} subtitulo={tr("Limiares que disparam os alertas do dashboard")} />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        <p style={{ color: cores.textoSuave, fontSize: "0.85rem", maxWidth: 640, margin: `0 0 ${espaco.lg}px` }}>
          {tr("Ajusta os limiares à realidade da tua equipa. Cada métrica dispara")}{" "}<strong>{tr("Atenção")}</strong> {tr("a partir do primeiro valor e")}{" "}<strong>{tr("Atenção alta")}</strong> {tr("a partir do segundo. Os alertas são pistas de monitorização, não diagnósticos.")}</p>
        <EditorLimites teamId={membro.team_id} iniciais={limites} />
        <ResumoDecisoes teamId={membro.team_id} />
      </div>
    </div>
  );
}

