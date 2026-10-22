"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cores, espaco } from "@/lib/theme";
import { useTr } from "@/lib/i18n/cliente";

/** Subpáginas de cada equipa da academia. */
export function NavEquipa({ teamId }: { teamId: string }) {
  const tr = useTr();
  const pathname = usePathname();
  const base = `/academia/equipa/${teamId}`;
  const tabs = [
    { href: base, label: tr("Testes") },
    { href: `${base}/jogos`, label: tr("Jogos") },
    { href: `${base}/relatorio`, label: tr("Relatórios T1–T4") },
  ];
  return (
    <nav data-no-print style={{ display: "flex", gap: espaco.xs, padding: `0 ${espaco.xxl}px`, borderBottom: `1px solid ${cores.borda}` }}>
      {tabs.map((t) => {
        const ativo = pathname === t.href;
        return (
          <Link key={t.href} href={t.href} style={{
            padding: `${espaco.sm}px ${espaco.md}px`, fontSize: "0.82rem", fontWeight: ativo ? 600 : 500,
            color: ativo ? cores.textoForte : cores.textoSuave, borderBottom: `2px solid ${ativo ? cores.acento : "transparent"}`,
            marginBottom: -1, textDecoration: "none",
          }}>{tr(t.label)}</Link>
        );
      })}
    </nav>
  );
}
