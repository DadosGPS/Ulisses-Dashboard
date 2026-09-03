"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useLoadUser } from "@/lib/use-load-user";
import { createClient } from "@/lib/supabase/client";
import { cores, espaco, raio } from "@/lib/theme";
import { StatusBadge, StatusIndicator } from "@/components/ui/StatusIndicator";
import { KpiCargaCard, type KpiCarga } from "@/components/ui/KpiCargaCard";
import { PageHeader } from "@/components/layout/PageHeader";

interface SquadStatus {
  normal: number;
  attention: number;
  highAttention: number;
  total: number;
}

interface Alert {
  player_id: string;
  player_name: string;
  status: "normal" | "attention" | "high-attention";
  primary_reason: string;
  reason_text: string;
  metric_value: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const user = useLoadUser();
  const [loading, setLoading] = useState(true);
  const [squadStatus, setSquadStatus] = useState<SquadStatus | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [kpis, setKpis] = useState<KpiCarga[]>([]);
  const [sessaoRecente, setSessaoRecente] = useState<string | null>(null);

  useEffect(() => {
    if (user.isLoading) return;
    if (!user.teamId) {
      router.push("/login");
      return;
    }
    fetchDashboardData();
  }, [user.teamId, user.isLoading]);

  async function fetchDashboardData() {
    try {
      setLoading(true);
      const teamId = user.teamId;

      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) {
        router.push("/login");
        return;
      }

      const apiBase = `${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}`;
      const opcoes = { headers: { Authorization: `Bearer ${token}` } };

      const [statusRes, alertsRes, cargaRes] = await Promise.all([
        fetch(`${apiBase}/dashboard/squad-status`, opcoes),
        fetch(`${apiBase}/dashboard/attention-required`, opcoes),
        fetch(`${apiBase}/carga-externa`, opcoes),
      ]);

      if (statusRes.ok) setSquadStatus(await statusRes.json());
      if (alertsRes.ok) setAlerts(await alertsRes.json());
      if (cargaRes.ok) {
        const carga = await cargaRes.json();
        setKpis(carga.kpis ?? []);
        setSessaoRecente(carga.sessao_recente ?? null);
      }
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div style={{ padding: espaco.xl, display: "flex", alignItems: "center", justifyContent: "center", minHeight: "60vh", color: cores.textoSuave }}>
        A carregar o estado da equipa…
      </div>
    );
  }

  const dataLegivel = sessaoRecente
    ? new Date(sessaoRecente).toLocaleDateString("pt-PT", { day: "2-digit", month: "long" })
    : null;

  const semDados = !squadStatus && kpis.length === 0 && alerts.length === 0;

  return (
    <div>
      <PageHeader titulo="Dashboard" subtitulo="O estado da equipa num relance" />

      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {semDados ? (
          <EstadoVazio />
        ) : (
          <>
            {/* ── Semáforo da equipa ─────────────────────────── */}
            {squadStatus && (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                  gap: espaco.md,
                  marginBottom: espaco.xxl,
                }}
              >
                <StatusBadge status="normal" count={squadStatus.normal} />
                <StatusBadge status="attention" count={squadStatus.attention} />
                <StatusBadge status="high-attention" count={squadStatus.highAttention} />
              </div>
            )}

            {/* ── Carga externa da equipa (protagonista) ─────── */}
            {kpis.length > 0 && (
              <div style={{ marginBottom: espaco.xxl }}>
                <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: espaco.md }}>
                  <SecaoTitulo>🛰️ Carga externa da equipa {dataLegivel && <span style={{ color: cores.textoSuave, fontWeight: 400 }}>· {dataLegivel}</span>}</SecaoTitulo>
                  <button onClick={() => router.push("/carga-externa")} style={linkBtn}>Ver detalhe →</button>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: espaco.md }}>
                  {kpis.map((k) => (
                    <KpiCargaCard key={k.chave} kpi={k} compacto />
                  ))}
                </div>
              </div>
            )}

            {/* ── Atenção requerida ──────────────────────────── */}
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: espaco.md }}>
              <SecaoTitulo>⚠️ Atenção requerida</SecaoTitulo>
              {alerts.length > 6 && <span style={{ fontSize: "0.75rem", color: cores.textoSuave }}>{alerts.length} atletas</span>}
            </div>
            {alerts.length === 0 ? (
              <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.lg, color: cores.textoSuave, fontSize: "0.9rem", marginBottom: espaco.xxl }}>
                🟢 Ninguém precisa de atenção especial neste momento.
              </div>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: espaco.md, marginBottom: espaco.xxl }}>
                {alerts.slice(0, 6).map((alert) => (
                  <div
                    key={alert.player_id}
                    onClick={() => router.push(`/jogadores?nome=${encodeURIComponent(alert.player_name)}`)}
                    style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md, cursor: "pointer" }}
                    onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.borderColor = cores.bordaForte)}
                    onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.borderColor = cores.borda)}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: espaco.sm }}>
                      <span style={{ fontSize: "0.95rem", fontWeight: 700, color: "white" }}>{alert.player_name}</span>
                      <StatusIndicator status={alert.status} size="sm" showLabel={false} />
                    </div>
                    <div style={{ fontSize: "0.82rem", fontWeight: 600, color: "white" }}>{alert.reason_text}</div>
                    <div style={{ fontSize: "0.8rem", color: cores.textoSuave, marginTop: 2 }}>{alert.metric_value}</div>
                    <div style={{ marginTop: espaco.md, paddingTop: espaco.sm, borderTop: `1px solid ${cores.borda}`, fontSize: "0.72rem", color: cores.destaque, fontWeight: 600 }}>
                      Ver perfil →
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* ── Ações rápidas ──────────────────────────────── */}
            <SecaoTitulo>Ações rápidas</SecaoTitulo>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: espaco.md }}>
              <AcaoBtn label="Importar GPS" cor={cores.sucesso} onClick={() => router.push("/sessoes/importar")} />
              <AcaoBtn label="Ver sessões" cor={cores.info} onClick={() => router.push("/sessoes/lista")} />
              <AcaoBtn label="Comparar jogadores" cor={cores.destaque} onClick={() => router.push("/analise/comparacao")} />
              <AcaoBtn label="Match benchmark" cor={cores.cargaInterna} onClick={() => router.push("/match-benchmark")} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

const linkBtn: React.CSSProperties = {
  background: "transparent",
  border: "none",
  color: cores.destaque,
  fontSize: "0.78rem",
  fontWeight: 600,
  cursor: "pointer",
};

function AcaoBtn({ label, cor, onClick }: { label: string; cor: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: `color-mix(in srgb, ${cor} 14%, transparent)`,
        border: `1px solid ${cor}`,
        borderRadius: raio.md,
        padding: `${espaco.md}px ${espaco.lg}px`,
        color: "white",
        fontSize: "0.9rem",
        fontWeight: 700,
        cursor: "pointer",
        transition: "opacity 0.15s",
      }}
      onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.opacity = "0.85")}
      onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.opacity = "1")}
    >
      {label}
    </button>
  );
}

function SecaoTitulo({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="font-display" style={{ fontSize: "1rem", fontWeight: 600, color: "white", margin: 0 }}>
      {children}
    </h2>
  );
}

function EstadoVazio() {
  const router = useRouter();
  return (
    <div style={{ maxWidth: 600, margin: "60px auto", padding: "0 24px", textAlign: "center" }}>
      <p style={{ color: cores.textoSuave, fontSize: "0.95rem", marginBottom: espaco.lg }}>
        Ainda não há dados carregados para esta equipa. Importa dados de GPS para veres o estado da equipa.
      </p>
      <button
        onClick={() => router.push("/sessoes/importar")}
        style={{ background: cores.sucesso, border: "none", borderRadius: raio.md, padding: `${espaco.md}px ${espaco.xl}px`, color: "white", fontWeight: 700, cursor: "pointer" }}
      >
        Importar GPS
      </button>
    </div>
  );
}
