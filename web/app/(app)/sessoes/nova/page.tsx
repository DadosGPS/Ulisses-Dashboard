"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { cores, espaco, raio } from "@/lib/theme";
import { PageHeader } from "@/components/layout/PageHeader";

interface FormData {
  date: string;
  sessionType: string;
  matchDay: string;
  duration: number;
  participants: number;
  rpe: number;
  notes: string;
}

const SESSION_TYPES = [
  "Jogo",
  "MD-1",
  "MD-2",
  "MD-3",
  "MD-4",
  "MD-5",
  "Recuperação",
  "Força",
  "Velocidade",
  "Técnica",
  "Tático",
  "Individual",
  "Outro",
];

const MATCH_DAYS = [
  "MD-5",
  "MD-4",
  "MD-3",
  "MD-2",
  "MD-1",
  "MD (Jogo)",
];

export default function AddSessionPage() {
  const router = useRouter();
  const [formData, setFormData] = useState<FormData>({
    date: new Date().toISOString().split("T")[0],
    sessionType: "Treino",
    matchDay: "MD-2",
    duration: 60,
    participants: 0,
    rpe: 5,
    notes: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      // TODO: Call API to create session
      // For now, just redirect after a delay
      await new Promise((resolve) => setTimeout(resolve, 1000));
      router.push("/sessoes");
    } catch (err) {
      setError("Erro ao criar sessão. Tente novamente.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ padding: espaco.xl, maxWidth: 800, margin: "0 auto" }}>
      <PageHeader
        titulo="Adicionar Sessão"
        subtitulo="Criar nova sessão de treino ou jogo"
      />

      <form onSubmit={handleSubmit}>
        <div
          style={{
            background: cores.bgElevado,
            border: `1px solid ${cores.borda}`,
            borderRadius: raio.md,
            padding: espaco.lg,
            marginBottom: espaco.lg,
          }}
        >
          {/* Date */}
          <div style={{ marginBottom: espaco.lg }}>
            <label
              style={{
                display: "block",
                fontSize: "0.875rem",
                fontWeight: 700,
                color: "white",
                marginBottom: espaco.sm,
              }}
            >
              Data *
            </label>
            <input
              type="date"
              required
              value={formData.date}
              onChange={(e) =>
                setFormData({ ...formData, date: e.currentTarget.value })
              }
              style={{
                width: "100%",
                padding: `${espaco.md}px ${espaco.md}px`,
                borderRadius: raio.sm,
                background: cores.bg,
                border: `1px solid ${cores.borda}`,
                color: "white",
                fontSize: "1rem",
              }}
            />
          </div>

          {/* Session Type */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: espaco.lg,
              marginBottom: espaco.lg,
            }}
          >
            <div>
              <label
                style={{
                  display: "block",
                  fontSize: "0.875rem",
                  fontWeight: 700,
                  color: "white",
                  marginBottom: espaco.sm,
                }}
              >
                Tipo de Sessão *
              </label>
              <select
                required
                value={formData.sessionType}
                onChange={(e) =>
                  setFormData({ ...formData, sessionType: e.currentTarget.value })
                }
                style={{
                  width: "100%",
                  padding: `${espaco.md}px ${espaco.md}px`,
                  borderRadius: raio.sm,
                  background: cores.bg,
                  border: `1px solid ${cores.borda}`,
                  color: "white",
                  fontSize: "1rem",
                }}
              >
                {SESSION_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label
                style={{
                  display: "block",
                  fontSize: "0.875rem",
                  fontWeight: 700,
                  color: "white",
                  marginBottom: espaco.sm,
                }}
              >
                Dia MD *
              </label>
              <select
                required
                value={formData.matchDay}
                onChange={(e) =>
                  setFormData({ ...formData, matchDay: e.currentTarget.value })
                }
                style={{
                  width: "100%",
                  padding: `${espaco.md}px ${espaco.md}px`,
                  borderRadius: raio.sm,
                  background: cores.bg,
                  border: `1px solid ${cores.borda}`,
                  color: "white",
                  fontSize: "1rem",
                }}
              >
                {MATCH_DAYS.map((day) => (
                  <option key={day} value={day}>
                    {day}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Duration and Participants */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: espaco.lg,
              marginBottom: espaco.lg,
            }}
          >
            <div>
              <label
                style={{
                  display: "block",
                  fontSize: "0.875rem",
                  fontWeight: 700,
                  color: "white",
                  marginBottom: espaco.sm,
                }}
              >
                Duração (minutos) *
              </label>
              <input
                type="number"
                required
                min="1"
                value={formData.duration}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    duration: parseInt(e.currentTarget.value) || 0,
                  })
                }
                style={{
                  width: "100%",
                  padding: `${espaco.md}px ${espaco.md}px`,
                  borderRadius: raio.sm,
                  background: cores.bg,
                  border: `1px solid ${cores.borda}`,
                  color: "white",
                  fontSize: "1rem",
                }}
              />
            </div>

            <div>
              <label
                style={{
                  display: "block",
                  fontSize: "0.875rem",
                  fontWeight: 700,
                  color: "white",
                  marginBottom: espaco.sm,
                }}
              >
                Participantes
              </label>
              <input
                type="number"
                min="0"
                value={formData.participants}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    participants: parseInt(e.currentTarget.value) || 0,
                  })
                }
                style={{
                  width: "100%",
                  padding: `${espaco.md}px ${espaco.md}px`,
                  borderRadius: raio.sm,
                  background: cores.bg,
                  border: `1px solid ${cores.borda}`,
                  color: "white",
                  fontSize: "1rem",
                }}
              />
            </div>
          </div>

          {/* RPE */}
          <div style={{ marginBottom: espaco.lg }}>
            <label
              style={{
                display: "block",
                fontSize: "0.875rem",
                fontWeight: 700,
                color: "white",
                marginBottom: espaco.sm,
              }}
            >
              RPE da Sessão (0-10): {formData.rpe}
            </label>
            <input
              type="range"
              min="0"
              max="10"
              step="0.5"
              value={formData.rpe}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  rpe: parseFloat(e.currentTarget.value),
                })
              }
              style={{
                width: "100%",
              }}
            />
          </div>

          {/* Notes */}
          <div>
            <label
              style={{
                display: "block",
                fontSize: "0.875rem",
                fontWeight: 700,
                color: "white",
                marginBottom: espaco.sm,
              }}
            >
              Notas
            </label>
            <textarea
              value={formData.notes}
              onChange={(e) =>
                setFormData({ ...formData, notes: e.currentTarget.value })
              }
              style={{
                width: "100%",
                minHeight: 120,
                padding: `${espaco.md}px ${espaco.md}px`,
                borderRadius: raio.sm,
                background: cores.bg,
                border: `1px solid ${cores.borda}`,
                color: "white",
                fontSize: "1rem",
                fontFamily: "inherit",
              }}
              placeholder="Notas sobre a sessão..."
            />
          </div>
        </div>

        {error && (
          <div
            style={{
              background: "rgba(239,68,68,0.12)",
              border: `1px solid #ef4444`,
              borderRadius: raio.md,
              padding: espaco.lg,
              color: "#ef4444",
              marginBottom: espaco.lg,
              fontWeight: 600,
            }}
          >
            {error}
          </div>
        )}

        <div
          style={{
            display: "flex",
            gap: espaco.lg,
            justifyContent: "flex-end",
          }}
        >
          <button
            type="button"
            onClick={() => router.back()}
            style={{
              background: cores.borda,
              color: cores.textoSuave,
              border: "none",
              borderRadius: raio.sm,
              padding: `${espaco.md}px ${espaco.lg}px`,
              cursor: "pointer",
              fontWeight: 700,
              fontSize: "1rem",
            }}
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={loading}
            style={{
              background: cores.sucesso,
              color: "white",
              border: "none",
              borderRadius: raio.sm,
              padding: `${espaco.md}px ${espaco.lg}px`,
              cursor: loading ? "not-allowed" : "pointer",
              fontWeight: 700,
              fontSize: "1rem",
              opacity: loading ? 0.5 : 1,
            }}
          >
            {loading ? "Criando..." : "Criar Sessão"}
          </button>
        </div>
      </form>
    </div>
  );
}
