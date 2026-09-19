"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { cores, espaco, raio } from "@/lib/theme";

/** Seletor de jogador para os gráficos de evolução da Época. Sem seleção mostra
 * a média da equipa; com um jogador escolhido sobrepõe a evolução dele à média.
 * Preserva os restantes query params (ex: intervalo de semanas). */
export function SeletorJogadorEpoca({
  jogadores,
  jogador,
}: {
  jogadores: string[];
  jogador: string | null;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const { oculto } = usePrivacidade();

  if (jogadores.length === 0) return null;

  function aplicar(valor: string) {
    const p = new URLSearchParams(params.toString());
    if (valor) p.set("jogador", valor);
    else p.delete("jogador");
    const qs = p.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname);
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: espaco.sm }}>
      <span style={{ fontSize: "0.85rem", fontWeight: 600, color: cores.textoSuave }}>👤 Jogador:</span>
      <select
        value={jogador ?? ""}
        onChange={(e) => aplicar(e.target.value)}
        aria-label="Jogador"
        style={{
          background: cores.bgCartao,
          border: `1px solid ${cores.bordaForte}`,
          borderRadius: raio.sm,
          color: "white",
          padding: "7px 10px",
          fontSize: "0.8rem",
          fontWeight: 600,
          cursor: "pointer",
        }}
      >
        <option value="">Média da equipa</option>
        {jogadores.map((j) => (
          <option key={j} value={j}>
            {nomeOuOculto(j, oculto)}
          </option>
        ))}
      </select>
    </div>
  );
}
