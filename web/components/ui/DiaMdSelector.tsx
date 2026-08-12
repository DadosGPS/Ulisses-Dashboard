"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { cores, raio } from "@/lib/theme";

export function DiaMdSelector({ opcoes, atual }: { opcoes: string[]; atual: string | null }) {
  const router = useRouter();
  const searchParams = useSearchParams();

  if (opcoes.length === 0) return null;

  function mudar(valor: string) {
    const params = new URLSearchParams(searchParams);
    if (valor) params.set("dia_md", valor);
    else params.delete("dia_md");
    router.push(`/dashboard?${params.toString()}`);
  }

  return (
    <select
      value={atual ?? ""}
      onChange={(e) => mudar(e.target.value)}
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
      <option value="">Todos os dias</option>
      {opcoes.map((d) => (
        <option key={d} value={d}>
          {d}
        </option>
      ))}
    </select>
  );
}
