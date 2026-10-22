/** Idiomas da app. O texto do código está em português e serve de chave: em
 * inglês procura-se a tradução em ./en.ts (se faltar, mostra-se o português).
 * Variáveis entram como {0}, {1}…: tr("{0} atleta(s)", [n]). */
import { EN } from "./en";

export type Lingua = "pt" | "en";
export const LINGUAS: Lingua[] = ["pt", "en"];
export const COOKIE_LINGUA = "lm-lingua";

export type Tr = ((pt: string, vars?: (string | number | null | undefined)[]) => string) & {
  lingua: Lingua;
  /** Locale para números e datas (toLocaleString). */
  loc: string;
};

const normal = (s: string) => s.replace(/\s+/g, " ").trim();

export function traduzir(lingua: Lingua, pt: string, vars?: (string | number | null | undefined)[]): string {
  let s = pt;
  if (lingua === "en") {
    const chave = normal(pt);
    const en = EN[chave];
    if (en !== undefined) {
      // Mantém os espaços das pontas do original (texto colado a outros elementos).
      const ini = pt.match(/^\s*/)?.[0] ?? "";
      const fim = pt.match(/\s*$/)?.[0] ?? "";
      s = ini + en + fim;
    }
  }
  if (vars) vars.forEach((v, i) => { s = s.split(`{${i}}`).join(v == null ? "" : String(v)); });
  return s;
}

const cache = new Map<Lingua, Tr>();
export function criarTr(lingua: Lingua): Tr {
  let f = cache.get(lingua);
  if (!f) {
    f = Object.assign((pt: string, vars?: (string | number | null | undefined)[]) => traduzir(lingua, pt, vars), {
      lingua, loc: lingua === "en" ? "en-GB" : "pt-PT",
    }) as Tr;
    cache.set(lingua, f);
  }
  return f;
}

/** Idioma a partir do cookie ou, sem cookie, do Accept-Language do browser. */
export function escolherLingua(cookie: string | undefined | null, acceptLanguage: string | undefined | null): Lingua {
  if (cookie === "pt" || cookie === "en") return cookie;
  return (acceptLanguage ?? "").toLowerCase().trim().startsWith("pt") ? "pt" : "en";
}
