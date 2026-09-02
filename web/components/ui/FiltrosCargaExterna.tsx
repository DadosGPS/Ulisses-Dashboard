"use client";

import { useRouter } from "next/navigation";
import { cores, espaco, raio } from "@/lib/theme";

/** Filtros da página de Carga Externa — propagam-se via query params para o
 * server component recarregar os dados (tal como IntervaloMicrociclos). */
export function FiltrosCargaExterna({
  tipos,
  posicoes,
  diasMd,
  tipo,
  posicao,
  diaMd,
}: {
  tipos: string[];
  posicoes: string[];
  diasMd: string[];
  tipo: string | null;
  posicao: string | null;
  diaMd: string | null;
}) {
  const router = useRouter();

  function aplicar(campo: string, valor: string) {
    const params = new URLSearchParams();
    const atual: Record<string, string | null> = { tipo, posicao, dia_md: diaMd };
    atual[campo] = valor || null;
    for (const [k, v] of Object.entries(atual)) if (v) params.set(k, v);
    router.push(params.toString() ? `/carga-externa?${params.toString()}` : "/carga-externa");
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

  const temFiltro = Boolean(tipo || posicao || diaMd);

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
      {diasMd.length > 0 && (
        <select value={diaMd ?? ""} onChange={(e) => aplicar("dia_md", e.target.value)} style={estilo}>
          <option value="">MD: todos</option>
          {diasMd.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      )}
      {temFiltro && (
        <button
          onClick={() => router.push("/carga-externa")}
          style={{ background: "transparent", border: "none", color: cores.info, fontSize: "0.72rem", cursor: "pointer", fontWeight: 600 }}
        >
          Limpar filtros
        </button>
      )}
    </div>
  );
}
