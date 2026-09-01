"use client";

import { cores, espaco, raio } from "@/lib/theme";
import { PageHeader } from "@/components/layout/PageHeader";

const preferencias = [
  { nome: "Unidades de Carga", valor: "au / km / m" },
  { nome: "Idioma", valor: "Português" },
  { nome: "Tema", valor: "Escuro" },
  { nome: "Tempo de alerta", valor: "24h" },
];

const toggles = [
  { nome: "Alertas automáticos", ativo: true },
  { nome: "Notificações por email", ativo: false },
  { nome: "Sincronização automática", ativo: true },
  { nome: "Modo de manutenção", ativo: false },
];

export default function SystemSettingsPage() {
  return (
    <div style={{ padding: espaco.xl, maxWidth: 1200, margin: "0 auto" }}>
      <PageHeader
        titulo="Sistema"
        subtitulo="Preferências gerais e definições de plataforma"
      />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: espaco.lg,
          paddingTop: espaco.xl,
        }}
      >
        {preferencias.map((item) => (
          <div
            key={item.nome}
            style={{
              background: cores.bgElevado,
              border: `1px solid ${cores.borda}`,
              borderRadius: raio.md,
              padding: espaco.lg,
            }}
          >
            <div style={{ color: cores.textoSuave, fontSize: "0.75rem", marginBottom: espaco.sm }}>
              {item.nome}
            </div>
            <div style={{ color: "white", fontWeight: 700, fontSize: "1.1rem" }}>{item.valor}</div>
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
          Preferências de Sistema
        </h3>

        <div style={{ display: "grid", gap: espaco.md }}>
          {toggles.map((toggle) => (
            <div
              key={toggle.nome}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                background: cores.bg,
                borderRadius: raio.sm,
                padding: espaco.md,
              }}
            >
              <span style={{ color: "white", fontWeight: 600 }}>{toggle.nome}</span>
              <div
                style={{
                  width: 54,
                  height: 28,
                  borderRadius: 999,
                  background: toggle.ativo ? cores.sucesso : cores.bordaForte,
                  position: "relative",
                }}
              >
                <div
                  style={{
                    position: "absolute",
                    top: 4,
                    left: toggle.ativo ? 28 : 4,
                    width: 18,
                    height: 18,
                    borderRadius: "50%",
                    background: "white",
                    transition: "all 0.2s",
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
