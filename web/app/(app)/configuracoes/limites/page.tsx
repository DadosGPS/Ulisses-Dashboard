"use client";

import { cores, espaco, raio } from "@/lib/theme";
import { PageHeader } from "@/components/layout/PageHeader";

const limites = [
  { nome: "ACWR Alerta", atual: 1.3, ideal: 1.3, unidade: "ratio", cor: cores.atencao },
  { nome: "ACWR Risco", atual: 1.5, ideal: 1.5, unidade: "ratio", cor: cores.cargaInterna },
  { nome: "Load Change", atual: 30, ideal: 30, unidade: "%", cor: cores.atencao },
  { nome: "Wellness Drop", atual: 20, ideal: 20, unidade: "%", cor: cores.atencao },
  { nome: "Velocidade Drop", atual: 12, ideal: 12, unidade: "%", cor: cores.cargaInterna },
  { nome: "HSR Exposure", atual: 40, ideal: 40, unidade: "%", cor: cores.atencao },
];

export default function ThresholdsPage() {
  return (
    <div style={{ padding: espaco.xl, maxWidth: 1200, margin: "0 auto" }}>
      <PageHeader
        titulo="Limites e Alertas"
        subtitulo="Configurar limiares para alertas automáticos"
      />

      <div
        style={{
          marginTop: espaco.xl,
          background: cores.bgElevado,
          border: `1px solid ${cores.borda}`,
          borderRadius: raio.md,
          padding: espaco.lg,
        }}
      >
        <div style={{ display: "grid", gap: espaco.md }}>
          {limites.map((limite) => (
            <div
              key={limite.nome}
              style={{
                display: "grid",
                gridTemplateColumns: "1.8fr 0.9fr 0.9fr 1fr",
                gap: espaco.md,
                background: cores.bg,
                borderRadius: raio.sm,
                padding: espaco.md,
                alignItems: "center",
              }}
            >
              <div style={{ color: "white", fontWeight: 700 }}>{limite.nome}</div>
              <div style={{ color: cores.textoSuave }}>Atual</div>
              <div style={{ color: cores.textoSuave }}>Ideal</div>
              <div
                style={{
                  justifySelf: "end",
                  background: "rgba(255,255,255,0.02)",
                  border: `1px solid ${cores.borda}`,
                  borderRadius: raio.sm,
                  padding: `${espaco.xs}px ${espaco.sm}px`,
                  fontWeight: 700,
                  color: limite.cor,
                }}
              >
                {limite.atual} {limite.unidade}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
