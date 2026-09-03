"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { cores, espaco, raio } from "@/lib/theme";

/** Filtros específicos da página de Carga Externa (tipo de sessão e posição).
 * O jogador, microciclo e dia MD são geridos pela barra de filtros global —
 * este componente preserva esses params ao mudar tipo/posição. */
export function FiltrosCargaExterna({
  tipos,
  posicoes,
  tipo,
  posicao,
}: {
  tipos: string[];
  posicoes: string[];
  tipo: string | null;
  posicao: string | null;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  function aplicar(chave: string, valor: string) {
    const p = new URLSearchParams(params.toString());
    if (valor) p.set(chave, valor);
    else p.delete(chave);
    const qs = p.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname);
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

  return (
    <div style={{ display: "flex", alignItems: "center", gap: espaco.sm, flexWrap: "wrap" }}>
      {tipos.length > 0 && (
        <select value={tipo ?? ""} onChange={(e) => aplicar("tipo", e.target.value)} style={estilo}>
          <option value="">Tipo: todos</option>
          {tipos.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      )}
      {posicoes.length > 0 && (
        <select value={posicao ?? ""} onChange={(e) => aplicar("posicao", e.target.value)} style={estilo}>
          <option value="">Posição: todas</option>
          {posicoes.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      )}
    </div>
  );
}
