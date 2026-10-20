import { Suspense } from "react";
import { Separadores } from "@/components/layout/Separadores";

const TABS = [
  { href: "/planeamento", label: "Microciclos" },
  { href: "/planeamento/sessoes", label: "Sessões" },
  { href: "/planeamento/treino-jogo", label: "Treino vs jogo" },
  { href: "/planeamento/benchmark", label: "Match Benchmark" },
];

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
