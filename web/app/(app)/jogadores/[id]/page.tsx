"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { cores, espaco, raio } from "@/lib/theme";
import { PageHeader } from "@/components/layout/PageHeader";
import { StatusIndicator } from "@/components/ui/StatusIndicator";

interface PlayerProfile {
  id: string;
  name: string;
  number: number;
  position: string;
  age: number;
  height: string;
  weight: string;
  status: "normal" | "attention" | "high-attention";
  availabilityState: "apto" | "lesionado" | "em_recuperacao" | "ausente";
}

type TabType = "overview" | "carga" | "gps" | "bem-estar" | "fisico" | "historico";

export default function PlayerProfilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const router = useRouter();
  const [tab, setTab] = useState<TabType>("overview");

  // TODO: Fetch player data from API using params.id
  const player: PlayerProfile = {
    id: "1",
    name: "João Silva",
    number: 7,
    position: "Médio Centro",
    age: 28,
    height: "1.82m",
    weight: "78kg",
    status: "high-attention",
    availabilityState: "apto",
  };

  const tabs: { id: TabType; label: string; emoji: string }[] = [
    { id: "overview", label: "Resumo", emoji: "👁️" },
    { id: "carga", label: "Carga", emoji: "🏋️" },
    { id: "gps", label: "GPS", emoji: "🏃" },
    { id: "bem-estar", label: "Bem-estar", emoji: "😊" },
    { id: "fisico", label: "Físico", emoji: "💪" },
    { id: "historico", label: "Histórico", emoji: "📋" },
  ];

  const availabilityLabel = {
    apto: "✅ Disponível",
    lesionado: "🤕 Lesionado",
    em_recuperacao: "⚕️ Recuperação",
    ausente: "❌ Ausente",
  };

  return (
    <div style={{ padding: espaco.xl, maxWidth: 1400, margin: "0 auto" }}>
      {/* Header with Player Info */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "start",
          marginBottom: espaco.xl,
          gap: espaco.lg,
          flexWrap: "wrap",
        }}
      >
        <div>
          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: espaco.md,
              marginBottom: espaco.md,
            }}
          >
            <span
              style={{
                fontSize: "3rem",
                fontWeight: 700,
                color: cores.destaque,
              }}
            >
              #{player.number}
            </span>
            <h1
              style={{
                fontSize: "2.5rem",
                fontWeight: 700,
                color: "white",
              }}
            >
              {player.name}
            </h1>
          </div>
          <p style={{ fontSize: "1.125rem", color: cores.textoSuave }}>
            {player.position}
          </p>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: espaco.md,
            alignItems: "flex-end",
          }}
        >
          <StatusIndicator status={player.status} size="lg" />
          <div
            style={{
              background: cores.bg,
              borderRadius: raio.sm,
              padding: `${espaco.sm}px ${espaco.lg}px`,
              fontSize: "0.875rem",
              fontWeight: 600,
              color: cores.textoSuave,
            }}
          >
            {availabilityLabel[player.availabilityState]}
          </div>
        </div>
      </div>

      {/* Player Info Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
          gap: espaco.lg,
          marginBottom: espaco.xl,
        }}
      >
        {[
          { label: "Idade", value: `${player.age}` },
          { label: "Altura", value: player.height },
          { label: "Peso", value: player.weight },
          { label: "Idade Treino", value: "8 anos" },
        ].map((card, idx) => (
          <div
            key={idx}
            style={{
              background: cores.bgElevado,
              border: `1px solid ${cores.borda}`,
              borderRadius: raio.md,
              padding: espaco.lg,
              textAlign: "center",
            }}
          >
            <div
              style={{
                fontSize: "0.75rem",
                color: cores.textoSuave,
                marginBottom: espaco.sm,
                textTransform: "uppercase",
                letterSpacing: 0.5,
              }}
            >
              {card.label}
            </div>
            <div
              style={{
                fontSize: "1.5rem",
                fontWeight: 700,
                color: "white",
              }}
            >
              {card.value}
            </div>
          </div>
        ))}
      </div>

      {/* Tab Navigation */}
      <div
        style={{
          display: "flex",
          gap: espaco.sm,
          marginBottom: espaco.xl,
          borderBottom: `1px solid ${cores.borda}`,
          overflow: "auto",
        }}
      >
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              padding: `${espaco.md}px ${espaco.lg}px`,
              background: "none",
              border: "none",
              borderBottom:
                tab === t.id ? `3px solid ${cores.destaque}` : "none",
              color: tab === t.id ? cores.destaque : cores.textoSuave,
              cursor: "pointer",
              fontWeight: 600,
              fontSize: "0.875rem",
              transition: "all 0.2s",
              whiteSpace: "nowrap",
            }}
          >
            {t.emoji} {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div>
        {/* Overview Tab */}
        {tab === "overview" && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
              gap: espaco.lg,
            }}
          >
            {/* Current Status */}
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
                  fontSize: "1rem",
                  fontWeight: 700,
                  color: "white",
                  marginBottom: espaco.lg,
                }}
              >
                📊 Status Atual
              </h3>
              <div style={{ display: "grid", gap: espaco.md }}>
                {[
                  { label: "Carga Semana", value: "4200 au", color: cores.cargaInterna },
                  { label: "Bem-estar", value: "13/20", color: cores.atencao },
                  { label: "ACWR", value: "1.45", color: cores.cargaInterna },
                  { label: "Disponibilidade", value: "100%", color: cores.sucesso },
                ].map((item, idx) => (
                  <div key={idx} style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: cores.textoSuave }}>{item.label}</span>
                    <span style={{ color: item.color, fontWeight: 700 }}>{item.value}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Last Session */}
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
                  fontSize: "1rem",
                  fontWeight: 700,
                  color: "white",
                  marginBottom: espaco.lg,
                }}
              >
                📅 Última Sessão
              </h3>
              <div style={{ display: "grid", gap: espaco.md }}>
                {[
                  { label: "Data", value: "01 Set 2026" },
                  { label: "Tipo", value: "Jogo" },
                  { label: "Duração", value: "90 min" },
                  { label: "Dia MD", value: "MD" },
                ].map((item, idx) => (
                  <div key={idx} style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: cores.textoSuave }}>{item.label}</span>
                    <span style={{ color: "white", fontWeight: 600 }}>{item.value}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Alerts */}
            <div
              style={{
                background: "rgba(239,68,68,0.12)",
                border: `1px solid ${cores.cargaInterna}`,
                borderRadius: raio.md,
                padding: espaco.lg,
              }}
            >
              <h3
                style={{
                  fontSize: "1rem",
                  fontWeight: 700,
                  color: cores.cargaInterna,
                  marginBottom: espaco.lg,
                }}
              >
                ⚠️ Alertas Ativos
              </h3>
              <div style={{ display: "grid", gap: espaco.md }}>
                <div>
                  <div style={{ fontSize: "0.875rem", color: cores.cargaInterna, fontWeight: 600 }}>
                    Carga muito elevada (ACWR 1.45)
                  </div>
                  <div style={{ fontSize: "0.75rem", color: cores.textoSuave, marginTop: espaco.xs }}>
                    Reduzir intensidade nos próximos 1-2 sessões
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "0.875rem", color: cores.atencao, fontWeight: 600 }}>
                    Bem-estar abaixo do normal
                  </div>
                  <div style={{ fontSize: "0.75rem", color: cores.textoSuave, marginTop: espaco.xs }}>
                    Verificar sono, stress e recuperação
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Carga Tab */}
        {tab === "carga" && (
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
              Análise de Carga (últimas 8 semanas)
            </h3>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
                gap: espaco.lg,
              }}
            >
              {[
                { label: "Carga Aguda (7d)", value: "4200 au", emoji: "⚡" },
                { label: "Carga Crónica (28d)", value: "2896 au", emoji: "🏋️" },
                { label: "ACWR", value: "1.45", emoji: "📊", color: cores.cargaInterna },
                { label: "Monotonia", value: "1.8", emoji: "📈" },
                { label: "Strain", value: "3360", emoji: "💨" },
                { label: "Mudança Semana", value: "+12%", emoji: "📈", color: cores.atencao },
              ].map((metric, idx) => (
                <div key={idx}>
                  <div style={{ fontSize: "0.875rem", color: cores.textoSuave, marginBottom: espaco.sm }}>
                    {metric.emoji} {metric.label}
                  </div>
                  <div
                    style={{
                      fontSize: "1.75rem",
                      fontWeight: 700,
                      color: metric.color || "white",
                    }}
                  >
                    {metric.value}
                  </div>
                </div>
              ))}
            </div>

            {/* TODO: Add chart component here */}
            <div
              style={{
                marginTop: espaco.xl,
                padding: espaco.lg,
                background: cores.bg,
                borderRadius: raio.md,
                textAlign: "center",
                color: cores.textoSuave,
              }}
            >
              📉 Gráfico de carga ao longo do tempo (será renderizado com Plotly)
            </div>
          </div>
        )}

        {/* GPS Tab */}
        {tab === "gps" && (
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
              Dados GPS
            </h3>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
                gap: espaco.lg,
              }}
            >
              {[
                { label: "Distância Média", value: "8.2 km", emoji: "🏃" },
                { label: "HSR Acumulada", value: "2100 m", emoji: "💨" },
                { label: "Sprints", value: "18", emoji: "⚡" },
                { label: "Acelerações", value: "42", emoji: "📈" },
                { label: "Desacelerações", value: "38", emoji: "📉" },
                { label: "Velocidade Máxima", value: "26.5 km/h", emoji: "🚀" },
              ].map((metric, idx) => (
                <div key={idx}>
                  <div style={{ fontSize: "0.875rem", color: cores.textoSuave, marginBottom: espaco.sm }}>
                    {metric.emoji} {metric.label}
                  </div>
                  <div
                    style={{
                      fontSize: "1.5rem",
                      fontWeight: 700,
                      color: "white",
                    }}
                  >
                    {metric.value}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Bem-estar Tab */}
        {tab === "bem-estar" && (
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
              Questionário de Bem-estar
            </h3>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
                gap: espaco.lg,
              }}
            >
              {[
                { label: "Qualidade do Sono", value: "2/5", emoji: "😴", color: cores.atencao },
                { label: "Fadiga", value: "4/5", emoji: "😫", color: cores.cargaInterna },
                { label: "Stress", value: "3/5", emoji: "😰", color: cores.atencao },
                { label: "Dor Muscular", value: "3/5", emoji: "💪", color: cores.atencao },
                { label: "Humor", value: "2/5", emoji: "😊", color: cores.atencao },
                { label: "Bem-estar Geral", value: "13/20", emoji: "📊", color: cores.atencao },
              ].map((metric, idx) => (
                <div key={idx}>
                  <div style={{ fontSize: "0.875rem", color: cores.textoSuave, marginBottom: espaco.sm }}>
                    {metric.emoji} {metric.label}
                  </div>
                  <div
                    style={{
                      fontSize: "1.5rem",
                      fontWeight: 700,
                      color: metric.color,
                    }}
                  >
                    {metric.value}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Físico Tab */}
        {tab === "fisico" && (
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
              Testes Físicos
            </h3>
            <div
              style={{
                padding: espaco.lg,
                background: cores.bg,
                borderRadius: raio.md,
                textAlign: "center",
                color: cores.textoSuave,
              }}
            >
              ℹ️ Nenhum teste registado ainda
            </div>
            <button
              style={{
                marginTop: espaco.lg,
                padding: `${espaco.md}px ${espaco.lg}px`,
                borderRadius: raio.sm,
                background: cores.destaque,
                color: "white",
                border: "none",
                cursor: "pointer",
                fontWeight: 600,
              }}
            >
              Adicionar Teste Físico
            </button>
          </div>
        )}

        {/* Histórico Tab */}
        {tab === "historico" && (
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
              Histórico de Sessões
            </h3>
            <div
              style={{
                display: "grid",
                gap: espaco.lg,
              }}
            >
              {[
                {
                  date: "01 Set 2026",
                  type: "Jogo",
                  duration: "90 min",
                  load: "3200 au",
                  distance: "8.5 km",
                },
                {
                  date: "31 Ago 2026",
                  type: "Treino Técnico",
                  duration: "75 min",
                  load: "2100 au",
                  distance: "6.2 km",
                },
                {
                  date: "30 Ago 2026",
                  type: "Recuperação",
                  duration: "45 min",
                  load: "800 au",
                  distance: "4.1 km",
                },
              ].map((session, idx) => (
                <div
                  key={idx}
                  style={{
                    background: cores.bg,
                    borderRadius: raio.sm,
                    padding: espaco.lg,
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr 1fr 1fr 1fr",
                    gap: espaco.lg,
                    alignItems: "center",
                  }}
                >
                  <div>
                    <div style={{ fontSize: "0.75rem", color: cores.textoSuave }}>Data</div>
                    <div style={{ fontWeight: 600, color: "white" }}>{session.date}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: "0.75rem", color: cores.textoSuave }}>Tipo</div>
                    <div style={{ fontWeight: 600, color: "white" }}>{session.type}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: "0.75rem", color: cores.textoSuave }}>Duração</div>
                    <div style={{ fontWeight: 600, color: "white" }}>{session.duration}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: "0.75rem", color: cores.textoSuave }}>Carga</div>
                    <div style={{ fontWeight: 600, color: cores.destaque }}>{session.load}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: "0.75rem", color: cores.textoSuave }}>Distância</div>
                    <div style={{ fontWeight: 600, color: "white" }}>{session.distance}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
