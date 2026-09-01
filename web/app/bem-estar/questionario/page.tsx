"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { cores, espaco, raio } from "@/lib/theme";

interface WellnessData {
  sleep: number;
  fatigue: number;
  stress: number;
  soreness: number;
  mood: number;
  notes: string;
}

export default function WellnessQuestionnaireePage() {
  const router = useRouter();
  const [wellness, setWellness] = useState<WellnessData>({
    sleep: 3,
    fatigue: 3,
    stress: 3,
    soreness: 3,
    mood: 3,
    notes: "",
  });
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const metrics = [
    { key: "sleep", label: "Qualidade do Sono", emoji: "😴" },
    { key: "fatigue", label: "Fadiga", emoji: "😫" },
    { key: "stress", label: "Stress", emoji: "😰" },
    { key: "soreness", label: "Dor Muscular", emoji: "💪" },
    { key: "mood", label: "Humor", emoji: "😊" },
  ];

  const totalScore =
    (wellness.sleep +
      wellness.fatigue +
      wellness.stress +
      wellness.soreness +
      wellness.mood) /
    5;

  async function handleSubmit() {
    setLoading(true);
    try {
      // TODO: Call API to save wellness data
      // For now, just simulate
      await new Promise((resolve) => setTimeout(resolve, 1000));
      setSubmitted(true);
      setTimeout(() => router.push("/dashboard"), 2000);
    } catch (error) {
      console.error("Error submitting wellness:", error);
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: cores.bg,
          padding: espaco.xl,
        }}
      >
        <div
          style={{
            textAlign: "center",
            background: cores.bgElevado,
            border: `1px solid ${cores.borda}`,
            borderRadius: raio.md,
            padding: espaco.xxl,
          }}
        >
          <div style={{ fontSize: "3rem", marginBottom: espaco.lg }}>
            ✅
          </div>
          <h2
            style={{
              fontSize: "1.5rem",
              fontWeight: 700,
              color: cores.sucesso,
              marginBottom: espaco.md,
            }}
          >
            Obrigado!
          </h2>
          <p
            style={{
              color: cores.textoSuave,
              fontSize: "1rem",
              marginBottom: espaco.lg,
            }}
          >
            Bem-estar registado com sucesso.
          </p>
          <p style={{ color: cores.textoSuave, fontSize: "0.875rem" }}>
            Será redirecionado em breve...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        background: cores.bg,
        padding: espaco.lg,
      }}
    >
      {/* Header */}
      <div
        style={{
          maxWidth: 600,
          margin: "0 auto",
          marginBottom: espaco.xl,
          textAlign: "center",
        }}
      >
        <h1
          style={{
            fontSize: "1.75rem",
            fontWeight: 700,
            color: "white",
            marginBottom: espaco.md,
          }}
        >
          Questionário de Bem-Estar
        </h1>
        <p style={{ fontSize: "1rem", color: cores.textoSuave }}>
          Como se sente hoje? (1 = Muito Mau | 5 = Excelente)
        </p>
      </div>

      {/* Metrics */}
      <div
        style={{
          maxWidth: 600,
          margin: "0 auto",
          marginBottom: espaco.xl,
        }}
      >
        {metrics.map((metric) => (
          <div
            key={metric.key}
            style={{
              background: cores.bgElevado,
              border: `1px solid ${cores.borda}`,
              borderRadius: raio.md,
              padding: espaco.lg,
              marginBottom: espaco.lg,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: espaco.md,
                marginBottom: espaco.md,
              }}
            >
              <span style={{ fontSize: "2rem" }}>{metric.emoji}</span>
              <div>
                <h3
                  style={{
                    fontSize: "1.125rem",
                    fontWeight: 700,
                    color: "white",
                  }}
                >
                  {metric.label}
                </h3>
              </div>
              <div
                style={{
                  marginLeft: "auto",
                  fontSize: "1.5rem",
                  fontWeight: 700,
                  color: cores.destaque,
                }}
              >
                {wellness[metric.key as keyof WellnessData]}/5
              </div>
            </div>

            {/* Slider */}
            <input
              type="range"
              min="1"
              max="5"
              step="1"
              value={wellness[metric.key as keyof WellnessData]}
              onChange={(e) =>
                setWellness({
                  ...wellness,
                  [metric.key]: parseInt(e.currentTarget.value),
                })
              }
              style={{
                width: "100%",
                height: 8,
                borderRadius: 4,
                background: cores.bg,
                outline: "none",
                WebkitAppearance: "none",
              }}
            />

            {/* Value indicators */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginTop: espaco.sm,
                fontSize: "0.75rem",
                color: cores.textoSuave,
              }}
            >
              <span>Muito Mau</span>
              <span>Mau</span>
              <span>Normal</span>
              <span>Bom</span>
              <span>Excelente</span>
            </div>
          </div>
        ))}
      </div>

      {/* Notes */}
      <div
        style={{
          maxWidth: 600,
          margin: "0 auto",
          marginBottom: espaco.xl,
        }}
      >
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
              marginBottom: espaco.md,
            }}
          >
            Notas Adicionais (Opcional)
          </h3>
          <textarea
            value={wellness.notes}
            onChange={(e) =>
              setWellness({ ...wellness, notes: e.currentTarget.value })
            }
            placeholder="Alguma observação que queira adicionar?"
            style={{
              width: "100%",
              minHeight: 100,
              padding: espaco.md,
              borderRadius: raio.sm,
              background: cores.bg,
              border: `1px solid ${cores.borda}`,
              color: "white",
              fontSize: "1rem",
              fontFamily: "inherit",
              resize: "none",
            }}
          />
        </div>
      </div>

      {/* Score Summary */}
      <div
        style={{
          maxWidth: 600,
          margin: "0 auto",
          marginBottom: espaco.xl,
        }}
      >
        <div
          style={{
            background:
              totalScore >= 4
                ? "rgba(34,197,94,0.12)"
                : totalScore >= 3
                ? "rgba(234,179,8,0.12)"
                : "rgba(239,68,68,0.12)",
            border: `1px solid ${
              totalScore >= 4
                ? cores.sucesso
                : totalScore >= 3
                ? cores.atencao
                : cores.cargaInterna
            }`,
            borderRadius: raio.md,
            padding: espaco.lg,
            textAlign: "center",
          }}
        >
          <div
            style={{
              fontSize: "0.875rem",
              color: cores.textoSuave,
              marginBottom: espaco.sm,
            }}
          >
            Bem-estar Geral
          </div>
          <div
            style={{
              fontSize: "2.5rem",
              fontWeight: 700,
              color:
                totalScore >= 4
                  ? cores.sucesso
                  : totalScore >= 3
                  ? cores.atencao
                  : cores.cargaInterna,
              marginBottom: espaco.sm,
            }}
          >
            {totalScore.toFixed(1)}/5
          </div>
          <div
            style={{
              fontSize: "0.875rem",
              color: cores.textoSuave,
            }}
          >
            {totalScore >= 4 && "Excelente estado"}
            {totalScore >= 3 && totalScore < 4 && "Estado normal"}
            {totalScore < 3 && "Necessário descanso"}
          </div>
        </div>
      </div>

      {/* Submit Button */}
      <div
        style={{
          maxWidth: 600,
          margin: "0 auto",
        }}
      >
        <button
          onClick={handleSubmit}
          disabled={loading}
          style={{
            width: "100%",
            padding: `${espaco.lg}px ${espaco.xl}px`,
            borderRadius: raio.md,
            background: cores.sucesso,
            color: "white",
            border: "none",
            fontSize: "1.125rem",
            fontWeight: 700,
            cursor: loading ? "not-allowed" : "pointer",
            transition: "all 0.2s",
            opacity: loading ? 0.7 : 1,
          }}
          onMouseEnter={(e) => {
            if (!loading) {
              (e.currentTarget as HTMLElement).style.opacity = "0.9";
            }
          }}
          onMouseLeave={(e) => {
            if (!loading) {
              (e.currentTarget as HTMLElement).style.opacity = "1";
            }
          }}
        >
          {loading ? "Enviando..." : "Enviar Bem-Estar"}
        </button>
      </div>

      <style>{`
        input[type="range"]::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          width: 24px;
          height: 24px;
          border-radius: 50%;
          background: ${cores.cargaInterna};
          cursor: pointer;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        }
        input[type="range"]::-moz-range-thumb {
          width: 24px;
          height: 24px;
          border-radius: 50%;
          background: ${cores.cargaInterna};
          cursor: pointer;
          border: none;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        }
      `}</style>
    </div>
  );
}
