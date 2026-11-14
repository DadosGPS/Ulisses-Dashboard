import {
  IconBarChart,
  IconCheckCircle,
  IconClipboard,
  IconPlus,
  IconSettings,
  IconUpload,
  IconUser,
  IconUsers,
} from "@/components/icons/Icons";

/** Navegação da app — fonte única para o menu lateral, os separadores de cada
 * área e a pesquisa (Ctrl+K).
 *
 * O menu lateral tem uma entrada por ÁREA (o que o preparador físico está a
 * fazer); as páginas de cada área são separadores no topo. Uma página com
 * `sub` mostra uma segunda linha de separadores (ex.: Planeamento).
 *
 * `prefixo`: o separador fica ativo também nas subpáginas (ex.: /jogadores/123).
 */
export type SubSeparador = { href: string; label: string };
export type Separador = { href: string; label: string; prefixo?: boolean; sub?: SubSeparador[] };
export type Area = {
  id: string;
  titulo: string;
  Icon: (p: { size?: number }) => React.ReactElement;
  /** Vazio = a área tem os seus próprios separadores (Academia). */
  separadores: Separador[];
  /** Caminho base de uma área sem separadores definidos aqui. */
  href?: string;
};

export const AREAS: Area[] = [
  { id: "hoje", titulo: "Hoje", Icon: IconCheckCircle, separadores: [
    { href: "/hoje", label: "Hoje" },
    { href: "/dashboard", label: "Centro de Controlo" },
    { href: "/prontidao", label: "Prontidão" },
    { href: "/mensagens", label: "Mensagens aos Jogadores" },
  ] },
  { id: "semana", titulo: "Semana", Icon: IconClipboard, separadores: [
    { href: "/planeamento", label: "Planeamento", sub: [
      { href: "/planeamento", label: "Microciclos" },
      { href: "/planeamento/semana", label: "Semana por jogador" },
      { href: "/planeamento/epoca", label: "Época" },
      { href: "/planeamento/exercicios", label: "Exercícios" },
    ] },
    { href: "/calendario", label: "Calendário" },
    { href: "/carga-externa", label: "Carga Externa" },
    { href: "/analise", label: "Carga Interna" },
    { href: "/forca", label: "Força e Ginásio" },
  ] },
  { id: "jogadores", titulo: "Jogadores", Icon: IconUser, separadores: [
    { href: "/jogadores", label: "Ficha do jogador", prefixo: true },
    { href: "/analise/tendencias", label: "Tendências" },
    { href: "/velocidade", label: "Limiares de Velocidade" },
    { href: "/perfil", label: "Testes" },
  ] },
  { id: "analise", titulo: "Análise", Icon: IconBarChart, separadores: [
    { href: "/analise/epoca", label: "Época" },
    { href: "/analise/comparacao", label: "Comparar", sub: [
      { href: "/analise/comparacao", label: "Jogadores" },
      { href: "/analise/posicao", label: "Posições" },
    ] },
    { href: "/analise/combinada", label: "Externa × Interna" },
  ] },
  { id: "saude", titulo: "Saúde", Icon: IconPlus, separadores: [
    { href: "/lesoes", label: "Lesões" },
    { href: "/regresso", label: "Regresso ao Jogo" },
  ] },
  { id: "academia", titulo: "Academia", Icon: IconUsers, href: "/academia", separadores: [] },
];

/** Atalhos fixos no fundo do menu (não são áreas de trabalho). */
export const UTILITARIOS: { href: string; label: string; Icon: (p: { size?: number }) => React.ReactElement }[] = [
  { href: "/upload", label: "Importar GPS", Icon: IconUpload },
  { href: "/configuracoes", label: "Definições", Icon: IconSettings },
];

export const hrefArea = (a: Area) => a.href ?? a.separadores[0]?.href ?? "/";

const caminhos = (s: Separador) => [s.href, ...(s.sub ?? []).map((x) => x.href)];

/** O separador (e a área) a que um caminho pertence. Ganha a correspondência
 * exata; depois o prefixo mais comprido (ex.: /jogadores/123 → Ficha). */
export function localizar(pathname: string): { area: Area; separador: Separador | null } | null {
  let melhor: { area: Area; separador: Separador | null; n: number } | null = null;
  for (const area of AREAS) {
    if (area.href && (pathname === area.href || pathname.startsWith(`${area.href}/`))) {
      if (!melhor || area.href.length > melhor.n) melhor = { area, separador: null, n: area.href.length };
    }
    for (const separador of area.separadores) {
      for (const c of caminhos(separador)) {
        if (pathname === c) return { area, separador };
        if (separador.prefixo && pathname.startsWith(`${c}/`) && (!melhor || c.length > melhor.n)) {
          melhor = { area, separador, n: c.length };
        }
      }
    }
  }
  return melhor ? { area: melhor.area, separador: melhor.separador } : null;
}
