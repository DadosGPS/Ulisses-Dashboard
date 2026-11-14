"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { cores, espaco } from "@/lib/theme";
import { useTr } from "@/lib/i18n/cliente";
import { localizar } from "@/components/layout/navegacao";

/** Separadores da área em que a página atual está (ver navegacao.tsx): uma
 * linha com as páginas da área e, se a página tiver subpáginas, uma segunda
 * linha mais discreta. Preservam os filtros (query params) ao trocar. */
export function SeparadoresArea() {
  const tr = useTr();
  const pathname = usePathname();
  const qs = useSearchParams().toString();
  const local = localizar(pathname);
  if (!local || local.area.separadores.length === 0) return null;
  const com = (href: string) => (qs ? `${href}?${qs}` : href);
  const sub = local.separador?.sub;

  return (
    <div data-no-print>
      <nav aria-label={tr(local.area.titulo)} style={{ display: "flex", gap: espaco.xs, flexWrap: "wrap", padding: `${espaco.md}px ${espaco.xxl}px 0`, borderBottom: `1px solid ${cores.borda}` }}>
        {local.area.separadores.map((s) => {
          const ativo = s === local.separador;
          return (
            <Link key={s.href} href={com(s.href)} aria-current={ativo ? "page" : undefined}
              style={{
                padding: `${espaco.sm}px ${espaco.md}px`, fontSize: "0.84rem", fontWeight: ativo ? 600 : 500,
                color: ativo ? cores.textoForte : cores.textoSuave,
                borderBottom: `2px solid ${ativo ? cores.acento : "transparent"}`, marginBottom: -1,
                textDecoration: "none", whiteSpace: "nowrap",
              }}>
              {tr(s.label)}
            </Link>
          );
        })}
      </nav>
      {sub && (
        <nav aria-label={tr(local.separador!.label)} style={{ display: "flex", gap: espaco.xs, flexWrap: "wrap", padding: `${espaco.sm}px ${espaco.xxl}px 0` }}>
          {sub.map((s) => {
            const ativo = pathname === s.href;
            return (
              <Link key={s.href} href={com(s.href)} aria-current={ativo ? "page" : undefined}
                style={{
                  padding: "4px 12px", fontSize: "0.78rem", fontWeight: ativo ? 600 : 500, borderRadius: 999,
                  color: ativo ? cores.textoForte : cores.textoSuave,
                  background: ativo ? cores.superficieHover : "transparent",
                  textDecoration: "none", whiteSpace: "nowrap",
                }}>
                {tr(s.label)}
              </Link>
            );
          })}
        </nav>
      )}
    </div>
  );
}
