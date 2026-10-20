"use client";

import { Separadores } from "@/components/layout/Separadores";

const TABS = [
  { href: "/analise", label: "Visão geral" },
  { href: "/analise/epoca", label: "Época" },
  { href: "/analise/comparacao", label: "Comparar jogadores" },
  { href: "/analise/posicao", label: "Por posição" },
  { href: "/analise/tendencias", label: "Tendências" },
  { href: "/analise/combinada", label: "Externa × Interna" },
];

/** Separadores da secção Análise. */
export default function AnaliseLayout({ children }: { children: React.ReactNode }) {
  return (
    <div>
      <Separadores tabs={TABS} />
      {children}
    </div>
  );
}
