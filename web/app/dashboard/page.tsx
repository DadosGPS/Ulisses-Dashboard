import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { KpiTile } from "@/components/ui/KpiTile";
import { RankingCard } from "@/components/ui/RankingCard";
import { AlertList } from "@/components/ui/AlertList";
import { cores } from "@/lib/theme";
import type { DashboardResponse } from "@/lib/types";

async function obterDashboard(teamId: string, accessToken: string): Promise<DashboardResponse> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/dashboard`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Falha ao carregar o dashboard (${res.status}).`);
  }
  return res.json();
}

export default async function DashboardPage() {
  const supabase = await createClient();

  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    redirect("/login");
  }

  // team_members criado automaticamente pelo trigger on_auth_user_created
  // (Fase 1/3 do plano) — um utilizador tem sempre pelo menos uma equipa.
  const { data: membro } = await supabase
    .from("team_members")
    .select("team_id")
    .eq("user_id", session.user.id)
    .limit(1)
    .single();

  if (!membro) {
    return <EstadoVazio mensagem="Ainda não estás associado a nenhuma equipa." />;
  }

  let dados: DashboardResponse;
  try {
    dados = await obterDashboard(membro.team_id, session.access_token);
  } catch {
    return <EstadoVazio mensagem="Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr." />;
  }

  if (!dados.tem_dados) {
    return <EstadoVazio mensagem="Ainda não há dados carregados para esta equipa." />;
  }

  return (
    <main style={{ maxWidth: 1100, margin: "0 auto", padding: "28px 24px 60px" }}>
      <h1 style={{ fontSize: "1.4rem", fontWeight: 700, marginBottom: 4 }}>
        Dashboard {dados.microciclo_recente ? `· MC ${dados.microciclo_recente}` : ""}
      </h1>
      <p style={{ color: "rgba(255,255,255,0.45)", fontSize: "0.85rem", marginBottom: 24 }}>
        {session.user.email}
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 24 }}>
        <KpiTile
          label="Carga Interna"
          valor={dados.kpis.carga_interna_media ?? "—"}
          unidade="UA"
          subLabel="média do microciclo"
          cor={cores.cargaInterna}
        />
        <KpiTile
          label="ACWR Médio"
          valor={dados.kpis.acwr_medio ?? "—"}
          unidade=""
          subLabel="0.8–1.3 = zona segura"
          cor={cores.distanciaTotal}
        />
        <KpiTile
          label="Hooper Index"
          valor={dados.kpis.hooper_medio ?? "—"}
          unidade="/20"
          subLabel="média do microciclo"
          cor={cores.hsr}
        />
        <KpiTile
          label="Em Risco"
          valor={dados.kpis.em_risco}
          unidade="jogadores"
          subLabel="ACWR ≥ 1.5 ou Hooper ≥ 14"
          cor={cores.sprint}
        />
      </div>

      <h2 style={{ fontSize: "1rem", fontWeight: 700, margin: "0 0 12px" }}>🚨 Alertas Prioritários</h2>
      <div style={{ marginBottom: 28 }}>
        <AlertList alertas={dados.alertas} />
      </div>

      <h2 style={{ fontSize: "1rem", fontWeight: 700, margin: "0 0 12px" }}>🏆 Ranking de Desempenho</h2>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        {dados.rankings.map((r) => (
          <RankingCard
            key={r.metrica}
            icon="📊"
            titulo={r.metrica}
            cor={r.cor}
            top3={r.top3}
            bottom3={r.bottom3}
            unidade={r.unidade}
          />
        ))}
      </div>
    </main>
  );
}

function EstadoVazio({ mensagem }: { mensagem: string }) {
  return (
    <main style={{ maxWidth: 600, margin: "80px auto", padding: "0 24px", textAlign: "center" }}>
      <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.95rem" }}>{mensagem}</p>
    </main>
  );
}
