"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useStore } from "@/lib/store";
import { cores, espaco, raio } from "@/lib/theme";
import { StatusBadge, StatusIndicator } from "@/components/ui/StatusIndicator";
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

interface WhatChanged {
  metric: string;
  previous: number;
  current: number;
  change_percent: number;
  direction: "up" | "down";
}

interface TodaySession {
  exists: boolean;
  session_id?: string;
  date?: string;
  type?: string;
  match_day?: string;
  duration_minutes?: number;
  participants?: number;
  team_load?: {
    total_distance: number;
    hsr: number;
    sprint: number;
    accelerations: number;
    decelerations: number;
    sRPE: number;
  };
}

export default function DashboardPage() {
  const router = useRouter();
  const { user } = useStore();
  const [loading, setLoading] = useState(true);
  const [squadStatus, setSquadStatus] = useState<SquadStatus | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [whatChanged, setWhatChanged] = useState<WhatChanged[]>([]);
  const [todaySession, setTodaySession] = useState<TodaySession | null>(null);

  useEffect(() => {
    if (!user.teamId) {
      router.push("/login");
      return;
    }

    fetchDashboardData();
  }, [user.teamId]);

  async function fetchDashboardData() {
    try {
      setLoading(true);
      const teamId = user.teamId;

      // Fetch squad status
      const statusRes = await fetch(
        `/api/teams/${teamId}/dashboard/squad-status`
      );
      if (statusRes.ok) {
        setSquadStatus(await statusRes.json());
      }

      // Fetch attention required
      const alertsRes = await fetch(
        `/api/teams/${teamId}/dashboard/attention-required`
      );
      if (alertsRes.ok) {
        setAlerts(await alertsRes.json());
      }

      // Fetch what changed
      const changedRes = await fetch(
        `/api/teams/${teamId}/dashboard/what-changed`
      );
      if (changedRes.ok) {
        setWhatChanged(await changedRes.json());
      }

      // Fetch today's session
      const sessionRes = await fetch(
        `/api/teams/${teamId}/dashboard/today-session`
      );
      if (sessionRes.ok) {
        setTodaySession(await sessionRes.json());
      }
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div
        style={{
          padding: espaco.xl,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "100vh",
          color: cores.textoSuave,
        }}
      >
        Carregando dashboard...
      </div>
    );
  }

  return (
    <div style={{ padding: espaco.xl, maxWidth: 1400, margin: "0 auto" }}>
      <PageHeader
        titulo="Dashboard"
        subtitulo="Visão geral do esquadrão"
      />

      {/* Squad Status Cards */}
      {squadStatus && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: espaco.lg,
            marginBottom: espaco.xl,
          }}
        >
          <StatusBadge
            status="normal"
            count={squadStatus.normal}
            onClick={() => {
              // Filter view by status
            }}
          />
          <StatusBadge
            status="attention"
            count={squadStatus.attention}
            onClick={() => {
              // Filter view by status
            }}
          />
          <StatusBadge
            status="high-attention"
            count={squadStatus.highAttention}
            onClick={() => {
              // Filter view by status
            }}
          />
        </div>
      )}

      {/* Attention Required Section */}
      {alerts.length > 0 && (
        <div
          style={{
            background: cores.bgElevado,
            border: `1px solid ${cores.borda}`,
            borderRadius: raio.md,
            padding: espaco.lg,
            marginBottom: espaco.xl,
          }}
        >
          <h2
            style={{
              fontSize: "1rem",
              fontWeight: 700,
              marginBottom: espaco.lg,
              color: "white",
            }}
          >
            ⚠️ Atenção Requerida
          </h2>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
              gap: espaco.md,
            }}
          >
            {alerts.slice(0, 6).map((alert) => (
              <div
                key={alert.player_id}
                style={{
                  background: cores.bg,
                  border: `1px solid ${cores.borda}`,
                  borderRadius: raio.sm,
                  padding: espaco.md,
                  cursor: "pointer",
                  transition: "all 0.2s",
                }}
                onClick={() => router.push(`/jogadores/${alert.player_id}`)}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLElement).style.background =
                    cores.bgElevado;
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.background = cores.bg;
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "start",
                    marginBottom: espaco.sm,
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontSize: "1rem",
                        fontWeight: 700,
                        color: "white",
                        marginBottom: espaco.xs,
                      }}
                    >
                      {alert.player_name}
                    </div>
                  </div>
                  <StatusIndicator
                    status={alert.status}
                    size="sm"
                    showLabel={false}
                  />
                </div>

                <div style={{ fontSize: "0.875rem", color: cores.textoSuave }}>
                  <div style={{ fontWeight: 600, color: "white" }}>
                    {alert.reason_text}
                  </div>
                  <div style={{ marginTop: espaco.xs }}>
                    {alert.metric_value}
                  </div>
                </div>

                <div
                  style={{
                    marginTop: espaco.md,
                    paddingTop: espaco.md,
                    borderTop: `1px solid ${cores.borda}`,
                    fontSize: "0.75rem",
                    color: cores.destaque,
                    fontWeight: 600,
                  }}
                >
                  Ver Perfil →
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* What Changed Section */}
      {whatChanged && whatChanged.length > 0 && (
        <div
          style={{
            background: cores.bgElevado,
            border: `1px solid ${cores.borda}`,
            borderRadius: raio.md,
            padding: espaco.lg,
            marginBottom: espaco.xl,
          }}
        >
          <h2
            style={{
              fontSize: "1rem",
              fontWeight: 700,
              marginBottom: espaco.lg,
              color: "white",
            }}
          >
            O Que Mudou?
          </h2>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: espaco.md,
            }}
          >
            {whatChanged.map((item, idx) => (
              <div
                key={idx}
                style={{
                  background: cores.bg,
                  border: `1px solid ${cores.borda}`,
                  borderRadius: raio.sm,
                  padding: espaco.md,
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                }}
              >
                <div
                  style={{
                    fontSize: "0.875rem",
                    color: cores.textoSuave,
                    marginBottom: espaco.sm,
                  }}
                >
                  {item.metric}
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "baseline",
                    gap: espaco.sm,
                  }}
                >
                  <span
                    style={{
                      fontSize: "1.5rem",
                      fontWeight: 700,
                      color:
                        item.direction === "up"
                          ? cores.cargaInterna
                          : cores.sucesso,
                    }}
                  >
                    {item.direction === "up" ? "↑" : "↓"}
                    {Math.abs(item.change_percent).toFixed(1)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Today's Session Section */}
      {todaySession?.exists && (
        <div
          style={{
            background: cores.bgElevado,
            border: `1px solid ${cores.borda}`,
            borderRadius: raio.md,
            padding: espaco.lg,
            marginBottom: espaco.xl,
          }}
        >
          <h2
            style={{
              fontSize: "1rem",
              fontWeight: 700,
              marginBottom: espaco.lg,
              color: "white",
            }}
          >
            Sessão de Hoje
          </h2>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: espaco.lg,
              marginBottom: espaco.lg,
            }}
          >
            <div>
              <div style={{ fontSize: "0.875rem", color: cores.textoSuave }}>
                Tipo de Sessão
              </div>
              <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "white" }}>
                {todaySession.type} — {todaySession.match_day}
              </div>
            </div>
            <div>
              <div style={{ fontSize: "0.875rem", color: cores.textoSuave }}>
                Duração
              </div>
              <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "white" }}>
                {todaySession.duration_minutes} min • {todaySession.participants} jogadores
              </div>
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
              gap: espaco.md,
            }}
          >
            {todaySession.team_load && Object.entries(todaySession.team_load).map(
              ([key, value]) => (
                <div
                  key={key}
                  style={{
                    background: cores.bg,
                    border: `1px solid ${cores.borda}`,
                    borderRadius: raio.sm,
                    padding: espaco.md,
                    textAlign: "center",
                  }}
                >
                  <div style={{ fontSize: "0.75rem", color: cores.textoSuave }}>
                    {key.toUpperCase()}
                  </div>
                  <div
                    style={{
                      fontSize: "1.25rem",
                      fontWeight: 700,
                      color: "white",
                      marginTop: espaco.xs,
                    }}
                  >
                    {typeof value === "number"
                      ? value.toLocaleString("pt-PT", {
                          maximumFractionDigits: 1,
                        })
                      : value}
                  </div>
                </div>
              )
            )}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
          gap: espaco.lg,
        }}
      >
        <button
          onClick={() => router.push("/sessoes/nova")}
          style={{
            background: cores.cargaInterna,
            border: "none",
            borderRadius: raio.md,
            padding: `${espaco.lg}px ${espaco.xl}px`,
            color: "white",
            fontSize: "1rem",
            fontWeight: 700,
            cursor: "pointer",
            transition: "all 0.2s",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLElement).style.opacity = "0.9";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLElement).style.opacity = "1";
          }}
        >
          + Adicionar Sessão
        </button>
        <button
          onClick={() => router.push("/sessoes/importar")}
          style={{
            background: cores.sucesso,
            border: "none",
            borderRadius: raio.md,
            padding: `${espaco.lg}px ${espaco.xl}px`,
            color: "white",
            fontSize: "1rem",
            fontWeight: 700,
            cursor: "pointer",
            transition: "all 0.2s",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLElement).style.opacity = "0.9";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLElement).style.opacity = "1";
          }}
        >
          Importar GPS
        </button>
        <button
          onClick={() => router.push("/jogadores")}
          style={{
            background: cores.atencao,
            border: "none",
            borderRadius: raio.md,
            padding: `${espaco.lg}px ${espaco.xl}px`,
            color: "white",
            fontSize: "1rem",
            fontWeight: 700,
            cursor: "pointer",
            transition: "all 0.2s",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLElement).style.opacity = "0.9";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLElement).style.opacity = "1";
          }}
        >
          Ver Jogadores
        </button>
      </div>
    </div>
  );
}
