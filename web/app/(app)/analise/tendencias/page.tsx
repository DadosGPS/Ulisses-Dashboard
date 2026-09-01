"use client";

import { useState } from "react";
import { cores, espaco, raio } from "@/lib/theme";
import { PageHeader } from "@/components/layout/PageHeader";

interface TrendData {
  period: string;
  value: number;
}

interface Trend {
  metric: string;
  emoji: string;
  unit: string;
  direction: "up" | "down" | "stable";
  data: TrendData[];
}

export default function TrendsAnalysisPage() {
  const [timeRange, setTimeRange] = useState<"4w" | "8w" | "16w">("8w");

  // TODO: Fetch trend data from API
  const trends: Trend[] = [
    {
      metric: "Carga Total",
      emoji: "🏋️",
      unit: "au",
      direction: "up",
      data: [
        { period: "W1", value: 42000 },
        { period: "W2", value: 44100 },
        { period: "W3", value: 45200 },
        { period: "W4", value: 46800 },
        { period: "W5", value: 52100 },
        { period: "W6", value: 48600 },
        { period: "W7", value: 47300 },
        { period: "W8", value: 50200 },
      ],
    },
    {
      metric: "Bem-estar Médio",
      emoji: "😊",
      unit: "/20",
      direction: "down",
      data: [
        { period: "W1", value: 16.5 },
        { period: "W2", value: 16.2 },
        { period: "W3", value: 16.1 },
        { period: "W4", value: 15.8 },
        { period: "W5", value: 14.8 },
        { period: "W6", value: 15.5 },
        { period: "W7", value: 15.8 },
        { period: "W8", value: 15.2 },
      ],
    },
    {
      metric: "ACWR Médio",
      emoji: "📊",
      unit: "",
      direction: "stable",
      data: [
        { period: "W1", value: 1.0 },
        { period: "W2", value: 1.05 },
        { period: "W3", value: 1.1 },
        { period: "W4", value: 1.15 },
        { period: "W5", value: 1.35 },
        { period: "W6", value: 1.2 },
        { period: "W7", value: 1.18 },
        { period: "W8", value: 1.25 },
      ],
    },
    {
      metric: "Distância Média por Sessão",
      emoji: "🏃",
      unit: "km",
      direction: "stable",
      data: [
        { period: "W1", value: 7.8 },
        { period: "W2", value: 7.9 },
        { period: "W3", value: 8.0 },
        { period: "W4", value: 8.1 },
        { period: "W5", value: 8.3 },
        { period: "W6", value: 8.2 },
        { period: "W7", value: 8.1 },
        { period: "W8", value: 8.0 },
      ],
    },
  ];

  const getDirectionEmoji = (direction: "up" | "down" | "stable") => {
    if (direction === "up") return "📈";
    if (direction === "down") return "📉";
    return "➡️";
  };

  const getChangePercent = (trend: Trend) => {
    const first = trend.data[0].value;
    const last = trend.data[trend.data.length - 1].value;
    return (((last - first) / first) * 100).toFixed(1);
  };

  return (
    <div style={{ padding: espaco.xl, maxWidth: 1400, margin: "0 auto" }}>
      <PageHeader
        titulo="Análise de Tendências"
        subtitulo="Evolução de métricas ao longo do tempo"
      />

      {/* Time Range Selector */}
      <div
        style={{
          display: "flex",
          gap: espaco.lg,
          marginBottom: espaco.xl,
          flexWrap: "wrap",
        }}
      >
        {(["4w", "8w", "16w"] as const).map((range) => (
          <button
            key={range}
            onClick={() => setTimeRange(range)}
            style={{
              padding: `${espaco.sm}px ${espaco.lg}px`,
              borderRadius: raio.sm,
              background:
                timeRange === range ? cores.cargaInterna : cores.bgElevado,
              color: timeRange === range ? "white" : cores.textoSuave,
              border: `1px solid ${
                timeRange === range ? cores.cargaInterna : cores.borda
              }`,
              cursor: "pointer",
              fontWeight: 600,
              fontSize: "0.875rem",
              transition: "all 0.2s",
            }}
          >
            {range === "4w" && "Últimas 4 Semanas"}
            {range === "8w" && "Últimas 8 Semanas"}
            {range === "16w" && "Últimas 16 Semanas"}
          </button>
        ))}
      </div>

      {/* Summary Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
          gap: espaco.lg,
          marginBottom: espaco.xl,
        }}
      >
        {trends.map((trend) => {
          const changePercent = getChangePercent(trend);
          const isPositive = parseFloat(changePercent) >= 0;

          return (
            <div
              key={trend.metric}
              style={{
                background: cores.bgElevado,
                border: `1px solid ${cores.borda}`,
                borderRadius: raio.md,
                padding: espaco.lg,
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: espaco.md,
                }}
              >
                <h4
                  style={{
                    fontSize: "1rem",
                    fontWeight: 700,
                    color: "white",
                  }}
                >
                  {trend.emoji} {trend.metric}
                </h4>
                <div
                  style={{
                    fontSize: "1.5rem",
                  }}
                >
                  {getDirectionEmoji(trend.direction)}
                </div>
              </div>

              {/* Current Value */}
              <div
                style={{
                  marginBottom: espaco.md,
                }}
              >
                <div
                  style={{
                    fontSize: "2rem",
                    fontWeight: 700,
                    color: "white",
                  }}
                >
                  {trend.data[trend.data.length - 1].value.toLocaleString("pt-PT", {
                    maximumFractionDigits: 1,
                  })}
                </div>
                <div
                  style={{
                    fontSize: "0.75rem",
                    color: cores.textoSuave,
                    marginBottom: espaco.sm,
                  }}
                >
                  {trend.unit}
                </div>
              </div>

              {/* Change Badge */}
              <div
                style={{
                  background:
                    isPositive && trend.direction === "up"
                      ? "rgba(34,197,94,0.15)"
                      : isPositive && trend.direction === "down"
                      ? "rgba(239,68,68,0.15)"
                      : "rgba(234,179,8,0.15)",
                  border: `1px solid ${
                    isPositive && trend.direction === "up"
                      ? cores.sucesso
                      : isPositive && trend.direction === "down"
                      ? cores.cargaInterna
                      : cores.atencao
                  }`,
                  borderRadius: raio.sm,
                  padding: espaco.sm,
                  textAlign: "center",
                  fontSize: "0.875rem",
                  fontWeight: 700,
                  color:
                    isPositive && trend.direction === "up"
                      ? cores.sucesso
                      : isPositive && trend.direction === "down"
                      ? cores.cargaInterna
                      : cores.atencao,
                }}
              >
                {isPositive ? "+" : ""}{changePercent}% neste período
              </div>

              {/* Mini Chart */}
              <div
                style={{
                  marginTop: espaco.lg,
                  paddingTop: espaco.lg,
                  borderTop: `1px solid ${cores.borda}`,
                  display: "flex",
                  alignItems: "flex-end",
                  gap: 3,
                  height: 40,
                }}
              >
                {trend.data.map((point, idx) => {
                  const maxValue = Math.max(...trend.data.map((d) => d.value));
                  const minValue = Math.min(...trend.data.map((d) => d.value));
                  const range = maxValue - minValue || 1;
                  const height =
                    ((point.value - minValue) / range) * 100;

                  return (
                    <div
                      key={idx}
                      style={{
                        flex: 1,
                        height: `${height}%`,
                        background: cores.destaque,
                        borderRadius: "2px 2px 0 0",
                        opacity: 0.6 + idx * 0.05,
                      }}
                    />
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Insights */}
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
          💡 Insights Principais
        </h3>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
            gap: espaco.lg,
          }}
        >
          {[
            {
              title: "Carga em Ascensão",
              description:
                "A carga de treino aumentou 19.5% nas últimas 8 semanas. Monitore bem-estar para evitar overtraining.",
              color: cores.cargaInterna,
            },
            {
              title: "Bem-estar em Declínio",
              description:
                "O bem-estar médio desceu 7.9%. Recomende descanso e recuperação ativa.",
              color: cores.atencao,
            },
            {
              title: "ACWR Elevado",
              description:
                "ACWR médio em 1.25 (zona amarela). Aumentar carga de treino leve ou descanso.",
              color: cores.atencao,
            },
          ].map((insight, idx) => (
            <div
              key={idx}
              style={{
                borderLeft: `4px solid ${insight.color}`,
                paddingLeft: espaco.lg,
              }}
            >
              <h4
                style={{
                  fontSize: "0.875rem",
                  fontWeight: 700,
                  color: insight.color,
                  marginBottom: espaco.sm,
                  textTransform: "uppercase",
                  letterSpacing: 0.5,
                }}
              >
                {insight.title}
              </h4>
              <p
                style={{
                  fontSize: "0.875rem",
                  color: cores.textoSuave,
                  lineHeight: 1.6,
                }}
              >
                {insight.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
