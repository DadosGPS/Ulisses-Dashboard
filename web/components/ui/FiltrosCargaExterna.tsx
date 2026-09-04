"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { cores, espaco, raio } from "@/lib/theme";

/** Barra de filtros única da página de Carga Externa. Junta num só sítio todos
 * os filtros que a página aplica — jogador, microciclo, dia MD, tipo e posição —
 * para não haver dois conjuntos de seletores (a barra global fica desligada
 * nesta página). Cada mudança escreve o query param e preserva os restantes. */
export function FiltrosCargaExterna({
  jogadores,
  microciclos,
  diasMd,
  tipos,
  posicoes,
  jogador,
  microciclo,
  diaMd,
  tipo,
  posicao,
}: {
  jogadores: string[];
  microciclos: number[];
  diasMd: string[];
  tipos: string[];
  posicoes: string[];
  jogador: string | null;
  microciclo: string | null;
  diaMd: string | null;
  tipo: string | null;
  posicao: string | null;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const { oculto } = usePrivacidade();

  function aplicar(chave: string, valor: string) {
    const p = new URLSearchParams(params.toString());
    if (valor) p.set(chave, valor);
    else p.delete(chave);
    const qs = p.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname);
  }

  const ativos = [jogador, microciclo, diaMd, tipo, posicao].filter(Boolean).length;

  function limpar() {
    const p = new URLSearchParams(params.toString());
    ["jogador", "microciclo", "dia_md", "tipo", "posicao"].forEach((k) => p.delete(k));
    const qs = p.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname);
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: espaco.sm, flexWrap: "wrap" }}>
      {jogadores.length > 0 && (
        <select value={jogador ?? ""} onChange={(e) => aplicar("jogador", e.target.value)} style={estilo} aria-label="Jogador">
          <option value="">Equipa toda</option>
          {jogadores.map((j) => (
            <option key={j} value={j}>{nomeOuOculto(j, oculto)}</option>
          ))}
        </select>
      )}
      {microciclos.length > 0 && (
        <select value={microciclo ?? ""} onChange={(e) => aplicar("microciclo", e.target.value)} style={estilo} aria-label="Microciclo">
          <option value="">Todos os microciclos</option>
          {microciclos.map((m) => (
            <option key={m} value={m}>Semana {m}</option>
          ))}
        </select>
      )}
      {diasMd.length > 0 && (
        <select value={diaMd ?? ""} onChange={(e) => aplicar("dia_md", e.target.value)} style={estilo} aria-label="Dia MD">
          <option value="">Todos os dias</option>
          {diasMd.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      )}
      {tipos.length > 0 && (
        <select value={tipo ?? ""} onChange={(e) => aplicar("tipo", e.target.value)} style={estilo} aria-label="Tipo">
          <option value="">Tipo: todos</option>
          {tipos.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      )}
      {posicoes.length > 0 && (
        <select value={posicao ?? ""} onChange={(e) => aplicar("posicao", e.target.value)} style={estilo} aria-label="Posição">
          <option value="">Posição: todas</option>
          {posicoes.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      )}
      {ativos > 0 && (
        <button onClick={limpar} style={{ background: "transparent", border: "none", color: cores.info, fontSize: "0.75rem", cursor: "pointer", fontWeight: 600 }}>
          Limpar
        </button>
      )}
    </div>
  );
}

const estilo: React.CSSProperties = {
  background: cores.bgCartao,
  border: `1px solid ${cores.bordaForte}`,
  borderRadius: raio.sm,
  color: "white",
  padding: "7px 10px",
  fontSize: "0.8rem",
  fontWeight: 600,
  cursor: "pointer",
};
