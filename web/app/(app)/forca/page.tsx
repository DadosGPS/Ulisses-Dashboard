import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { ForcaGinasio } from "@/components/forca/ForcaGinasio";
import { obterEquipaAtiva } from "@/lib/equipa-ativa-servidor";
import { espaco } from "@/lib/theme";
import { obterTr } from "@/lib/i18n/servidor";
import { EstadoVazio } from "@/components/ui/base";

export default async function ForcaPage() {
  const tr = await obterTr();
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;
  const { data: membro } = await obterEquipaAtiva(supabase, session.user.id);
  return (
    <div>
      <PageHeader titulo={tr("Força e Ginásio")} subtitulo={tr("Prescrição, registo por jogador e progressão de força — a PSE do ginásio entra na carga interna do dia")} />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px`, maxWidth: 1200 }}>
        {membro ? <ForcaGinasio teamId={membro.team_id} /> : <EstadoVazio mensagem={tr("Ainda não estás associado a nenhuma equipa.")} />}
      </div>
    </div>
  );
}
