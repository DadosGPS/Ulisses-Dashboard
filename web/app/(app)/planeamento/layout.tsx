import { Suspense } from "react";
import { Separadores } from "@/components/layout/Separadores";

const TABS = [
  { href: "/planeamento", label: "Microciclos" },
  { href: "/planeamento/epoca", label: "Época" },
  { href: "/planeamento/exercicios", label: "Exercícios" },
];

/** Separadores do Planeamento. */
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
