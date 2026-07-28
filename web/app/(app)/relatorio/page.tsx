import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { RelatorioEditor } from "@/components/ui/RelatorioEditor";
import { cores, espaco, raio } from "@/lib/theme";

async function obterTexto(teamId: string, accessToken: string): Promise<{ texto: string; data: string | null }> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/relatorio/texto`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Falha ao carregar o resumo (${res.status}).`);
  return res.json();
}

export default async function RelatorioPage() {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) return null;

  const { data: membro } = await supabase
    .from("team_members")
    .select("team_id")
    .eq("user_id", session.user.id)
    .limit(1)
    .single();

  if (!membro) return <EstadoVazio mensagem="Ainda não estás associado a nenhuma equipa." />;

  let dados: { texto: string; data: string | null };
  try {
    dados = await obterTexto(membro.team_id, session.access_token);
  } catch {
    return <EstadoVazio mensagem="Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr." />;
  }

  return (
    <div>
      <PageHeader titulo="Relatório do Dia" subtitulo="Resumo 5W+1H editável + gráficos da sessão mais recente, pronto para exportar em PDF" />

      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px`, maxWidth: 760 }}>
        <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.lg }}>
          <div style={{ fontSize: "0.78rem", color: cores.textoSuave, marginBottom: espaco.md }}>
            Sessão de {dados.data ?? "—"}
          </div>
          <RelatorioEditor teamId={membro.team_id} textoInicial={dados.texto} />
        </div>

        <p style={{ color: cores.textoFraco, fontSize: "0.76rem", marginTop: espaco.md }}>
          O PDF inclui este texto e gráficos de Distância Total, Acelerações, Desacelerações, Velocidade Máxima e HSR
          de todos os jogadores da sessão mais recente.
        </p>
      </div>
    </div>
  );
}

function EstadoVazio({ mensagem }: { mensagem: string }) {
  return (
    <div style={{ maxWidth: 600, margin: "80px auto", padding: "0 24px", textAlign: "center" }}>
      <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.95rem" }}>{mensagem}</p>
    </div>
  );
}
