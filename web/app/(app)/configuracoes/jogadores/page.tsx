import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { EditorJogadores } from "@/components/ui/EditorJogadores";
import { EstadoAtletas } from "@/components/ui/EstadoAtletas";
import { cores, espaco } from "@/lib/theme";
import type { EstadoJogador } from "@/lib/types";

import { obterEquipaAtiva } from "@/lib/equipa-ativa-servidor";
import { obterTr, obterLingua } from "@/lib/i18n/servidor";
import { EstadoVazio } from "@/components/ui/base";
interface ConfigResponse {
  jogadores: EstadoJogador[];
}

async function obterConfig(teamId: string, accessToken: string): Promise<ConfigResponse> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/configuracoes`, {
    headers: { Authorization: `Bearer ${accessToken}`, "X-Lingua": await obterLingua() },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Falha (${res.status}).`);
  return res.json();
}

export default async function ConfigJogadoresPage() {
  const tr = await obterTr();
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;

  const { data: membro } = await obterEquipaAtiva(supabase, session.user.id);
  if (!membro) return <EstadoVazio mensagem={tr("Ainda não estás associado a nenhuma equipa.")} />;

  let dados: ConfigResponse;
  try {
    dados = await obterConfig(membro.team_id, session.access_token);
  } catch {
    return <EstadoVazio mensagem={tr("Não foi possível ligar à API.")} />;
  }

  return (
    <div>
      <PageHeader titulo={tr("Definições · Jogadores")} subtitulo={tr("Adicionar, editar e gerir o plantel e a disponibilidade")} />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        <EditorJogadores teamId={membro.team_id} jogadoresIniciais={dados.jogadores} />

        <h2 className="font-display" style={{ fontSize: "1rem", fontWeight: 600, color: cores.textoForte, margin: `${espaco.xxl}px 0 ${espaco.md}px` }}>
          {tr("Disponibilidade / Estado")}</h2>
        <EstadoAtletas teamId={membro.team_id} estadosIniciais={dados.jogadores} />
      </div>
    </div>
  );
}

