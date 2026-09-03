"use client";

import { useRouter } from "next/navigation";
import { cores, espaco, raio } from "@/lib/theme";
import { PageHeader } from "@/components/layout/PageHeader";

export default function SettingsPage() {
  const router = useRouter();

  return (
    <div style={{ padding: espaco.xl, maxWidth: 1400, margin: "0 auto" }}>
      <PageHeader
        titulo="Definições"
        subtitulo="Configuração de equipa, dados e sistema"
      />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
          gap: espaco.lg,
        }}
      >
        <div
          onClick={() => router.push("/configuracoes/equipa")}
          style={{
            background: cores.bgElevado,
            border: `1px solid ${cores.borda}`,
            borderRadius: raio.md,
            padding: espaco.lg,
            cursor: "pointer",
            transition: "all 0.2s",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLElement).style.background =
              cores.cargaInterna;
            (e.currentTarget as HTMLElement).style.borderColor =
              cores.cargaInterna;
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLElement).style.background =
              cores.bgElevado;
            (e.currentTarget as HTMLElement).style.borderColor = cores.borda;
          }}
        >
          <div
            style={{
              fontSize: "1.5rem",
              marginBottom: espaco.md,
            }}
          >
            👥
          </div>
          <h3
            style={{
              fontSize: "1rem",
              fontWeight: 700,
              color: "white",
              marginBottom: espaco.sm,
            }}
          >
            Equipa
          </h3>
          <p style={{ fontSize: "0.875rem", color: cores.textoSuave }}>
            Informações e membros da equipa
          </p>
        </div>

        <div
          onClick={() => router.push("/configuracoes/jogadores")}
          style={{
            background: cores.bgElevado,
            border: `1px solid ${cores.borda}`,
            borderRadius: raio.md,
            padding: espaco.lg,
            cursor: "pointer",
            transition: "all 0.2s",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLElement).style.background = cores.sucesso;
            (e.currentTarget as HTMLElement).style.borderColor = cores.sucesso;
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLElement).style.background =
              cores.bgElevado;
            (e.currentTarget as HTMLElement).style.borderColor = cores.borda;
          }}
        >
          <div
            style={{
              fontSize: "1.5rem",
              marginBottom: espaco.md,
            }}
          >
            🎽
          </div>
          <h3
            style={{
              fontSize: "1rem",
              fontWeight: 700,
              color: "white",
              marginBottom: espaco.sm,
            }}
          >
            Jogadores
          </h3>
          <p style={{ fontSize: "0.875rem", color: cores.textoSuave }}>
            Adicionar, editar e remover jogadores
          </p>
        </div>

        <div
          onClick={() => router.push("/sistema")}
          style={{
            background: cores.bgElevado,
            border: `1px solid ${cores.borda}`,
            borderRadius: raio.md,
            padding: espaco.lg,
            cursor: "pointer",
            transition: "all 0.2s",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLElement).style.background =
              cores.atencao;
            (e.currentTarget as HTMLElement).style.borderColor =
              cores.atencao;
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLElement).style.background =
              cores.bgElevado;
            (e.currentTarget as HTMLElement).style.borderColor = cores.borda;
          }}
        >
          <div
            style={{
              fontSize: "1.5rem",
              marginBottom: espaco.md,
            }}
          >
            🔗
          </div>
          <h3
            style={{
              fontSize: "1rem",
              fontWeight: 700,
              color: "white",
              marginBottom: espaco.sm,
            }}
          >
            Dados e Importações
          </h3>
          <p style={{ fontSize: "0.875rem", color: cores.textoSuave }}>
            Histórico de importações e validação de dados
          </p>
        </div>

        <div
          onClick={() => router.push("/sistema")}
          style={{
            background: cores.bgElevado,
            border: `1px solid ${cores.borda}`,
            borderRadius: raio.md,
            padding: espaco.lg,
            cursor: "pointer",
            transition: "all 0.2s",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLElement).style.background =
              cores.cargaInterna;
            (e.currentTarget as HTMLElement).style.borderColor =
              cores.cargaInterna;
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLElement).style.background =
              cores.bgElevado;
            (e.currentTarget as HTMLElement).style.borderColor = cores.borda;
          }}
        >
          <div
            style={{
              fontSize: "1.5rem",
              marginBottom: espaco.md,
            }}
          >
            🔧
          </div>
          <h3
            style={{
              fontSize: "1rem",
              fontWeight: 700,
              color: "white",
              marginBottom: espaco.sm,
            }}
          >
            Sistema
          </h3>
          <p style={{ fontSize: "0.875rem", color: cores.textoSuave }}>
            Diagnóstico do sistema e estado dos dados
          </p>
        </div>
      </div>
    </div>
  );
}
