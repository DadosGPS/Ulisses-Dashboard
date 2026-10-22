"use client";

import { createContext, useContext } from "react";
import { COOKIE_LINGUA, criarTr, type Lingua, type Tr } from "./core";

const Contexto = createContext<Lingua>("pt");

export function LinguaProvider({ lingua, children }: { lingua: Lingua; children: React.ReactNode }) {
  return <Contexto.Provider value={lingua}>{children}</Contexto.Provider>;
}

/** Tradutor para componentes do browser: const tr = useTr(); tr("Guardar"). */
export function useTr(): Tr {
  return criarTr(useContext(Contexto));
}

/** Muda o idioma (guarda no cookie e recarrega para o servidor também mudar). */
export function mudarLingua(l: Lingua) {
  document.cookie = `${COOKIE_LINGUA}=${l}; path=/; max-age=${60 * 60 * 24 * 365}; samesite=lax`;
  window.location.reload();
}

/** Idioma atual fora de componentes (ex.: cabeçalho dos pedidos à API). */
export function linguaDoCookie(): Lingua {
  if (typeof document === "undefined") return "pt";
  const m = document.cookie.match(new RegExp(`(?:^|; )${COOKIE_LINGUA}=(pt|en)`));
  if (m) return m[1] as Lingua;
  return (navigator.language || "").toLowerCase().startsWith("pt") ? "pt" : "en";
}
