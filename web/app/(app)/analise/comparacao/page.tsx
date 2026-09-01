"use client";

import { useState } from "react";
import { cores, espaco, raio } from "@/lib/theme";
import { PageHeader } from "@/components/layout/PageHeader";

interface ComparisonPlayer {
  id: string;
  name: string;
  position: string;
  number: number;
}

interface PlayerComparisonData {
  metric: string;
  unit: string;
  emoji: string;
  values: Record<string, number>;
  benchmark: number;
}

export default function PlayerComparisonPage() {
  const [selectedPlayers, setSelectedPlayers] = useState<ComparisonPlayer[]>([
    { id: "1", name: "João Silva", position: "CM", number: 7 },
  ]);

  const [allPlayers] = useState<ComparisonPlayer[]>([
    { id: "1", name: "João Silva", position: "CM", number: 7 },
    { id: "2", name: "Pedro Costa", position: "CB", number: 4 },
    { id: "3", name: "Miguel Santos", position: "LW", number: 11 },
    { id: "4", name: "Ana Martins", position: "GK", number: 1 },
    { id: "5", name: "Carlos Teixeira", position: "RB", number: 2 },
  ]);

  // TODO: Fetch actual comparison data from API
  const comparisonMetrics: PlayerComparisonData[] = [
    {
      metric: "Carga Semanal",
      unit: "au",
      emoji: "🏋️",
      values: { "1": 4200, "2": 3100, "3": 3850 },
      benchmark: 3500,
    },
    {
      metric: "Bem-estar",
      unit: "/20",
      emoji: "😊",
      values: { "1": 13, "2": 17, "3": 14 },
      benchmark: 15,
    },
    {
      metric: "ACWR",
      unit: "",
      emoji: "📊",
      values: { "1": 1.45, "2": 0.95, "3": 1.12 },
      benchmark: 1.2,
    },
    {
      metric: "Distância Média",
      unit: "km",
      emoji: "🏃",
      values: { "1": 8.2, "2": 6.5, "3": 7.8 },
      benchmark: 7.5,
    },
    {
      metric: "HSR Acumulada",
      unit: "m",
      emoji: "💨",
      values: { "1": 2100, "2": 1200, "3": 1850 },
      benchmark: 1500,
    },
  ];

  const addPlayer = (player: ComparisonPlayer) => {
    if (
      selectedPlayers.length < 4 &&
      !selectedPlayers.find((p) => p.id === player.id)
    ) {
      setSelectedPlayers([...selectedPlayers, player]);
    }
  };

  const removePlayer = (playerId: string) => {
    setSelectedPlayers(selectedPlayers.filter((p) => p.id !== playerId));
  };

  const getMetricColor = (value: number, benchmark: number) => {
    const ratio = value / benchmark;
    if (ratio > 1.2) return cores.cargaInterna;
    if (ratio < 0.8) return cores.atencao;
    return cores.sucesso;
  };

  return (
    <div style={{ padding: espaco.xl, maxWidth: 1400, margin: "0 auto" }}>
      <PageHeader
        titulo="Comparação de Jogadores"
        subtitulo="Compare até 4 jogadores lado a lado"
      />

      {/* Player Selection */}
      <div
        style={{
          background: cores.bgElevado,
          border: `1px solid ${cores.borda}`,
          borderRadius: raio.md,
          padding: espaco.lg,
          marginBottom: espaco.xl,
        }}
      >
        <h3
          style={{
            fontSize: "1rem",
            fontWeight: 700,
            color: "white",
            marginBottom: espaco.md,
          }}
        >
          Selecionar Jogadores
        </h3>

        <div style={{ marginBottom: espaco.lg }}>
          <div
            style={{
              display: "flex",
              gap: espaco.sm,
              flexWrap: "wrap",
            }}
          >
            {selectedPlayers.map((player) => (
              <div
                key={player.id}
                style={{
                  background: cores.cargaInterna,
                  color: "white",
                  padding: `${espaco.sm}px ${espaco.md}px`,
                  borderRadius: raio.sm,
                  display: "flex",
                  alignItems: "center",
                  gap: espaco.sm,
                  fontSize: "0.875rem",
                }}
              >
                <span>
                  #{player.number} {player.name}
                </span>
                <button
                  onClick={() => removePlayer(player.id)}
                  style={{
                    background: "none",
                    border: "none",
                    color: "white",
                    cursor: "pointer",
                    fontSize: "1.125rem",
                    padding: 0,
                  }}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>

        {selectedPlayers.length < 4 && (
          <div>
            <div
              style={{
                fontSize: "0.875rem",
                color: cores.textoSuave,
                marginBottom: espaco.sm,
              }}
            >
              Adicionar jogador:
            </div>
            <div
              style={{
                display: "flex",
                gap: espaco.sm,
                flexWrap: "wrap",
              }}
            >
              {allPlayers
                .filter(
                  (p) => !selectedPlayers.find((sp) => sp.id === p.id)
                )
                .map((player) => (
                  <button
                    key={player.id}
                    onClick={() => addPlayer(player)}
                    style={{
                      background: cores.bg,
                      color: cores.destaque,
                      padding: `${espaco.sm}px ${espaco.md}px`,
                      borderRadius: raio.sm,
                      border: `1px solid ${cores.destaque}`,
                      cursor: "pointer",
                      fontSize: "0.875rem",
                      fontWeight: 600,
                      transition: "all 0.2s",
                    }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLElement).style.background =
                        cores.destaque;
                      (e.currentTarget as HTMLElement).style.color = "white";
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLElement).style.background =
                        cores.bg;
                      (e.currentTarget as HTMLElement).style.color =
                        cores.destaque;
                    }}
                  >
                    + #{player.number} {player.name}
                  </button>
                ))}
            </div>
          </div>
        )}
      </div>

      {/* Comparison Table */}
      {selectedPlayers.length > 0 && (
        <div
          style={{
            background: cores.bgElevado,
            border: `1px solid ${cores.borda}`,
            borderRadius: raio.md,
            padding: espaco.lg,
          }}
        >
          <h3
            style={{
              fontSize: "1.125rem",
              fontWeight: 700,
              color: "white",
              marginBottom: espaco.lg,
            }}
          >
            Comparação de Métricas
          </h3>

          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: "0.875rem",
              }}
            >
              <thead>
                <tr style={{ borderBottom: `2px solid ${cores.borda}` }}>
                  <th
                    style={{
                      textAlign: "left",
                      padding: espaco.md,
                      color: cores.textoSuave,
                      fontWeight: 600,
                    }}
                  >
                    Métrica
                  </th>
                  <th
                    style={{
                      textAlign: "center",
                      padding: espaco.md,
                      color: cores.textoSuave,
                      fontWeight: 600,
                    }}
                  >
                    Benchmark
                  </th>
                  {selectedPlayers.map((player) => (
                    <th
                      key={player.id}
                      style={{
                        textAlign: "center",
                        padding: espaco.md,
                        color: cores.destaque,
                        fontWeight: 600,
                      }}
                    >
                      #{player.number}
                      <br />
                      <span style={{ fontSize: "0.75rem", color: cores.textoSuave }}>
                        {player.name}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {comparisonMetrics.map((metric) => (
                  <tr
                    key={metric.metric}
                    style={{ borderBottom: `1px solid ${cores.borda}` }}
                  >
                    <td
                      style={{
                        padding: espaco.md,
                        color: "white",
                        fontWeight: 600,
                      }}
                    >
                      {metric.emoji} {metric.metric}
                    </td>
                    <td
                      style={{
                        textAlign: "center",
                        padding: espaco.md,
                        color: cores.textoSuave,
                      }}
                    >
                      {metric.benchmark} {metric.unit}
                    </td>
                    {selectedPlayers.map((player) => {
                      const value = metric.values[player.id];
                      return (
                        <td
                          key={player.id}
                          style={{
                            textAlign: "center",
                            padding: espaco.md,
                            color: getMetricColor(value, metric.benchmark),
                            fontWeight: 700,
                          }}
                        >
                          {value} {metric.unit}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div
            style={{
              marginTop: espaco.lg,
              paddingTop: espaco.lg,
              borderTop: `1px solid ${cores.borda}`,
              fontSize: "0.75rem",
              color: cores.textoSuave,
            }}
          >
            <span style={{ color: cores.sucesso }}>●</span> Normal{" "}
            <span style={{ marginLeft: espaco.lg, color: cores.atencao }}>
              ●
            </span>{" "}
            Abaixo de Benchmark{" "}
            <span style={{ marginLeft: espaco.lg, color: cores.cargaInterna }}>
              ●
            </span>{" "}
            Acima do Benchmark
          </div>
        </div>
      )}
    </div>
  );
}
