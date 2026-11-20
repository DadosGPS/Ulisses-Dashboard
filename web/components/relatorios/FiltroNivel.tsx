"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { cores, raio, letra } from "@/lib/theme";
import { useTr } from "@/lib/i18n/cliente";

const OPCOES = [
  ["erros_avisos", "Erros + avisos"], ["erros", "Erros"], ["avisos", "Avisos"], ["info", "Info"], ["todos", "Todos"],
] as const;

/** Filtro de nível da lista de problemas (muda ?nivel=). */
export function FiltroNivel({ atual }: { atual: string }) {
  const tr = useTr();
  const pathname = usePathname();
  const params = useSearchParams();
  return (
    <div style={{ display: "flex", gap: 2, background: cores.superficie, borderRadius: raio.sm, padding: 2 }}>
      {OPCOES.map(([v, rot]) => {
        const q = new URLSearchParams(params.toString());
        q.set("nivel", v);
        const ativo = v === atual;
        return (
          <Link key={v} href={`${pathname}?${q.toString()}`} scroll={false}
            style={{ padding: "6px 12px", borderRadius: 6, fontSize: letra.pequeno, fontWeight: 600, textDecoration: "none",
              background: ativo ? cores.perigo : "transparent", color: ativo ? "#fff" : cores.textoSuave }}>
            {tr(rot)}
          </Link>
        );
      })}
    </div>
  );
}
