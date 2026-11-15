"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { cores, raio } from "@/lib/theme";
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
            style={{ padding: "5px 10px", borderRadius: 6, fontSize: "0.76rem", fontWeight: 600, textDecoration: "none",
              background: ativo ? cores.perigo : "transparent", color: ativo ? "#fff" : cores.textoSuave }}>
            {tr(rot)}
          </Link>
        );
      })}
    </div>
  );
}
