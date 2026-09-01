"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { cores, espaco, raio } from "@/lib/theme";
import { PageHeader } from "@/components/layout/PageHeader";

type Step = "upload" | "preview" | "mapping" | "process" | "complete";

interface ImportState {
  currentStep: Step;
  fileName: string;
  rawData: string[][];
  mappedColumns: { [csvCol: string]: string };
  errors: string[];
  successCount: number;
}

const CANONICAL_COLUMNS = [
  "Jogador",
  "Data",
  "Tipo",
  "Dia MD",
  "Duração",
  "PSE",
  "Distância",
  "HSR",
  "Sprint",
  "Acelerações",
  "Desacelerações",
  "Vel. Máx",
  "Bem-estar",
];

export default function ImportSessionsPage() {
  const router = useRouter();
  const [state, setState] = useState<ImportState>({
    currentStep: "upload",
    fileName: "",
    rawData: [],
    mappedColumns: {},
    errors: [],
    successCount: 0,
  });

  async function handleFileUpload(file: File) {
    try {
      const text = await file.text();
      const lines = text.split("\n");
      const data = lines
        .slice(0, Math.min(10, lines.length))
        .map((line) => line.split(","));

      setState((prev) => ({
        ...prev,
        fileName: file.name,
        rawData: data,
        currentStep: "preview",
      }));
    } catch (error) {
      setState((prev) => ({
        ...prev,
        errors: ["Erro ao ler ficheiro. Certifique-se de que é um CSV válido."],
      }));
    }
  }

  function goToMapping() {
    setState((prev) => ({
      ...prev,
      currentStep: "mapping",
    }));
  }

  async function handleImport() {
    setState((prev) => ({
      ...prev,
      currentStep: "process",
    }));

    try {
      // TODO: Call actual import API
      // For now, simulate success
      await new Promise((resolve) => setTimeout(resolve, 2000));

      setState((prev) => ({
        ...prev,
        currentStep: "complete",
        successCount: 22,
      }));
    } catch (error) {
      setState((prev) => ({
        ...prev,
        errors: ["Erro ao importar dados. Tente novamente."],
        currentStep: "upload",
      }));
    }
  }

  return (
    <div style={{ padding: espaco.xl, maxWidth: 1000, margin: "0 auto" }}>
      <PageHeader
        titulo="Importar GPS"
        subtitulo="Fazer upload e processar dados de treino"
      />

      {/* Progress Indicator */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: espaco.xl,
          gap: espaco.lg,
        }}
      >
        {["upload", "preview", "mapping", "process", "complete"].map(
          (step, idx) => (
            <div key={step} style={{ flex: 1 }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: espaco.sm,
                  marginBottom: espaco.sm,
                }}
              >
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: "50%",
                    background:
                      ["upload", "preview", "mapping", "process", "complete"].indexOf(
                        state.currentStep
                      ) >= idx
                        ? cores.cargaInterna
                        : cores.borda,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "white",
                    fontWeight: 700,
                    fontSize: "0.875rem",
                  }}
                >
                  {idx + 1}
                </div>
                <span
                  style={{
                    fontSize: "0.875rem",
                    color: cores.textoSuave,
                    fontWeight: 600,
                  }}
                >
                  {step.charAt(0).toUpperCase() + step.slice(1)}
                </span>
              </div>
              {idx < 4 && (
                <div
                  style={{
                    height: 2,
                    background:
                      ["upload", "preview", "mapping", "process"].indexOf(
                        state.currentStep
                      ) > idx
                        ? cores.sucesso
                        : cores.borda,
                    marginTop: "12px",
                  }}
                />
              )}
            </div>
          )
        )}
      </div>

      {/* Step: Upload */}
      {state.currentStep === "upload" && (
        <div
          style={{
            background: cores.bgElevado,
            border: `2px dashed ${cores.borda}`,
            borderRadius: raio.md,
            padding: espaco.xxl,
            textAlign: "center",
            cursor: "pointer",
            transition: "all 0.2s",
          }}
          onDragOver={(e) => {
            e.preventDefault();
            (e.currentTarget as HTMLElement).style.background =
              cores.cargaInterna;
            (e.currentTarget as HTMLElement).style.opacity = "0.5";
          }}
          onDragLeave={(e) => {
            (e.currentTarget as HTMLElement).style.background =
              cores.bgElevado;
            (e.currentTarget as HTMLElement).style.opacity = "1";
          }}
          onDrop={(e) => {
            e.preventDefault();
            const file = e.dataTransfer.files[0];
            if (file) handleFileUpload(file);
          }}
        >
          <div style={{ fontSize: "2rem", marginBottom: espaco.lg }}>
            📤
          </div>
          <h3
            style={{
              fontSize: "1.25rem",
              fontWeight: 700,
              color: "white",
              marginBottom: espaco.sm,
            }}
          >
            Arrastar ficheiro aqui
          </h3>
          <p style={{ color: cores.textoSuave, marginBottom: espaco.lg }}>
            Ou clique para selecionar um arquivo CSV/XLSX
          </p>
          <input
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={(e) => {
              const file = e.currentTarget.files?.[0];
              if (file) handleFileUpload(file);
            }}
            style={{ display: "none" }}
            id="file-input"
          />
          <label htmlFor="file-input">
            <button
              style={{
                background: cores.cargaInterna,
                color: "white",
                border: "none",
                borderRadius: raio.sm,
                padding: `${espaco.md}px ${espaco.lg}px`,
                fontSize: "1rem",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              Selecionar Ficheiro
            </button>
          </label>
          <p
            style={{
              fontSize: "0.75rem",
              color: cores.textoSuave,
              marginTop: espaco.lg,
            }}
          >
            Formatos suportados: CSV, XLSX
          </p>
        </div>
      )}

      {/* Step: Preview */}
      {state.currentStep === "preview" && (
        <div>
          <div
            style={{
              background: cores.bgElevado,
              border: `1px solid ${cores.borda}`,
              borderRadius: raio.md,
              padding: espaco.lg,
              marginBottom: espaco.lg,
            }}
          >
            <h3
              style={{
                fontSize: "1rem",
                fontWeight: 700,
                color: "white",
                marginBottom: espaco.md,
              }}
            >
              Pré-visualização dos Dados
            </h3>
            <div
              style={{
                overflowX: "auto",
                background: cores.bg,
                borderRadius: raio.sm,
                padding: espaco.md,
              }}
            >
              <table
                style={{
                  width: "100%",
                  fontSize: "0.875rem",
                  borderCollapse: "collapse",
                }}
              >
                <thead>
                  <tr>
                    {state.rawData[0]?.map((col, idx) => (
                      <th
                        key={idx}
                        style={{
                          padding: espaco.sm,
                          background: cores.borda,
                          color: "white",
                          fontWeight: 700,
                          textAlign: "left",
                          borderRight: `1px solid ${cores.bg}`,
                        }}
                      >
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {state.rawData.slice(1, 6).map((row, idx) => (
                    <tr key={idx}>
                      {row.map((cell, cidx) => (
                        <td
                          key={cidx}
                          style={{
                            padding: espaco.sm,
                            borderBottom: `1px solid ${cores.borda}`,
                            color: cores.textoSuave,
                            borderRight: `1px solid ${cores.borda}`,
                          }}
                        >
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div
            style={{
              display: "flex",
              gap: espaco.lg,
              justifyContent: "flex-end",
            }}
          >
            <button
              onClick={() =>
                setState((prev) => ({ ...prev, currentStep: "upload" }))
              }
              style={{
                background: cores.borda,
                color: cores.textoSuave,
                border: "none",
                borderRadius: raio.sm,
                padding: `${espaco.md}px ${espaco.lg}px`,
                cursor: "pointer",
                fontWeight: 600,
              }}
            >
              ← Voltar
            </button>
            <button
              onClick={goToMapping}
              style={{
                background: cores.cargaInterna,
                color: "white",
                border: "none",
                borderRadius: raio.sm,
                padding: `${espaco.md}px ${espaco.lg}px`,
                cursor: "pointer",
                fontWeight: 600,
              }}
            >
              Próximo →
            </button>
          </div>
        </div>
      )}

      {/* Step: Mapping */}
      {state.currentStep === "mapping" && (
        <div>
          <div
            style={{
              background: cores.bgElevado,
              border: `1px solid ${cores.borda}`,
              borderRadius: raio.md,
              padding: espaco.lg,
              marginBottom: espaco.lg,
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
              Mapear Colunas
            </h3>
            <p style={{ color: cores.textoSuave, marginBottom: espaco.lg }}>
              Selecione qual coluna do seu ficheiro corresponde a cada métrica:
            </p>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: espaco.lg,
              }}
            >
              {CANONICAL_COLUMNS.map((canonical) => (
                <div key={canonical}>
                  <label
                    style={{
                      display: "block",
                      fontSize: "0.875rem",
                      fontWeight: 600,
                      color: "white",
                      marginBottom: espaco.sm,
                    }}
                  >
                    {canonical}
                  </label>
                  <select
                    style={{
                      width: "100%",
                      padding: `${espaco.sm}px ${espaco.md}px`,
                      borderRadius: raio.sm,
                      background: cores.bg,
                      color: "white",
                      border: `1px solid ${cores.borda}`,
                      fontSize: "0.875rem",
                    }}
                  >
                    <option value="">Não mapeado</option>
                    {state.rawData[0]?.map((col, idx) => (
                      <option key={idx} value={col}>
                        {col}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </div>

          <div
            style={{
              display: "flex",
              gap: espaco.lg,
              justifyContent: "flex-end",
            }}
          >
            <button
              onClick={() =>
                setState((prev) => ({ ...prev, currentStep: "preview" }))
              }
              style={{
                background: cores.borda,
                color: cores.textoSuave,
                border: "none",
                borderRadius: raio.sm,
                padding: `${espaco.md}px ${espaco.lg}px`,
                cursor: "pointer",
                fontWeight: 600,
              }}
            >
              ← Voltar
            </button>
            <button
              onClick={handleImport}
              style={{
                background: cores.sucesso,
                color: "white",
                border: "none",
                borderRadius: raio.sm,
                padding: `${espaco.md}px ${espaco.lg}px`,
                cursor: "pointer",
                fontWeight: 600,
              }}
            >
              Importar →
            </button>
          </div>
        </div>
      )}

      {/* Step: Process */}
      {state.currentStep === "process" && (
        <div
          style={{
            background: cores.bgElevado,
            border: `1px solid ${cores.borda}`,
            borderRadius: raio.md,
            padding: espaco.xxl,
            textAlign: "center",
          }}
        >
          <div style={{ fontSize: "2rem", marginBottom: espaco.lg }}>
            ⏳
          </div>
          <h3
            style={{
              fontSize: "1.25rem",
              fontWeight: 700,
              color: "white",
              marginBottom: espaco.md,
            }}
          >
            Processando Dados...
          </h3>
          <p style={{ color: cores.textoSuave }}>
            Por favor, aguarde enquanto importamos os dados.
          </p>
          <div
            style={{
              marginTop: espaco.lg,
              height: 4,
              background: cores.bg,
              borderRadius: raio.sm,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                height: "100%",
                background: cores.cargaInterna,
                animation: "pulse 1.5s ease-in-out infinite",
                width: "50%",
              }}
            />
          </div>
        </div>
      )}

      {/* Step: Complete */}
      {state.currentStep === "complete" && (
        <div
          style={{
            background: cores.bgElevado,
            border: `1px solid ${cores.borda}`,
            borderRadius: raio.md,
            padding: espaco.xxl,
            textAlign: "center",
          }}
        >
          <div style={{ fontSize: "3rem", marginBottom: espaco.lg }}>
            ✅
          </div>
          <h3
            style={{
              fontSize: "1.5rem",
              fontWeight: 700,
              color: cores.sucesso,
              marginBottom: espaco.md,
            }}
          >
            Importação Concluída!
          </h3>
          <p style={{ fontSize: "1.125rem", color: "white", marginBottom: espaco.lg }}>
            {state.successCount} jogadores/sessões importados com sucesso
          </p>
          <button
            onClick={() => router.push("/sessoes")}
            style={{
              background: cores.cargaInterna,
              color: "white",
              border: "none",
              borderRadius: raio.sm,
              padding: `${espaco.md}px ${espaco.xl}px`,
              cursor: "pointer",
              fontWeight: 700,
              fontSize: "1rem",
            }}
          >
            Ver Sessões
          </button>
        </div>
      )}

      {/* Errors */}
      {state.errors.length > 0 && (
        <div
          style={{
            background: "rgba(239,68,68,0.12)",
            border: `1px solid #ef4444`,
            borderRadius: raio.md,
            padding: espaco.lg,
            marginTop: espaco.lg,
            color: "#ef4444",
          }}
        >
          <strong>Erros:</strong>
          <ul>
            {state.errors.map((error, idx) => (
              <li key={idx}>{error}</li>
            ))}
          </ul>
        </div>
      )}

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
}
