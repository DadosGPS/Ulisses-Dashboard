"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { cores, raio } from "@/lib/theme";
import { useTr } from "@/lib/i18n/cliente";

const estilo: React.CSSProperties = {
  background: cores.bgCartao,
  border: `1px solid ${cores.bordaForte}`,
  borderRadius: raio.sm,
  color: cores.textoForte,
  padding: "8px 12px",
  fontSize: "0.85rem",
  fontWeight: 600,
  cursor: "pointer",
};

/** Seletor de jogador para a página Análise — preserva os restantes filtros
 * (microciclo, dia MD, comparar) na navegação. "Equipa toda" remove o filtro. */
export function JogadorAnaliseSelector({ jogadores, atual }: { jogadores: string[]; atual: string | null }) {
  const tr = useTr();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { oculto } = usePrivacidade();

  if (jogadores.length === 0) return null;

  function mudar(valor: string) {
    const params = new URLSearchParams(searchParams);
    if (valor) params.set("jogador", valor);
    else params.delete("jogador");
    router.push(`/analise?${params.toString()}`);
  }

  return (
    <select value={atual ?? ""} onChange={(e) => mudar(e.target.value)} style={estilo}>
      <option value="">{tr("Equipa toda")}</option>
      {jogadores.map((j) => (
        <option key={j} value={j}>
          {nomeOuOculto(j, oculto)}
        </option>
      ))}
    </select>
  );
}

/** Seletor "comparar com" — escolhe um segundo microciclo para comparar com o
 * selecionado. Exclui o microciclo atualmente selecionado. */
export function CompararMicrocicloSelector({
  opcoes,
  atual,
  microcicloSelecionado,
}: {
  opcoes: number[];
  atual: number | null;
  microcicloSelecionado: number | null;
}) {
  const tr = useTr();
  const router = useRouter();
  const searchParams = useSearchParams();

  if (opcoes.length < 2) return null;

  function mudar(valor: string) {
    const params = new URLSearchParams(searchParams);
    if (valor) params.set("comparar", valor);
    else params.delete("comparar");
    router.push(`/analise?${params.toString()}`);
  }

  return (
    <select value={atual ?? ""} onChange={(e) => mudar(e.target.value)} style={estilo} title={tr("Comparar com outro microciclo")}>
      <option value="">{tr("Comparar com…")}</option>
      {opcoes
        .filter((mc) => mc !== microcicloSelecionado)
        .map((mc) => (
          <option key={mc} value={mc}>
            {tr("vs Semana")}{" "}{mc}
          </option>
        ))}
    </select>
  );
}
