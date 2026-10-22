"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { cores, raio } from "@/lib/theme";
import { useTr } from "@/lib/i18n/cliente";

export function DiaMdSelector({ opcoes, atual }: { opcoes: string[]; atual: string | null }) {
  const tr = useTr();
  const router = useRouter();
  const searchParams = useSearchParams();

  if (opcoes.length === 0) return null;

  function mudar(valor: string) {
    const params = new URLSearchParams(searchParams);
    if (valor) params.set("dia_md", valor);
    else params.delete("dia_md");
    router.push(`/analise?${params.toString()}`);
  }

  return (
    <select
      value={atual ?? ""}
      onChange={(e) => mudar(e.target.value)}
      style={{
        background: cores.bgCartao,
        border: `1px solid ${cores.bordaForte}`,
        borderRadius: raio.sm,
        color: cores.textoForte,
        padding: "8px 12px",
        fontSize: "0.85rem",
        fontWeight: 600,
        cursor: "pointer",
      }}
    >
      <option value="">{tr("Todos os dias")}</option>
      {opcoes.map((d) => (
        <option key={d} value={d}>
          {d}
        </option>
      ))}
    </select>
  );
}
