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

  return (
    <div
      data-no-print
      style={{
        position: "sticky",
        top: 0,
        zIndex: 20,
        display: "flex",
        alignItems: "center",
        gap: espaco.sm,
        flexWrap: "wrap",
        padding: `${espaco.sm}px ${espaco.xxl}px`,
        background: cores.bgElevado,
        borderBottom: `1px solid ${cores.borda}`,
      }}
    >
      <span style={{ fontSize: "0.68rem", textTransform: "uppercase", letterSpacing: "0.06em", color: cores.textoFraco, fontWeight: 700, marginRight: 4 }}>
        {tr("Filtros")}</span>

      {quais.includes("jogador") && (
        <select value={jogador ?? ""} onChange={(e) => aplicar("jogador", e.target.value)} style={sel} aria-label={tr("Jogador")}>
          <option value="">{tr("Equipa toda")}</option>
          {jogadores.map((j) => (
            <option key={j} value={j}>{nomeOuOculto(j, oculto)}</option>
          ))}
        </select>
      )}

      {quais.includes("microciclo") && microciclos.length > 0 && (
        <select value={microciclo ?? ""} onChange={(e) => aplicar("microciclo", e.target.value)} style={sel} aria-label={tr("Microciclo")}>
          <option value="">{tr("Todos os microciclos")}</option>
          {microciclos.map((m) => (
            <option key={m} value={m}>{tr("Semana")}{" "}{m}</option>
          ))}
        </select>
      )}

      {quais.includes("dia_md") && diasMd.length > 0 && (
        <select value={diaMd ?? ""} onChange={(e) => aplicar("dia_md", e.target.value)} style={sel} aria-label={tr("Dia MD")}>
          <option value="">{tr("Todos os dias")}</option>
          {diasMd.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      )}

      {ativos.length > 0 && (
        <button
          onClick={() => {
            const p = new URLSearchParams(params.toString());
            quais.forEach((q) => p.delete(q));
            const qs = p.toString();
            router.push(qs ? `${pathname}?${qs}` : pathname);
          }}
          style={{ background: "transparent", border: "none", color: cores.info, fontSize: "0.75rem", cursor: "pointer", fontWeight: 600 }}
        >
          {tr("Limpar")}</button>
      )}
    </div>
  );
}

const sel: React.CSSProperties = {
  background: cores.bgCartao,
  border: `1px solid ${cores.bordaForte}`,
  borderRadius: raio.sm,
  color: cores.textoForte,
  padding: "6px 10px",
  fontSize: "0.8rem",
  fontWeight: 600,
  cursor: "pointer",
};
