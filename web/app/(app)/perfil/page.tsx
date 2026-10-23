import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { PerfilJogadores } from "@/components/ui/PerfilJogadores";
import { espaco } from "@/lib/theme";
import type { PerfilResponse } from "@/lib/types";

import { obterEquipaAtiva } from "@/lib/equipa-ativa-servidor";
import { obterTr, obterLingua } from "@/lib/i18n/servidor";
import { EstadoVazio } from "@/components/ui/base";
async function obterPerfil(teamId: string, accessToken: string, momento?: string): Promise<PerfilResponse | null> {
  try {
    const q = momento && /^[1-4]$/.test(momento) ? `?momento=${momento}` : "";
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/perfil${q}`, {
      headers: { Authorization: `Bearer ${accessToken}`, "X-Lingua": await obterLingua() },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function PerfilPage({ searchParams }: { searchParams: Promise<{ momento?: string }> }) {
  const tr = await obterTr();
  const { momento } = await searchParams;
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;

  const { data: membro } = await obterEquipaAtiva(supabase, session.user.id);
  if (!membro) return <EstadoVazio mensagem={tr("Ainda não estás associado a nenhuma equipa.")} />;

  const dados = await obterPerfil(membro.team_id, session.access_token, momento);

  return (
    <div>
      <PageHeader titulo={tr("Perfil dos Jogadores")} subtitulo={dados?.fonte === "academia"
        ? tr("Testes da Academia comparados no plantel — velocidade, 1 km e saltos")
        : tr("Pontos fortes e fracos por testes — STEN (1–10) vs plantel")} />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {dados ? (
          <PerfilJogadores dados={dados} />
        ) : (
          <EstadoVazio mensagem={tr("Não foi possível carregar os perfis. Confirma que a API está a correr e que há testes importados.")} />
        )}
      </div>
    </div>
  );
}

