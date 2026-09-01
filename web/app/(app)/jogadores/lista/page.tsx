"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { cores, espaco, raio } from "@/lib/theme";
import { PageHeader } from "@/components/layout/PageHeader";
import { StatusIndicator } from "@/components/ui/StatusIndicator";

interface Player {
  id: string;
  name: string;
  position: string;
  number?: number;
  status: "normal" | "attention" | "high-attention";
  availabilityState: "apto" | "lesionado" | "em_recuperacao" | "ausente";
  load?: number;
  wellness?: number;
}

export default function PlayersListPage() {
  const router = useRouter();
  const [players, setPlayers] = useState<Player[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "apto" | "indisponivel">("all");

  useEffect(() => {
    // TODO: Fetch actual players from API
    // For now, use mock data
    setPlayers([
      {
        id: "1",
        name: "João Silva",
        position: "CM",
        number: 7,
        status: "high-attention",
        availabilityState: "apto",
        load: 4200,
        wellness: 13,
      },
      {
        id: "2",
        name: "Pedro Costa",
        position: "CB",
        number: 4,
        status: "normal",
        availabilityState: "apto",
        load: 3100,
        wellness: 17,
      },
      {
        id: "3",
        name: "Miguel Santos",
        position: "LW",
        number: 11,
        status: "attention",
        availabilityState: "apto",
        load: 3850,
        wellness: 14,
      },
      {
        id: "4",
        name: "Ana Martins",
        position: "GK",
        number: 1,
        status: "normal",
        availabilityState: "lesionado",
        load: 0,
        wellness: 0,
      },
    ]);
    setLoading(false);
  }, []);

  const filteredPlayers = players.filter((p) => {
    if (filter === "apto") return p.availabilityState === "apto";
    if (filter === "indisponivel")
      return p.availabilityState !== "apto";
    return true;
  });

  const availabilityLabel = {
    apto: "✅ Disponível",
    lesionado: "🤕 Lesionado",
    em_recuperacao: "⚕️ Recuperação",
    ausente: "❌ Ausente",
  };

  return (
    <div style={{ padding: espaco.xl, maxWidth: 1400, margin: "0 auto" }}>
      <PageHeader
        titulo="Jogadores"
        subtitulo={`${filteredPlayers.length} jogador${filteredPlayers.length !== 1 ? "es" : ""} disponível${filteredPlayers.length !== 1 ? "eis" : ""}`}
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
        {(["all", "apto", "indisponivel"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: `${espaco.sm}px ${espaco.lg}px`,
              borderRadius: raio.sm,
              background:
                filter === f
                  ? cores.cargaInterna
                  : cores.bgElevado,
              color: filter === f ? "white" : cores.textoSuave,
              border: `1px solid ${
                filter === f ? cores.cargaInterna : cores.borda
              }`,
              cursor: "pointer",
              fontWeight: 600,
              fontSize: "0.875rem",
              transition: "all 0.2s",
            }}
          >
            {f === "all" && "Todos"}
            {f === "apto" && "Disponíveis"}
            {f === "indisponivel" && "Indisponíveis"}
          </button>
        ))}
      </div>

      {/* Players Grid */}
      {loading ? (
        <div style={{ textAlign: "center", color: cores.textoSuave, padding: espaco.xl }}>
          Carregando jogadores...
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
            gap: espaco.lg,
          }}
        >
          {filteredPlayers.map((player) => (
            <div
              key={player.id}
              onClick={() => router.push(`/jogadores/${player.id}`)}
              style={{
                background: cores.bgElevado,
                border: `1px solid ${cores.borda}`,
                borderRadius: raio.md,
                padding: espaco.lg,
                cursor: "pointer",
                transition: "all 0.2s",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.background =
                  cores.bg;
                (e.currentTarget as HTMLElement).style.borderColor =
                  cores.cargaInterna;
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.background =
                  cores.bgElevado;
                (e.currentTarget as HTMLElement).style.borderColor =
                  cores.borda;
              }}
            >
              {/* Header */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "start",
                  marginBottom: espaco.md,
                }}
              >
                <div>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "baseline",
                      gap: espaco.sm,
                      marginBottom: espaco.xs,
                    }}
                  >
                    {player.number && (
                      <span
                        style={{
                          fontSize: "1.5rem",
                          fontWeight: 700,
                          color: cores.destaque,
                        }}
                      >
                        #{player.number}
                      </span>
                    )}
                    <h3
                      style={{
                        fontSize: "1rem",
                        fontWeight: 700,
                        color: "white",
                      }}
                    >
                      {player.name}
                    </h3>
                  </div>
                  <div
                    style={{
                      fontSize: "0.875rem",
                      color: cores.textoSuave,
                    }}
                  >
                    {player.position}
                  </div>
                </div>
                <StatusIndicator
                  status={player.status}
                  size="sm"
                  showLabel={false}
                  compact
                />
              </div>

              {/* Availability */}
              <div
                style={{
                  background: cores.bg,
                  borderRadius: raio.sm,
                  padding: espaco.sm,
                  marginBottom: espaco.md,
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  color: cores.textoSuave,
                  textAlign: "center",
                }}
              >
                {availabilityLabel[player.availabilityState]}
              </div>

              {/* Metrics */}
              {player.availabilityState === "apto" && (
                <>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr",
                      gap: espaco.sm,
                      marginBottom: espaco.md,
                    }}
                  >
                    <div>
                      <div
                        style={{
                          fontSize: "0.75rem",
                          color: cores.textoSuave,
                          marginBottom: espaco.xs,
                        }}
                      >
                        Carga Semana
                      </div>
                      <div
                        style={{
                          fontSize: "1.125rem",
                          fontWeight: 700,
                          color: "white",
                        }}
                      >
                        {player.load?.toLocaleString("pt-PT") || "—"}
                      </div>
                    </div>
                    <div>
                      <div
                        style={{
                          fontSize: "0.75rem",
                          color: cores.textoSuave,
                          marginBottom: espaco.xs,
                        }}
                      >
                        Bem-estar
                      </div>
                      <div
                        style={{
                          fontSize: "1.125rem",
                          fontWeight: 700,
                          color:
                            player.wellness && player.wellness >= 15
                              ? cores.sucesso
                              : player.wellness && player.wellness < 12
                              ? cores.cargaInterna
                              : "white",
                        }}
                      >
                        {player.wellness}/20
                      </div>
                    </div>
                  </div>
                </>
              )}

              {/* Action */}
              <div
                style={{
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
      )}
    </div>
  );
}
