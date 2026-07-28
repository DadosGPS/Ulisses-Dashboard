import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { LoadProfileTable, type ColunaCarga, type LinhaCarga } from "@/components/ui/LoadProfileTable";
import { cores, espaco, raio } from "@/lib/theme";
import type { PlaneamentoResponse } from "@/lib/types";

const CORES_METRICA: Record<string, string> = {
  "Distância Total (m)": cores.distanciaTotal,
  "HSR (m)": cores.hsr,
  "Sprint (m)": cores.sprint,
  "Carga Interna": cores.cargaInterna,
};

async function obterPlaneamento(teamId: string, accessToken: string): Promise<PlaneamentoResponse> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/planeamento`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Falha ao carregar o planeamento (${res.status}).`);
  return res.json();
}

export default async function PlaneamentoPage() {
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

  if (!membro) {
    return <EstadoVazio mensagem="Ainda não estás associado a nenhuma equipa." />;
  }

  let dados: PlaneamentoResponse;
  try {
    dados = await obterPlaneamento(membro.team_id, session.access_token);
  } catch {
    return <EstadoVazio mensagem="Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr." />;
  }

  if (!dados.tem_dados) {
    return <EstadoVazio mensagem="Ainda não há dados carregados para esta equipa." />;
  }

  if (!dados.tem_jogos) {
    return (
      <EstadoVazio mensagem='Ainda não há sessões marcadas como "Jogo" nos dados — a comparação Treino vs Jogo precisa de pelo menos um jogo registado.' />
    );
  }

  const colunas: ColunaCarga[] = dados.metricas.map((m) => ({
    chave: m,
    label: m.replace(" (m)", "").replace(" (n)", ""),
    cor: CORES_METRICA[m] ?? cores.distanciaTotal,
    casas: 0,
  }));

  const linhas: LinhaCarga[] = dados.dias.map((d) => ({
    jogador: d.dia_md,
    valores: Object.fromEntries(dados.metricas.map((m) => [m, d.valores[m] ?? null])),
  }));

  return (
    <div>
      <PageHeader titulo="Planeamento" subtitulo="Treino vs Jogo — intensidade de cada dia do microciclo, em % da referência de jogo" />

      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        <SecaoTitulo>⚽ Referência de Jogo (média por sessão)</SecaoTitulo>
        <div style={{ display: "grid", gridTemplateColumns: `repeat(${dados.metricas.length}, 1fr)`, gap: espaco.md, marginBottom: espaco.xxl }}>
          {dados.metricas.map((m) => (
            <div
              key={m}
              style={{
                background: cores.bgCartao,
                border: `1px solid ${cores.borda}`,
                borderTop: `2px solid ${CORES_METRICA[m] ?? cores.distanciaTotal}`,
                borderRadius: raio.md,
                padding: espaco.md,
              }}
            >
              <div style={{ fontSize: "0.64rem", color: cores.textoSuave, letterSpacing: "0.06em", textTransform: "uppercase", fontWeight: 600, marginBottom: 4 }}>
                {m.replace(" (m)", "").replace(" (n)", "")}
              </div>
              <div className="font-display" style={{ fontSize: "1.3rem", fontWeight: 700, color: "white" }}>
                {dados.referencia[m]?.toLocaleString("pt-PT") ?? "—"}
              </div>
            </div>
          ))}
        </div>

        <SecaoTitulo>📅 Intensidade por Dia do Microciclo (% vs Jogo)</SecaoTitulo>
        <p style={{ color: cores.textoSuave, fontSize: "0.8rem", marginTop: -8, marginBottom: espaco.md, maxWidth: 640 }}>
          Cor mais intensa = valor mais próximo da intensidade de jogo nesse dia. Dias de tapering (MD-1) e recuperação
          (MD+1/MD+2) são naturalmente mais claros — isso é esperado, não um alerta.
        </p>
        <LoadProfileTable colunas={colunas} linhas={linhas} labelLinha="Dia MD" />
      </div>
    </div>
  );
}

function SecaoTitulo({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="font-display" style={{ fontSize: "1rem", fontWeight: 600, color: "white", margin: `0 0 ${espaco.md}px` }}>
      {children}
    </h2>
  );
}

function EstadoVazio({ mensagem }: { mensagem: string }) {
  return (
    <div style={{ maxWidth: 600, margin: "80px auto", padding: "0 24px", textAlign: "center" }}>
      <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.95rem" }}>{mensagem}</p>
    </div>
  );
}
