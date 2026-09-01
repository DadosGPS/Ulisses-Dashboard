"use client";

import { cores, espaco, raio } from "@/lib/theme";
import { PageHeader } from "@/components/layout/PageHeader";

const jogadores = [
  { nome: "João Silva", posicao: "CM", numero: 7, disponibilidade: "Disponível" },
  { nome: "Pedro Costa", posicao: "CB", numero: 4, disponibilidade: "Disponível" },
  { nome: "Miguel Santos", posicao: "LW", numero: 11, disponibilidade: "Recuperação" },
  { nome: "Ana Martins", posicao: "GK", numero: 1, disponibilidade: "Lesionado" },
];

export default function PlayersSettingsPage() {
  return (
    <div style={{ padding: espaco.xl, maxWidth: 1200, margin: "0 auto" }}>
      <PageHeader
        titulo="Jogadores"
        subtitulo="Adicionar, editar e gerir a lista de jogadores"
      />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: espaco.lg,
          paddingTop: espaco.xl,
        }}
      >
        {jogadores.map((jogador) => (
          <div
            key={jogador.nome}
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
              <div>
                <div style={{ color: cores.textoSuave, fontSize: "0.75rem" }}>Número</div>
                <div style={{ color: "white", fontWeight: 700, fontSize: "1.4rem" }}>
                  #{jogador.numero}
                </div>
              </div>
              <div
                style={{
                  background:
                    jogador.disponibilidade === "Disponível"
                      ? "rgba(34,197,94,0.15)"
                      : jogador.disponibilidade === "Recuperação"
                      ? "rgba(245,158,11,0.15)"
                      : "rgba(239,68,68,0.15)",
                  border: `1px solid ${
                    jogador.disponibilidade === "Disponível"
                      ? cores.sucesso
                      : jogador.disponibilidade === "Recuperação"
                      ? cores.atencao
                      : cores.cargaInterna
                  }`,
                  color:
                    jogador.disponibilidade === "Disponível"
                      ? cores.sucesso
                      : jogador.disponibilidade === "Recuperação"
                      ? cores.atencao
                      : cores.cargaInterna,
                  borderRadius: raio.sm,
                  padding: `${espaco.xs}px ${espaco.sm}px`,
                  fontSize: "0.7rem",
                  fontWeight: 700,
                }}
              >
                {jogador.disponibilidade}
              </div>
            </div>

            <h3 style={{ fontSize: "1.125rem", fontWeight: 700, color: "white" }}>
              {jogador.nome}
            </h3>
            <div style={{ color: cores.textoSuave, marginTop: espaco.xs }}>
              {jogador.posicao}
            </div>

            <div
              style={{
                display: "flex",
                gap: espaco.sm,
                marginTop: espaco.lg,
              }}
            >
              <button
                style={{
                  flex: 1,
                  background: cores.destaque,
                  color: "white",
                  border: "none",
                  borderRadius: raio.sm,
                  padding: `${espaco.sm}px ${espaco.md}px`,
                  cursor: "pointer",
                  fontWeight: 600,
                }}
              >
                Editar
              </button>
              <button
                style={{
                  flex: 1,
                  background: cores.bg,
                  color: cores.texto,
                  border: `1px solid ${cores.borda}`,
                  borderRadius: raio.sm,
                  padding: `${espaco.sm}px ${espaco.md}px`,
                  cursor: "pointer",
                  fontWeight: 600,
                }}
              >
                Ver
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
