import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { KpiTile } from "@/components/ui/KpiTile";
import { RankingCard } from "@/components/ui/RankingCard";
import { AlertList } from "@/components/ui/AlertList";
import { Resumo5W1HCard } from "@/components/ui/Resumo5W1HCard";
import { MicrocicloSelector } from "@/components/ui/MicrocicloSelector";
import { cores, espaco } from "@/lib/theme";
import type { DashboardResponse } from "@/lib/types";

async function obterDashboard(teamId: string, accessToken: string, microciclo?: string): Promise<DashboardResponse> {
  const url = new URL(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/dashboard`);
  if (microciclo) url.searchParams.set("microciclo", microciclo);
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Falha ao carregar o dashboard (${res.status}).`);
  }
  return res.json();
}

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ microciclo?: string }>;
}) {
  const { microciclo } = await searchParams;

  // Autenticação já garantida por app/(app)/layout.tsx — aqui só se obtêm os
  // dados necessários a esta página (token para a API, id da equipa).
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

  let dados: DashboardResponse;
  try {
    dados = await obterDashboard(membro.team_id, session.access_token, microciclo);
  } catch {
    return <EstadoVazio mensagem="Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr." />;
  }

  if (!dados.tem_dados) {
    return (
      <EstadoVazio mensagem="Ainda não há dados carregados para esta equipa.">
        <Link
          href="/upload"
          style={{
            display: "inline-block",
            marginTop: 16,
            padding: "10px 20px",
            background: cores.cargaInterna,
            borderRadius: 8,
            color: "white",
            fontWeight: 700,
            fontSize: "0.85rem",
            textDecoration: "none",
          }}
        >
          📤 Carregar dados
        </Link>
      </EstadoVazio>
    );
  }

  return (
    <div>
      <PageHeader
        titulo="Dashboard"
        subtitulo={session.user.email}
        acoes={<MicrocicloSelector opcoes={dados.microciclos_disponiveis} atual={dados.microciclo_selecionado} />}
      />

      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: espaco.md, marginBottom: espaco.xxl }}>
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

        {dados.resumo_5w1h && (
          <div style={{ marginBottom: espaco.xxl }}>
            <Resumo5W1HCard resumo={dados.resumo_5w1h} />
          </div>
        )}

        <SecaoTitulo>🚨 Alertas Prioritários</SecaoTitulo>
        <div style={{ marginBottom: espaco.xxl }}>
          <AlertList alertas={dados.alertas} />
        </div>

        <SecaoTitulo>🏆 Ranking de Desempenho</SecaoTitulo>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: espaco.md }}>
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

function EstadoVazio({ mensagem, children }: { mensagem: string; children?: React.ReactNode }) {
  return (
    <div style={{ maxWidth: 600, margin: "80px auto", padding: "0 24px", textAlign: "center" }}>
      <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.95rem" }}>{mensagem}</p>
      {children}
    </div>
  );
}
