import { Suspense } from "react";
import { Separadores } from "@/components/layout/Separadores";

const TABS = [
  { href: "/planeamento/calendario", label: "Calendário" },
  { href: "/planeamento/epoca", label: "Época e microciclos" },
  { href: "/planeamento/semana", label: "Semana por jogador" },
  { href: "/planeamento/exercicios", label: "Exercícios" },
];

/** Separadores de Planear (Calendário, Época e microciclos, Semana, Exercícios). */
export default function PlaneamentoLayout({ children }: { children: React.ReactNode }) {
  return (
    <div>
      <Suspense>
        <Separadores tabs={TABS} />
      </Suspense>
      {children}
    </div>
  );
}
