"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { COOKIE_EQUIPA, definirEquipaAtiva } from "@/lib/equipa-ativa";
import { useStore } from "@/lib/store";
import { cores, espaco } from "@/lib/theme";
import { useTr } from "@/lib/i18n/cliente";

/** Subpáginas de cada equipa da academia. */
export function NavEquipa({ teamId }: { teamId: string }) {
  const tr = useTr();
  const pathname = usePathname();
  const router = useRouter();
  const setUser = useStore((s) => s.setUser);
  // Uma só equipa ativa: abrir uma equipa da Academia torna-a a equipa ativa
  // da app (seletor do menu, Hoje, Análise…), para nunca haver duas escolhas.
  useEffect(() => {
    const m = document.cookie.match(new RegExp(`(?:^|; )${COOKIE_EQUIPA}=([^;]+)`));
    if (!m || decodeURIComponent(m[1]) !== teamId) {
      definirEquipaAtiva(teamId);
      setUser({ teamId });
      router.refresh();
    }
  }, [teamId, router, setUser]);
  const base = `/academia/equipa/${teamId}`;
  const tabs = [
    { href: base, label: tr("Resultados T1–T4") },
    { href: `${base}/testes`, label: tr("Registar testes") },
    { href: `${base}/jogos`, label: tr("Jogos") },
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
