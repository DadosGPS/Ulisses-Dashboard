import { Suspense } from "react";
import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { ComparacaoJogadores, type ComparacaoResposta } from "@/components/ui/ComparacaoJogadores";
import { cores, espaco } from "@/lib/theme";

import { obterEquipaAtiva } from "@/lib/equipa-ativa-servidor";
import { obterTr, obterLingua } from "@/lib/i18n/servidor";
import { EstadoVazio } from "@/components/ui/base";
type ComparacaoResponse = ComparacaoResposta;

async function obterDados(teamId: string, accessToken: string, f: { microciclo?: string; dia_md?: string }): Promise<ComparacaoResponse> {
  const url = new URL(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/comparacao/jogadores`);
  url.searchParams.set("contexto", "jogos");
  if (f.microciclo) url.searchParams.set("microciclo", f.microciclo);
  if (f.dia_md) url.searchParams.set("dia_md", f.dia_md);
  const res = await fetch(url, { headers: { Authorization: `Bearer ${accessToken}`, "X-Lingua": await obterLingua() }, cache: "no-store" });
  if (!res.ok) throw new Error(`Falha (${res.status}).`);
  return res.json();
}

export default async function ComparacaoPage({
  searchParams,
}: {
  searchParams: Promise<{ microciclo?: string; dia_md?: string }>;
}) {
  const tr = await obterTr();
  const { microciclo, dia_md } = await searchParams;
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) return null;

  const { data: membro } = await obterEquipaAtiva(supabase, session.user.id);
  if (!membro) return <EstadoVazio mensagem={tr("Ainda não estás associado a nenhuma equipa.")} />;

  let dados: ComparacaoResponse;
  try {
    dados = await obterDados(membro.team_id, session.access_token, { microciclo, dia_md });
  } catch {
    return <EstadoVazio mensagem={tr("Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr.")} />;
  }

  return (
    <div>
      <PageHeader
        titulo={tr("Comparação de Jogadores")}
        subtitulo={tr("Até 3 jogadores, cada um face ao seu próprio normal (ou face ao plantel), em jogos ou treinos, por sessão ou por minuto")}
      />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {/* Mesmo sem jogos ainda, pode haver treinos: o componente escolhe o contexto. */}
        <Suspense><ComparacaoJogadores teamId={membro.team_id} inicial={dados} /></Suspense>
      </div>
    </div>
  );
}

