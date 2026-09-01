"use client";

import { cores, espaco, raio } from "@/lib/theme";
import { PageHeader } from "@/components/layout/PageHeader";

const membros = [
  { nome: "João Silva", papel: "Técnico / Coordenação", status: "Ativo" },
  { nome: "Pedro Costa", papel: "Médio / Observação", status: "Ativo" },
  { nome: "Miguel Santos", papel: "Preparador físico", status: "Ativo" },
  { nome: "Ana Martins", papel: "Analista", status: "Em revisão" },
];

export default function TeamSettingsPage() {
  return (
    <div style={{ padding: espaco.xl, maxWidth: 1200, margin: "0 auto" }}>
      <PageHeader
        titulo="Equipa"
        subtitulo="Informações e membros da equipa"
      />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
          gap: espaco.lg,
          paddingTop: espaco.xl,
        }}
      >
        {[
          { label: "Nome da Equipa", value: "Belenenses FC" },
          { label: "Liga", value: "Liga de Elite" },
          { label: "Nível de Competição", value: "Profissional" },
          { label: "Temporada", value: "2026/27" },
        ].map((item) => (
          <div
            key={item.label}
            style={{
              background: cores.bgElevado,
              border: `1px solid ${cores.borda}`,
              borderRadius: raio.md,
              padding: espaco.lg,
            }}
          >
            <div style={{ fontSize: "0.75rem", color: cores.textoSuave, marginBottom: espaco.sm }}>
              {item.label}
            </div>
            <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "white" }}>
              {item.value}
            </div>
          </div>
        ))}
      </div>

      <div
        style={{
          marginTop: espaco.xxl,
          background: cores.bgElevado,
          border: `1px solid ${cores.borda}`,
          borderRadius: raio.md,
          padding: espaco.lg,
        }}
      >
        <h3 style={{ fontSize: "1.125rem", fontWeight: 700, color: "white", marginBottom: espaco.lg }}>
          Membros da Equipa
        </h3>

        <div style={{ display: "grid", gap: espaco.md }}>
          {membros.map((membro) => (
            <div
              key={membro.nome}
              style={{
                display: "grid",
                gridTemplateColumns: "1.5fr 1.5fr 0.8fr",
                gap: espaco.md,
                background: cores.bg,
                borderRadius: raio.sm,
                padding: espaco.md,
                alignItems: "center",
              }}
            >
              <div>
                <div style={{ color: "white", fontWeight: 700 }}>{membro.nome}</div>
              </div>
              <div style={{ color: cores.textoSuave }}>{membro.papel}</div>
              <div
                style={{
                  justifySelf: "end",
                  background:
                    membro.status === "Ativo"
                      ? "rgba(34,197,94,0.12)"
                      : "rgba(245,158,11,0.12)",
                  border: `1px solid ${
                    membro.status === "Ativo" ? cores.sucesso : cores.atencao
                  }`,
                  color: membro.status === "Ativo" ? cores.sucesso : cores.atencao,
                  padding: `${espaco.xs}px ${espaco.sm}px`,
                  borderRadius: raio.sm,
                  fontSize: "0.75rem",
                  fontWeight: 700,
                  textAlign: "center",
                }}
              >
                {membro.status}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
