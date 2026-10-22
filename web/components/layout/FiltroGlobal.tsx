"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { cores, espaco, raio } from "@/lib/theme";
import { useTr } from "@/lib/i18n/cliente";

type Filtro = "jogador" | "microciclo" | "dia_md";

/** Que filtros cada página aplica de facto — evita mostrar filtros decorativos.
 * A ordem das verificações vai do caminho mais específico para o mais geral. */
function aplicaveis(pathname: string): Filtro[] {
  if (
    pathname.startsWith("/analise/comparacao") ||
    pathname.startsWith("/analise/posicao") ||
    pathname.startsWith("/analise/combinada")
  ) {
    return ["microciclo", "dia_md"];
  }
  // A aba Época tem o seu próprio seletor de intervalo de microciclos.
  if (pathname.startsWith("/analise/epoca")) return [];
  // /carga-externa tem a sua própria barra de filtros (FiltrosCargaExterna),
  // que junta tipo/posição a jogador/microciclo/dia — por isso a barra global
  // não aparece lá, para não haver dois conjuntos de filtros a confundir.
  if (
    pathname.startsWith("/analise") || // inclui /analise e /analise/tendencias
    pathname.startsWith("/jogadores")
  ) {
    return ["jogador", "microciclo", "dia_md"];
  }
  return [];
}

/** Barra de filtros partilhada — escreve a escolha nos query params
 * (jogador/microciclo/dia_md), preservando a rota, de modo que a seleção se
 * mantém ao navegar. Mostra apenas os filtros que a página atual aplica. */
export function FiltroGlobal({
  jogadores,
  microciclos,
  diasMd,
}: {
  jogadores: string[];
  microciclos: number[];
  diasMd: string[];
}) {
  const tr = useTr();
  const pathname = usePathname();
  const router = useRouter();
  const params = useSearchParams();
  const { oculto } = usePrivacidade();

  const quais = aplicaveis(pathname);
  if (quais.length === 0) return null;

  const jogador = params.get("jogador");
  const microciclo = params.get("microciclo");
  const diaMd = params.get("dia_md");

  function aplicar(chave: string, valor: string) {
    const p = new URLSearchParams(params.toString());
    if (valor) p.set(chave, valor);
    else p.delete(chave);
    const qs = p.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname);
  }

  const ativos = quais.filter((q) => (q === "jogador" ? jogador : q === "microciclo" ? microciclo : diaMd));

  const limpar = () => {
    const p = new URLSearchParams(params.toString());
    quais.forEach((q) => p.delete(q));
    const qs = p.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname);
  };

  return (
    <BarraFiltros nAtivos={ativos.length} onLimpar={limpar}>
      {quais.includes("jogador") && (
        <select value={jogador ?? ""} onChange={(e) => aplicar("jogador", e.target.value)} style={seletor(!!jogador)} aria-label={tr("Jogador")}>
          <option value="">{tr("Equipa toda")}</option>
          {jogadores.map((j) => (
            <option key={j} value={j}>{nomeOuOculto(j, oculto)}</option>
          ))}
        </select>
      )}

      {quais.includes("microciclo") && microciclos.length > 0 && (
        <select value={microciclo ?? ""} onChange={(e) => aplicar("microciclo", e.target.value)} style={seletor(!!microciclo)} aria-label={tr("Microciclo")}>
          <option value="">{tr("Todos os microciclos")}</option>
          {microciclos.map((m) => (
            <option key={m} value={m}>{tr("Semana")}{" "}{m}</option>
          ))}
        </select>
      )}

      {quais.includes("dia_md") && diasMd.length > 0 && (
        <select value={diaMd ?? ""} onChange={(e) => aplicar("dia_md", e.target.value)} style={seletor(!!diaMd)} aria-label={tr("Dia MD")}>
          <option value="">{tr("Todos os dias")}</option>
          {diasMd.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      )}
    </BarraFiltros>
  );
}

/** Barra de filtros por cima do cabeçalho da página — a mesma em todas as
 * páginas. Os filtros escolhidos ficam realçados; «Limpar» aparece quando há algum. */
export function BarraFiltros({ children, nAtivos, onLimpar }: { children: React.ReactNode; nAtivos: number; onLimpar: () => void }) {
  const tr = useTr();
  return (
    <div
      data-no-print
      style={{
        position: "sticky", top: 0, zIndex: 20, display: "flex", alignItems: "center", gap: espaco.sm, flexWrap: "wrap",
        padding: `${espaco.sm}px ${espaco.xxl}px`, background: cores.bgElevado, borderBottom: `1px solid ${cores.borda}`,
      }}
    >
      <span style={{ fontSize: "0.68rem", textTransform: "uppercase", letterSpacing: "0.06em", color: cores.textoFraco, fontWeight: 700, marginRight: 4 }}>
        {tr("Filtros")}</span>
      {children}
      {nAtivos > 0 && (
        <span style={{ display: "inline-flex", alignItems: "center", gap: espaco.sm, marginLeft: 4 }}>
          <span style={{ fontSize: "0.74rem", color: cores.textoSuave }}>{tr("{0} ativo(s)", [nAtivos])}</span>
          <button onClick={onLimpar} style={{ background: "transparent", border: "none", color: cores.acento, fontSize: "0.75rem", cursor: "pointer", fontWeight: 600, padding: 0 }}>
            {tr("Limpar")}</button>
        </span>
      )}
    </div>
  );
}

/** Seletor da barra de filtros; realçado quando tem um valor escolhido. */
export function seletor(ativo: boolean): React.CSSProperties {
  return {
    background: ativo ? `color-mix(in srgb, ${cores.acento} 14%, ${cores.bgCartao})` : cores.bgCartao,
    border: `1px solid ${ativo ? cores.acento : cores.borda}`,
    borderRadius: raio.sm,
    color: ativo ? cores.textoForte : cores.textoSuave,
    padding: "5px 9px",
    fontSize: "0.79rem",
    fontWeight: ativo ? 600 : 500,
    cursor: "pointer",
  };
}
