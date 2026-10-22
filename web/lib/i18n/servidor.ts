import { cookies, headers } from "next/headers";
import { COOKIE_LINGUA, criarTr, escolherLingua, type Lingua, type Tr } from "./core";

export async function obterLingua(): Promise<Lingua> {
  const [c, h] = await Promise.all([cookies(), headers()]);
  return escolherLingua(c.get(COOKIE_LINGUA)?.value, h.get("accept-language"));
}

/** Tradutor para páginas do servidor: const tr = await obterTr(). */
export async function obterTr(): Promise<Tr> {
  return criarTr(await obterLingua());
}
