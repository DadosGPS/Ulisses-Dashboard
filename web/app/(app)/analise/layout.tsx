"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { cores, espaco } from "@/lib/theme";

const TABS = [
  { href: "/analise", label: "Visão geral" },
  { href: "/analise/comparacao", label: "Comparar jogadores" },
  { href: "/analise/posicao", label: "Por posição" },
  { href: "/analise/tendencias", label: "Tendências" },
  { href: "/analise/combinada", label: "Externa × Interna" },
];

/** Separadores da secção Análise — tornam as sub-páginas acessíveis e
 * preservam os filtros globais (query params) ao trocar de separador. */
export default function AnaliseLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const params = useSearchParams();
  const qs = params.toString();

  return (
    <div>
      <nav
        style={{
          display: "flex",
          gap: espaco.xs,
          flexWrap: "wrap",
          padding: `${espaco.md}px ${espaco.xxl}px 0`,
          borderBottom: `1px solid ${cores.borda}`,
          background: cores.bgElevado,
        }}
      >
        {TABS.map((t) => {
          const ativo = pathname === t.href;
          return (
            <Link
              key={t.href}
              href={qs ? `${t.href}?${qs}` : t.href}
              style={{
                padding: `${espaco.sm}px ${espaco.md}px`,
                fontSize: "0.84rem",
                fontWeight: ativo ? 700 : 500,
                color: ativo ? "white" : cores.textoSuave,
                borderBottom: `2px solid ${ativo ? cores.destaque : "transparent"}`,
                textDecoration: "none",
                whiteSpace: "nowrap",
              }}
            >
              {t.label}
            </Link>
          );
        })}
      </nav>
      {children}
    </div>
  );
}
