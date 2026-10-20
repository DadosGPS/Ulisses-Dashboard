import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { GestaoMensagens, type MensagensResponse } from "@/components/ui/GestaoMensagens";
import { espaco } from "@/lib/theme";

import { obterEquipaAtiva } from "@/lib/equipa-ativa-servidor";
async function obter(teamId: string, accessToken: string): Promise<MensagensResponse | null> {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/mensagens`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function MensagensPage() {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;
  const { data: membro } = await obterEquipaAtiva(supabase, session.user.id);
  if (!membro) return null;
  const dados = await obter(membro.team_id, session.access_token);

  return (
    <div>
      <PageHeader titulo="Mensagens" subtitulo="Bem-estar todas as manhãs e PSE no fim do treino, por WhatsApp no telemóvel de cada jogador" />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {dados ? (
          <GestaoMensagens teamId={membro.team_id} dadosIniciais={dados} />
        ) : (
          <p style={{ color: "rgb(var(--ink) / 0.6)" }}>Não foi possível carregar as mensagens. Confirma que a API está a correr.</p>
        )}
      </div>
    </div>
  );
}
