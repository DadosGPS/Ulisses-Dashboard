"use client";

import { useRouter } from "next/navigation";
import { cores, espaco, raio } from "@/lib/theme";
import { PageHeader } from "@/components/layout/PageHeader";

export default function SessionsPage() {
  const router = useRouter();

  return (
    <div style={{ padding: espaco.xl, maxWidth: 1400, margin: "0 auto" }}>
      <PageHeader
        titulo="Sessões"
        subtitulo="Criar, importar e analisar sessões de treino e jogo"
      />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
          gap: espaco.lg,
        }}
      >
        <div
          onClick={() => router.push("/sessoes/lista")}
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
            📋
          </div>
          <h3
            style={{
              fontSize: "1rem",
              fontWeight: 700,
              color: "white",
              marginBottom: espaco.sm,
            }}
          >
            Todas as Sessões
          </h3>
          <p style={{ fontSize: "0.875rem", color: cores.textoSuave }}>
            Ver, filtrar e editar sessões
          </p>
        </div>

        <div
          onClick={() => router.push("/sessoes/nova")}
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
            ➕
          </div>
          <h3
            style={{
              fontSize: "1rem",
              fontWeight: 700,
              color: "white",
              marginBottom: espaco.sm,
            }}
          >
            Criar Sessão
          </h3>
          <p style={{ fontSize: "0.875rem", color: cores.textoSuave }}>
            Adicionar nova sessão manualmente
          </p>
        </div>

        <div
          onClick={() => router.push("/sessoes/importar")}
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
            📥
          </div>
          <h3
            style={{
              fontSize: "1rem",
              fontWeight: 700,
              color: "white",
              marginBottom: espaco.sm,
            }}
          >
            Importar GPS
          </h3>
          <p style={{ fontSize: "0.875rem", color: cores.textoSuave }}>
            Fazer upload de ficheiro CSV/XLSX
          </p>
        </div>
      </div>
    </div>
  );
}
