"use client";

import { useRouter } from "next/navigation";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { cores, raio } from "@/lib/theme";
import { useTr } from "@/lib/i18n/cliente";

export function JogadorSelector({
  jogadores,
  atual,
  basePath = "/jogadores",
  paramName = "nome",
  opcaoEquipa = false,
}: {
  jogadores: string[];
  atual: string | null;
  /** Página para onde navegar ao escolher — por omissão /jogadores. */
  basePath?: string;
  /** Nome do parâmetro de URL — por omissão "nome". */
  paramName?: string;
  /** Mostra uma opção extra "Equipa toda" que remove o parâmetro (em vez de escolher sempre um jogador). */
  opcaoEquipa?: boolean;
}) {
  const tr = useTr();
  const router = useRouter();
  const { oculto } = usePrivacidade();

  return (
    <select
      value={atual ?? ""}
      onChange={(e) => {
        const valor = e.target.value;
        router.push(valor ? `${basePath}?${paramName}=${encodeURIComponent(valor)}` : basePath);
      }}
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
      {opcaoEquipa && <option value="">{tr("Equipa toda")}</option>}
      {jogadores.map((j) => (
        <option key={j} value={j}>
          {nomeOuOculto(j, oculto)}
        </option>
      ))}
    </select>
  );
}
