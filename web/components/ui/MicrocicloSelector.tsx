"use client";

import { useRouter } from "next/navigation";
import { cores, raio } from "@/lib/theme";

export function MicrocicloSelector({ opcoes, atual }: { opcoes: number[]; atual: number | null }) {
  const router = useRouter();

  if (opcoes.length === 0) return null;

  return (
    <select
      value={atual ?? ""}
      onChange={(e) => router.push(`/dashboard?microciclo=${encodeURIComponent(e.target.value)}`)}
      style={{
        background: cores.bgCartao,
        border: `1px solid ${cores.bordaForte}`,
        borderRadius: raio.sm,
        color: "white",
        padding: "8px 12px",
        fontSize: "0.85rem",
        fontWeight: 600,
        cursor: "pointer",
      }}
    >
      {opcoes.map((mc) => (
        <option key={mc} value={mc}>
          Semana {mc}
        </option>
      ))}
    </select>
  );
}
