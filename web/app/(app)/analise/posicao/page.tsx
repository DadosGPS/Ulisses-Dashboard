"use client";

import { useState } from "react";
import { cores, espaco, raio } from "@/lib/theme";
import { PageHeader } from "@/components/layout/PageHeader";

interface PositionStats {
  position: string;
  count: number;
  avgLoad: number;
  avgWellness: number;
  avgDistance: number;
  injuryRate: number;
}

export default function PositionAnalysisPage() {
  const [selectedPosition, setSelectedPosition] = useState<string | null>(null);

  // TODO: Fetch from API endpoint for position analysis
  const positionStats: PositionStats[] = [
    {
      position: "GK",
      count: 2,
      avgLoad: 2100,
      avgWellness: 16.2,
      avgDistance: 3.2,
      injuryRate: 5,
    },
    {
      position: "CB",
      count: 4,
      avgLoad: 3850,
      avgWellness: 15.1,
      avgDistance: 6.8,
      injuryRate: 8,
    },
    {
      position: "LB/RB",
      count: 4,
      avgLoad: 4200,
      avgWellness: 14.8,
      avgDistance: 8.5,
      injuryRate: 12,
    },
    {
      position: "CM",
      count: 4,
      avgLoad: 4600,
      avgWellness: 14.2,
      avgDistance: 9.2,
      injuryRate: 15,
    },
    {
      position: "LW/RW",
      count: 4,
      avgLoad: 4400,
      avgWellness: 13.9,
      avgDistance: 9.0,
      injuryRate: 18,
    },
    {
      position: "ST",
      count: 1,
      avgLoad: 4100,
      avgWellness: 14.5,
      avgDistance: 8.3,
      injuryRate: 10,
    },
  ];

  return (
    <div style={{ padding: espaco.xl, maxWidth: 1400, margin: "0 auto" }}>
      <PageHeader
        titulo="Análise por Posição"
        subtitulo="Tendências e benchmarks por posição táctica"
      />

      {/* Position Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: espaco.lg,
          marginBottom: espaco.xl,
        }}
      >
        {positionStats.map((pos) => (
          <div
            key={pos.position}
            onClick={() =>
              setSelectedPosition(
                selectedPosition === pos.position ? null : pos.position
              )
            }
            style={{
              background: cores.bgElevado,
              border:
                selectedPosition === pos.position
                  ? `2px solid ${cores.destaque}`
                  : `1px solid ${cores.borda}`,
              borderRadius: raio.md,
              padding: espaco.lg,
              cursor: "pointer",
              transition: "all 0.2s",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.background = cores.bg;
              (e.currentTarget as HTMLElement).style.borderColor =
                cores.destaque;
            }}
            onMouseLeave={(e) => {
              if (selectedPosition !== pos.position) {
                (e.currentTarget as HTMLElement).style.background =
                  cores.bgElevado;
                (e.currentTarget as HTMLElement).style.borderColor =
                  cores.borda;
              }
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
              <h3
                style={{
                  fontSize: "1.25rem",
                  fontWeight: 700,
                  color: "white",
                }}
              >
                {pos.position}
              </h3>
              <div
                style={{
                  background: cores.cargaInterna,
                  color: "white",
                  padding: `${espaco.xs}px ${espaco.sm}px`,
                  borderRadius: raio.sm,
                  fontSize: "0.875rem",
                  fontWeight: 700,
                }}
              >
                {pos.count}
              </div>
            </div>

            {/* Stats Grid */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: espaco.sm,
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
                  Carga
                </div>
                <div
                  style={{
                    fontSize: "1.125rem",
                    fontWeight: 700,
                    color: "white",
                  }}
                >
                  {pos.avgLoad.toLocaleString("pt-PT")}
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
                      pos.avgWellness >= 15
                        ? cores.sucesso
                        : pos.avgWellness >= 14
                        ? "white"
                        : cores.atencao,
                  }}
                >
                  {pos.avgWellness}/20
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
                  Distância
                </div>
                <div
                  style={{
                    fontSize: "1.125rem",
                    fontWeight: 700,
                    color: "white",
                  }}
                >
                  {pos.avgDistance.toFixed(1)}km
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
                  Risco Lesão
                </div>
                <div
                  style={{
                    fontSize: "1.125rem",
                    fontWeight: 700,
                    color:
                      pos.injuryRate < 10
                        ? cores.sucesso
                        : pos.injuryRate < 15
                        ? cores.atencao
                        : cores.cargaInterna,
                  }}
                >
                  {pos.injuryRate}%
                </div>
              </div>
            </div>

            {/* Trend Bar */}
            <div
              style={{
                marginTop: espaco.md,
                paddingTop: espaco.md,
                borderTop: `1px solid ${cores.borda}`,
              }}
            >
              <div
                style={{
                  fontSize: "0.75rem",
                  color: cores.textoSuave,
                  marginBottom: espaco.xs,
                }}
              >
                Tendência
              </div>
              <div
                style={{
                  display: "flex",
                  gap: 2,
                  height: 4,
                }}
              >
                {Array.from({ length: 8 }).map((_, idx) => (
                  <div
                    key={idx}
                    style={{
                      flex: 1,
                      background: [
                        cores.sucesso,
                        cores.sucesso,
                        cores.atencao,
                        cores.atencao,
                        cores.cargaInterna,
                        cores.cargaInterna,
                        cores.atencao,
                        cores.sucesso,
                      ][idx],
                      borderRadius: 1,
                    }}
                  />
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Detailed View for Selected Position */}
      {selectedPosition && (
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
            Detalhes - {selectedPosition}
          </h3>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
              gap: espaco.lg,
            }}
          >
            {[
              {
                title: "Distribuição de Carga",
                values: [
                  "< 2000 au: 0 jogadores",
                  "2000-3000: 1 jogador",
                  "3000-4000: 4 jogadores",
                  "> 4000: 18 jogadores",
                ],
              },
              {
                title: "Estado de Bem-estar",
                values: [
                  "Excelente (>16): 8 jogadores",
                  "Bom (14-16): 10 jogadores",
                  "Normal (12-14): 4 jogadores",
                  "Necessário Descanso (<12): 1 jogador",
                ],
              },
              {
                title: "Risco de Lesão",
                values: [
                  "Baixo (<10%): 15 jogadores",
                  "Moderado (10-15%): 8 jogadores",
                  "Alto (15-20%): 2 jogadores",
                  "Muito Alto (>20%): 0 jogadores",
                ],
              },
            ].map((detail, idx) => (
              <div key={idx}>
                <h4
                  style={{
                    fontSize: "0.875rem",
                    fontWeight: 700,
                    color: cores.destaque,
                    marginBottom: espaco.md,
                    textTransform: "uppercase",
                    letterSpacing: 0.5,
                  }}
                >
                  {detail.title}
                </h4>
                <ul
                  style={{
                    listStyle: "none",
                    padding: 0,
                    margin: 0,
                  }}
                >
                  {detail.values.map((value, vidx) => (
                    <li
                      key={vidx}
                      style={{
                        fontSize: "0.875rem",
                        color: cores.textoSuave,
                        marginBottom: espaco.sm,
                        paddingLeft: espaco.md,
                      }}
                    >
                      • {value}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
