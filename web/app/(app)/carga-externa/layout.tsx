"use client";

import { Separadores } from "@/components/layout/Separadores";

const TABS = [
  { href: "/carga-externa", label: "Visão geral" },
  { href: "/carga-externa/epoca", label: "Época" },
  { href: "/carga-externa/comparacao", label: "Comparar jogadores" },
  { href: "/carga-externa/posicao", label: "Por posição" },
  { href: "/carga-externa/tendencias", label: "Tendências" },
  { href: "/carga-externa/combinada", label: "Externa × Interna" },
  { href: "/carga-externa/velocidade", label: "Velocidade" },
];

/** Separadores da secção Carga externa (GPS). */
export default function CargaExternaLayout({ children }: { children: React.ReactNode }) {
  return (
    <div>
      <Separadores tabs={TABS} />
      {children}
    </div>
  );
}
