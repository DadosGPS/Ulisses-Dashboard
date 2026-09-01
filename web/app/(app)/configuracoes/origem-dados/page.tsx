"use client";

import { cores, espaco, raio } from "@/lib/theme";
import { PageHeader } from "@/components/layout/PageHeader";

const origens = [
  { nome: "GPS Tracker", estado: "Ativa", ultimo: "2 min atrás", tipo: "Sinais em tempo real" },
  { nome: "Supabase Database", estado: "Sincronizada", ultimo: "1 min atrás", tipo: "Base de dados principal" },
  { nome: "CSV Upload", estado: "Pronto", ultimo: "Hoje 09:40", tipo: "Importações manuais" },
  { nome: "Questionário Bem-Estar", estado: "Ativo", ultimo: "Hoje 08:00", tipo: "Inputs de recuperação" },
];

export default function DataSourcesPage() {
  return (
    <div style={{ padding: espaco.xl, maxWidth: 1200, margin: "0 auto" }}>
      <PageHeader
        titulo="Origem de Dados"
        subtitulo="Integrações e histórico de carregamento"
      />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: espaco.lg,
          paddingTop: espaco.xl,
        }}
      >
        {origens.map((origem) => (
          <div
            key={origem.nome}
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
              <h3 style={{ fontSize: "1.125rem", fontWeight: 700, color: "white" }}>
                {origem.nome}
              </h3>
              <span
                style={{
                  padding: `${espaco.xs}px ${espaco.sm}px`,
                  borderRadius: raio.sm,
                  background: origem.estado === "Ativa" || origem.estado === "Sincronizada" ? "rgba(34,197,94,0.12)" : "rgba(245,158,11,0.12)",
                  border: `1px solid ${origem.estado === "Ativa" || origem.estado === "Sincronizada" ? cores.sucesso : cores.atencao}`,
                  color: origem.estado === "Ativa" || origem.estado === "Sincronizada" ? cores.sucesso : cores.atencao,
                  fontSize: "0.7rem",
                  fontWeight: 700,
                }}
              >
                {origem.estado}
              </span>
            </div>

            <div style={{ color: cores.textoSuave, fontSize: "0.875rem", marginBottom: espaco.sm }}>
              {origem.tipo}
            </div>
            <div style={{ color: cores.textoSuave, fontSize: "0.75rem" }}>
              Última atualização: {origem.ultimo}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
