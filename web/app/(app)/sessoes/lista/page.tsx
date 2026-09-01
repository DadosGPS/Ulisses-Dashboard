"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { cores, espaco, raio } from "@/lib/theme";
import { PageHeader } from "@/components/layout/PageHeader";

interface Session {
  id: string;
  date: string;
  type: string;
  participants: number;
  duration: number;
  totalLoad: number;
  averageWellness: number;
  status: "completed" | "pending" | "error";
}

type FilterType = "all" | "jogo" | "treino" | "recuperacao";

export default function SessionsListPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<FilterType>("all");
  const [dateRange, setDateRange] = useState<"week" | "month" | "all">("week");

  useEffect(() => {
    // TODO: Fetch from /api/teams/{team_id}/sessions endpoint
    setSessions([
      {
        id: "1",
        date: "01 Set 2026",
        type: "Jogo",
        participants: 23,
        duration: 90,
        totalLoad: 73600,
        averageWellness: 13.2,
        status: "completed",
      },
      {
        id: "2",
        date: "31 Ago 2026",
        type: "Treino Técnico",
        participants: 22,
        duration: 75,
        totalLoad: 46200,
        averageWellness: 15.1,
        status: "completed",
      },
      {
        id: "3",
        date: "30 Ago 2026",
        type: "Recuperação",
        participants: 20,
        duration: 45,
        totalLoad: 16800,
        averageWellness: 16.8,
        status: "completed",
      },
      {
        id: "4",
        date: "29 Ago 2026",
        type: "Jogo Preparação",
        participants: 23,
        duration: 90,
        totalLoad: 68400,
        averageWellness: 12.9,
        status: "completed",
      },
      {
        id: "5",
        date: "28 Ago 2026",
        type: "Treino Força",
        participants: 21,
        duration: 60,
        totalLoad: 38500,
        averageWellness: 14.3,
        status: "completed",
      },
    ]);
    setLoading(false);
  }, []);

  const filteredSessions = sessions.filter((s) => {
    if (filter === "jogo")
      return s.type.includes("Jogo");
    if (filter === "treino")
      return s.type.includes("Treino");
    if (filter === "recuperacao")
      return s.type.includes("Recuperação");
    return true;
  });

  const sessionTypeColor = (type: string) => {
    if (type.includes("Jogo")) return cores.cargaInterna;
    if (type.includes("Recuperação")) return cores.sucesso;
    return cores.destaque;
  };

  const wellnessColor = (wellness: number) => {
    if (wellness >= 16) return cores.sucesso;
    if (wellness >= 14) return "white";
    return cores.atencao;
  };

  return (
    <div style={{ padding: espaco.xl, maxWidth: 1400, margin: "0 auto" }}>
      <PageHeader
        titulo="Sessões"
        subtitulo={`${filteredSessions.length} sessão${filteredSessions.length !== 1 ? "s" : ""}`}
      />

      {/* Filters */}
      <div
        style={{
          display: "flex",
          gap: espaco.lg,
          marginBottom: espaco.xl,
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", gap: espaco.sm, flexWrap: "wrap" }}>
          <button
            onClick={() => setFilter("all")}
            style={{
              padding: `${espaco.sm}px ${espaco.lg}px`,
              borderRadius: raio.sm,
              background:
                filter === "all" ? cores.cargaInterna : cores.bgElevado,
              color: filter === "all" ? "white" : cores.textoSuave,
              border: `1px solid ${
                filter === "all" ? cores.cargaInterna : cores.borda
              }`,
              cursor: "pointer",
              fontWeight: 600,
              fontSize: "0.875rem",
              transition: "all 0.2s",
            }}
          >
            Todos
          </button>
          <button
            onClick={() => setFilter("jogo")}
            style={{
              padding: `${espaco.sm}px ${espaco.lg}px`,
              borderRadius: raio.sm,
              background:
                filter === "jogo" ? cores.cargaInterna : cores.bgElevado,
              color: filter === "jogo" ? "white" : cores.textoSuave,
              border: `1px solid ${
                filter === "jogo" ? cores.cargaInterna : cores.borda
              }`,
              cursor: "pointer",
              fontWeight: 600,
              fontSize: "0.875rem",
              transition: "all 0.2s",
            }}
          >
            Jogos
          </button>
          <button
            onClick={() => setFilter("treino")}
            style={{
              padding: `${espaco.sm}px ${espaco.lg}px`,
              borderRadius: raio.sm,
              background:
                filter === "treino" ? cores.destaque : cores.bgElevado,
              color: filter === "treino" ? "white" : cores.textoSuave,
              border: `1px solid ${
                filter === "treino" ? cores.destaque : cores.borda
              }`,
              cursor: "pointer",
              fontWeight: 600,
              fontSize: "0.875rem",
              transition: "all 0.2s",
            }}
          >
            Treinos
          </button>
          <button
            onClick={() => setFilter("recuperacao")}
            style={{
              padding: `${espaco.sm}px ${espaco.lg}px`,
              borderRadius: raio.sm,
              background:
                filter === "recuperacao" ? cores.sucesso : cores.bgElevado,
              color: filter === "recuperacao" ? "white" : cores.textoSuave,
              border: `1px solid ${
                filter === "recuperacao" ? cores.sucesso : cores.borda
              }`,
              cursor: "pointer",
              fontWeight: 600,
              fontSize: "0.875rem",
              transition: "all 0.2s",
            }}
          >
            Recuperação
          </button>
        </div>
      </div>

      {/* Sessions List */}
      {loading ? (
        <div style={{ textAlign: "center", color: cores.textoSuave, padding: espaco.xl }}>
          Carregando sessões...
        </div>
      ) : filteredSessions.length === 0 ? (
        <div
          style={{
            background: cores.bgElevado,
            border: `1px solid ${cores.borda}`,
            borderRadius: raio.md,
            padding: espaco.xl,
            textAlign: "center",
            color: cores.textoSuave,
          }}
        >
          Nenhuma sessão encontrada
        </div>
      ) : (
        <div style={{ display: "grid", gap: espaco.lg }}>
          {filteredSessions.map((session) => (
            <div
              key={session.id}
              onClick={() => router.push(`/sessoes/${session.id}`)}
              style={{
                background: cores.bgElevado,
                border: `1px solid ${cores.borda}`,
                borderRadius: raio.md,
                padding: espaco.lg,
                cursor: "pointer",
                transition: "all 0.2s",
                display: "grid",
                gridTemplateColumns: "1fr 1fr 1fr 1fr 1fr auto",
                gap: espaco.lg,
                alignItems: "center",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.background = cores.bg;
                (e.currentTarget as HTMLElement).style.borderColor =
                  cores.destaque;
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.background =
                  cores.bgElevado;
                (e.currentTarget as HTMLElement).style.borderColor =
                  cores.borda;
              }}
            >
              {/* Date & Type */}
              <div>
                <div
                  style={{
                    fontSize: "0.75rem",
                    color: cores.textoSuave,
                    marginBottom: espaco.xs,
                  }}
                >
                  Data
                </div>
                <div
                  style={{
                    fontSize: "1rem",
                    fontWeight: 700,
                    color: "white",
                }}
                >
                  {session.date}
                </div>
                <div
                  style={{
                    fontSize: "0.875rem",
                    color: sessionTypeColor(session.type),
                    fontWeight: 600,
                    marginTop: espaco.xs,
                  }}
                >
                  {session.type}
                </div>
              </div>

              {/* Participants & Duration */}
              <div>
                <div
                  style={{
                    fontSize: "0.75rem",
                    color: cores.textoSuave,
                    marginBottom: espaco.xs,
                  }}
                >
                  Participants
                </div>
                <div
                  style={{
                    fontSize: "1.25rem",
                    fontWeight: 700,
                    color: "white",
                }}
                >
                  {session.participants}
                </div>
                <div
                  style={{
                    fontSize: "0.75rem",
                    color: cores.textoSuave,
                    marginTop: espaco.xs,
                  }}
                >
                  {session.duration} min
                </div>
              </div>

              {/* Total Load */}
              <div>
                <div
                  style={{
                    fontSize: "0.75rem",
                    color: cores.textoSuave,
                    marginBottom: espaco.xs,
                  }}
                >
                  Carga Total
                </div>
                <div
                  style={{
                    fontSize: "1.5rem",
                    fontWeight: 700,
                    color: cores.cargaInterna,
                }}
                >
                  {(session.totalLoad / 1000).toFixed(1)}K
                </div>
              </div>

              {/* Average Wellness */}
              <div>
                <div
                  style={{
                    fontSize: "0.75rem",
                    color: cores.textoSuave,
                    marginBottom: espaco.xs,
                  }}
                >
                  Bem-estar Médio
                </div>
                <div
                  style={{
                    fontSize: "1.5rem",
                    fontWeight: 700,
                    color: wellnessColor(session.averageWellness),
                  }}
                >
                  {session.averageWellness}/20
                </div>
              </div>

              {/* Status Indicator */}
              <div>
                <div
                  style={{
                    fontSize: "0.75rem",
                    color: cores.textoSuave,
                    marginBottom: espaco.xs,
                  }}
                >
                  Status
                </div>
                <div
                  style={{
                    display: "inline-block",
                    width: 12,
                    height: 12,
                    borderRadius: "50%",
                    background:
                      session.status === "completed"
                        ? cores.sucesso
                        : session.status === "pending"
                        ? cores.atencao
                        : cores.cargaInterna,
                  }}
                />
              </div>

              {/* Arrow */}
              <div
                style={{
                  fontSize: "1.25rem",
                  color: cores.destaque,
                  opacity: 0.5,
                }}
              >
                →
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Quick Actions */}
      <div
        style={{
          marginTop: espaco.xxl,
          display: "flex",
          gap: espaco.lg,
          justifyContent: "center",
          flexWrap: "wrap",
        }}
      >
        <button
          onClick={() => router.push("/sessoes/nova")}
          style={{
            padding: `${espaco.md}px ${espaco.xl}px`,
            borderRadius: raio.md,
            background: cores.destaque,
            color: "white",
            border: "none",
            cursor: "pointer",
            fontWeight: 600,
            fontSize: "1rem",
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
            padding: `${espaco.md}px ${espaco.xl}px`,
            borderRadius: raio.md,
            background: cores.bgElevado,
            color: cores.destaque,
            border: `1px solid ${cores.destaque}`,
            cursor: "pointer",
            fontWeight: 600,
            fontSize: "1rem",
            transition: "all 0.2s",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLElement).style.background =
              cores.destaque;
            (e.currentTarget as HTMLElement).style.color = "white";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLElement).style.background =
              cores.bgElevado;
            (e.currentTarget as HTMLElement).style.color = cores.destaque;
          }}
        >
          📥 Importar GPS
        </button>
      </div>
    </div>
  );
}
