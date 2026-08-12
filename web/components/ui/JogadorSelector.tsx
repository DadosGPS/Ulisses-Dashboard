"use client";

import { useRouter } from "next/navigation";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { cores, raio } from "@/lib/theme";

export function JogadorSelector({ jogadores, atual }: { jogadores: string[]; atual: string | null }) {
  const router = useRouter();
  const { oculto } = usePrivacidade();

  return (
    <select
      value={atual ?? ""}
      onChange={(e) => router.push(`/jogadores?nome=${encodeURIComponent(e.target.value)}`)}
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
      {jogadores.map((j) => (
        <option key={j} value={j}>
          {nomeOuOculto(j, oculto)}
        </option>
      ))}
    </select>
  );
}
