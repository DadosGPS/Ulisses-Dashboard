import { Suspense } from "react";
import { Separadores } from "@/components/layout/Separadores";

const TABS = [
  { href: "/hoje", label: "Para agir" },
  { href: "/hoje/prontidao", label: "Prontidão do plantel" },
];

/** O dia de hoje em duas vistas: o que fazer (exceções) e o estado de todos. */
export default function HojeLayout({ children }: { children: React.ReactNode }) {
  return (
    <div>
      <Suspense><Separadores tabs={TABS} /></Suspense>
      {children}
    </div>
  );
}
