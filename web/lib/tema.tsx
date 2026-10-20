"use client";

import { useEffect, useState } from "react";

import { CHAVE_TEMA } from "@/lib/tema-config";

export type Tema = "dark" | "light";

/** Tema atual (atributo data-theme do <html>), atualizado quando muda. */
export function useTema(): Tema {
  const [tema, setTema] = useState<Tema>("dark");
  useEffect(() => {
    const ler = () => setTema(document.documentElement.dataset.theme === "light" ? "light" : "dark");
    ler();
    const obs = new MutationObserver(ler);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => obs.disconnect();
  }, []);
  return tema;
}

export function definirTema(tema: Tema) {
  document.documentElement.dataset.theme = tema;
  try {
    localStorage.setItem(CHAVE_TEMA, tema);
  } catch {
    /* modo privado / armazenamento bloqueado: o tema vale só para esta visita */
  }
}

/** Converte valores com var(--…) em cores reais (o Plotly não lê variáveis
 * CSS). Percorre objetos/arrays e devolve uma cópia. */
export function resolverCores<T>(valor: T): T {
  if (typeof document === "undefined") return valor;
  const sonda = document.createElement("span");
  sonda.style.display = "none";
  document.body.appendChild(sonda);
  const cache = new Map<string, string>();
  const resolver = (v: unknown): unknown => {
    if (typeof v === "string" && v.includes("var(")) {
      if (!cache.has(v)) {
        sonda.style.color = "";
        sonda.style.color = v;
        cache.set(v, getComputedStyle(sonda).color || v);
      }
      return cache.get(v);
    }
    if (Array.isArray(v)) return v.map(resolver);
    if (v && typeof v === "object") {
      return Object.fromEntries(Object.entries(v as Record<string, unknown>).map(([k, x]) => [k, resolver(x)]));
    }
    return v;
  };
  try {
    return resolver(valor) as T;
  } finally {
    sonda.remove();
  }
}
