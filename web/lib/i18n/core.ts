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
// Índice pelas chaves normalizadas (sem espaços nas pontas): os espaços das
// pontas vêm sempre do texto original.
const INDICE: Record<string, string> = Object.fromEntries(Object.entries(EN).map(([k, v]) => [normal(k), v.trim()]));

/** Textos que chegam da API com números lá dentro (ex.: "Hooper 17 (+4,8 vs
 * média)"). Usados quando não há tradução exata no dicionário. */
const PADROES_EN: [RegExp, string][] = [
  [/^Hooper (\S+) \((\S+) vs média\)$/, "Hooper $1 ($2 vs average)"],
  [/^CMJ (\S+)% vs média própria \((\S+) vs (\S+) cm\)$/, "CMJ $1% vs own average ($2 vs $3 cm)"],
  [/^baseline de (\d+) dias$/, "$1-day baseline"],
  [/^Semana (\d+) · total da semana$/, "Week $1 · weekly total"],
  [/^Semana (\d+)$/, "Week $1"],
  [/^Microciclo (\d+)$/, "Microcycle $1"],
];

export function traduzir(lingua: Lingua, pt: string, vars?: (string | number | null | undefined)[]): string {
  let s = pt;
  if (lingua === "en") {
    const chave = normal(pt);
    const en = INDICE[chave];
    const enPadrao = en === undefined ? PADROES_EN.find(([re]) => re.test(chave)) : undefined;
    if (en === undefined && enPadrao) {
      s = pt.replace(chave, chave.replace(enPadrao[0], enPadrao[1]));
    } else if (en !== undefined) {
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
