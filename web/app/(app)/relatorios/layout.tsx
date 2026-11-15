"use client";

import { Separadores } from "@/components/layout/Separadores";

const TABS = [
  { href: "/relatorios/treino", label: "Treino" },
  { href: "/relatorios/jogo", label: "Jogo" },
  { href: "/relatorios/verificacao", label: "Verificação de dados" },
];

/** Separadores da secção Relatórios. */
export default function RelatoriosLayout({ children }: { children: React.ReactNode }) {
  return (
    <div>
      <div data-no-print><Separadores tabs={TABS} /></div>
      {children}
    </div>
  );
}
