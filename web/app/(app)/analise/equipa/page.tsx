"use client";

import { useState, useEffect } from "react";
import { cores, espaco, raio } from "@/lib/theme";
import { PageHeader } from "@/components/layout/PageHeader";

interface TeamMetric {
  week: string;
  totalLoad: number;
  averageWellness: number;
  injuryRisk: "low" | "medium" | "high";
  players: number;
  sessionsCount: number;
}

export default function TeamAnalysisPage() {
  const [metrics, setMetrics] = useState<TeamMetric[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // TODO: Fetch from /api/teams/{team_id}/analise endpoint
    // Simulating data for now
    setMetrics([
      {
        week: "W35",
        totalLoad: 45200,
        averageWellness: 16.2,
        injuryRisk: "low",
        players: 23,
        sessionsCount: 4,
      },
      {
        week: "W36",
        totalLoad: 52100,
        averageWellness: 14.8,
        injuryRisk: "medium",
        players: 23,
        sessionsCount: 5,
      },
      {
        week: "W37",
        totalLoad: 48600,
        averageWellness: 15.5,
        injuryRisk: "low",
        players: 22,
        sessionsCount: 4,
      },
    ]);
    setLoading(false);
  }, []);

  const riskColor = {
    low: cores.sucesso,
    medium: cores.atencao,
    high: cores.cargaInterna,
  };

  return (
    <div style={{ padding: espaco.xl, maxWidth: 1400, margin: "0 auto" }}>
      <PageHeader
        titulo="Análise de Equipa"
        subtitulo="Tendências semanais, distribuição de carga e padrões"
      />

      {/* Summary Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
          gap: espaco.lg,
          marginBottom: espaco.xl,
        }}
      >
        {[
          { label: "Carga Média", value: "50.2K", emoji: "🏋️" },
          { label: "Bem-estar Médio", value: "15.5/20", emoji: "😊" },
          { label: "Risco de Lesão", value: "Baixo", emoji: "✅" },
          { label: "Sessões Semana", value: "4.3", emoji: "📅" },
        ].map((card, idx) => (
          <div
            key={idx}
            style={{
              background: cores.bgElevado,
              border: `1px solid ${cores.borda}`,
              borderRadius: raio.md,
              padding: espaco.lg,
            }}
          >
            <div
              style={{
                fontSize: "0.875rem",
                color: cores.textoSuave,
                marginBottom: espaco.sm,
              }}
            >
              {card.emoji} {card.label}
            </div>
            <div
              style={{
                fontSize: "2rem",
                fontWeight: 700,
                color: "white",
              }}
            >
              {card.value}
            </div>
          </div>
        ))}
      </div>

      {/* Weekly Trends Table */}
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
            fontSize: "1.125rem",
            fontWeight: 700,
            color: "white",
            marginBottom: espaco.lg,
          }}
        >
          Tendências Semanais
        </h3>

        {loading ? (
          <div style={{ color: cores.textoSuave }}>Carregando...</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: "0.875rem",
              }}
            >
              <thead>
                <tr style={{ borderBottom: `1px solid ${cores.borda}` }}>
                  <th
                    style={{
                      textAlign: "left",
                      padding: espaco.md,
                      color: cores.textoSuave,
                      fontWeight: 600,
                    }}
                  >
                    Semana
                  </th>
                  <th
                    style={{
                      textAlign: "right",
                      padding: espaco.md,
                      color: cores.textoSuave,
                      fontWeight: 600,
                    }}
                  >
                    Carga Total
                  </th>
                  <th
                    style={{
                      textAlign: "center",
                      padding: espaco.md,
                      color: cores.textoSuave,
                      fontWeight: 600,
                    }}
                  >
                    Bem-estar
                  </th>
                  <th
                    style={{
                      textAlign: "center",
                      padding: espaco.md,
                      color: cores.textoSuave,
                      fontWeight: 600,
                    }}
                  >
                    Risco
                  </th>
                  <th
                    style={{
                      textAlign: "right",
                      padding: espaco.md,
                      color: cores.textoSuave,
                      fontWeight: 600,
                    }}
                  >
                    Sessões
                  </th>
                </tr>
              </thead>
              <tbody>
                {metrics.map((metric) => (
                  <tr
                    key={metric.week}
                    style={{ borderBottom: `1px solid ${cores.borda}` }}
                  >
                    <td style={{ padding: espaco.md, color: "white" }}>
                      <strong>{metric.week}</strong>
                    </td>
                    <td
                      style={{
                        textAlign: "right",
                        padding: espaco.md,
                        color: "white",
                      }}
                    >
                      {metric.totalLoad.toLocaleString("pt-PT")}
                    </td>
                    <td style={{ textAlign: "center", padding: espaco.md }}>
                      <div
                        style={{
                          display: "inline-block",
                          background: cores.bg,
                          padding: `${espaco.xs}px ${espaco.sm}px`,
                          borderRadius: raio.sm,
                          color: "white",
                        }}
                      >
                        {metric.averageWellness}/20
                      </div>
                    </td>
                    <td style={{ textAlign: "center", padding: espaco.md }}>
                      <span
                        style={{
                          display: "inline-block",
                          width: 12,
                          height: 12,
                          borderRadius: "50%",
                          background: riskColor[metric.injuryRisk],
                        }}
                      />
                    </td>
                    <td
                      style={{
                        textAlign: "right",
                        padding: espaco.md,
                        color: "white",
                      }}
                    >
                      {metric.sessionsCount}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Load Distribution */}
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
          Distribuição de Carga
        </h3>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: espaco.lg,
          }}
        >
          {["Muito Alta", "Alta", "Moderada", "Baixa"].map((level, idx) => (
            <div key={idx}>
              <div
                style={{
                  fontSize: "0.875rem",
                  color: cores.textoSuave,
                  marginBottom: espaco.sm,
                }}
              >
                {level}
              </div>
              <div
                style={{
                  background: cores.bg,
                  borderRadius: raio.sm,
                  padding: espaco.lg,
                  textAlign: "center",
                }}
              >
                <div
                  style={{
                    fontSize: "2rem",
                    fontWeight: 700,
                    color: "white",
                  }}
                >
                  {[23, 18, 12, 8][idx]}
                </div>
                <div style={{ fontSize: "0.75rem", color: cores.textoSuave }}>
                  jogadores
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
