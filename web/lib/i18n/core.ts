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
  [/^(\d+) vs habitual (\d+) · \+(\d+)% \(varia ±(\d+)%\)$/, "$1 vs usual $2 · +$3% (varies ±$4%)"],
  [/^média dos (\S+) anteriores$/, "average of previous $1 sessions"],
  [/^Sessão mais recente · (\S+)$/, "Most recent session · $1"],
  [/^Semana (\d+) · total da semana$/, "Week $1 · weekly total"],
  [/^Semana (\d+)$/, "Week $1"],
  [/^Microciclo (\d+)$/, "Microcycle $1"],
  // Sugestões de calibração (decisoes_service.sugerir).
  [/^Mantido ou ignorado em (\d+) de (\d+) vezes, sem lesões nos (\d+) dias seguintes: experimentar (.+) de (\S+) para (\S+)\.$/,
    "Kept or dismissed $1 of $2 times, with no injuries in the next $3 days: try $4 from $5 to $6."],
  [/^(\d+) lesões nos (\d+) dias seguintes depois de o aviso ser mantido ou ignorado: manter (.+) em (\S+) e agir quando aparece\.$/,
    "$1 injuries in the $2 days after the warning was kept or dismissed: keep $3 at $4 and act when it appears."],
  // Ações sugeridas dos avisos (alertas_service).
  [/^Carga recente (\S+) UA\/dia vs habitual (\S+) UA\/dia: manter as próximas sessões abaixo do habitual até o rácio descer de (\S+)\.$/,
    "Recent load $1 AU/day vs usual $2 AU/day: keep the next sessions below usual until the ratio drops under $3."],
  [/^Incluir sprint a pelo menos (\S+) km\/h \((\S+)% do recorde de (\S+)\) na próxima sessão sem jogo no dia seguinte\.$/,
    "Include sprinting at $1 km/h or more ($2% of the $3 record) in the next session not followed by a match."],
  [/^Faltaram (\S+) m de (\S+) esta semana: incluir na próxima semana ou num treino compensatório\.$/,
    "$1 m of $2 was missing this week: add it next week or in a compensatory session."],
  [/^Faltam (\S+) m de (\S+) para a zona da semana: ~(\S+) m em cada um dos (\d+) treino\(s\) que costumam faltar\.$/,
    "$1 m of $2 missing for the weekly zone: ~$3 m in each of the $4 session(s) usually left."],
  [/^A semana já vai em (\S+)× o jogo \(máx\. (\S+)×\): retirar (\S+) das sessões que faltam \((\S+) m acima\)\.$/,
    "The week is already at $1× the match (max $2×): remove $3 from the remaining sessions ($4 m over)."],
  [/^Confirmar se os (\S+) de (\S+) \(habitual (\S+) num (\S+)\) foram planeados; vigiar o wellness e a PSE no dia seguinte\.$/,
    "Check whether the $1 of $2 (usual $3 on $4) was planned; watch wellness and RPE the next day."],
  [/^Falar com o jogador antes do treino — pior item: sono (\d)\/5 — e ajustar a sessão\.$/, "Talk to the player before training — worst item: sleep $1/5 — and adjust the session."],
  [/^Falar com o jogador antes do treino — pior item: dor muscular (\d)\/5 — e ajustar a sessão\.$/, "Talk to the player before training — worst item: muscle soreness $1/5 — and adjust the session."],
  [/^Falar com o jogador antes do treino — pior item: stress (\d)\/5 — e ajustar a sessão\.$/, "Talk to the player before training — worst item: stress $1/5 — and adjust the session."],
  [/^Falar com o jogador antes do treino — pior item: humor (\d)\/5 — e ajustar a sessão\.$/, "Talk to the player before training — worst item: mood $1/5 — and adjust the session."],
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
