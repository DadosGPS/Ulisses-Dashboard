"use client";

import { usePathname, useRouter } from "next/navigation";
import { cores, espaco, raio } from "@/lib/theme";

/** Seletor de intervalo (início/fim) para os gráficos de evolução por
 * microciclo — por omissão mostra a época toda. Escreve nos query params da
 * própria rota, por isso é reutilizável em qualquer página. */
export function IntervaloMicrociclos({
  opcoes,
  inicio,
  fim,
}: {
  opcoes: number[];
  inicio: number | null;
  fim: number | null;
}) {
  const router = useRouter();
  const pathname = usePathname();

  if (opcoes.length === 0) return null;

  function mudar(novoInicio: number | null, novoFim: number | null) {
    const params = new URLSearchParams();
    if (novoInicio !== null) params.set("micro_inicio", String(novoInicio));
    if (novoFim !== null) params.set("micro_fim", String(novoFim));
    router.push(params.toString() ? `${pathname}?${params.toString()}` : pathname);
  }

  const estiloSelect: React.CSSProperties = {
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
    <div style={{ display: "flex", alignItems: "center", gap: espaco.sm }}>
      <span style={{ fontSize: "0.72rem", color: cores.textoSuave }}>Semana</span>
      <select value={inicio ?? ""} onChange={(e) => mudar(e.target.value ? Number(e.target.value) : null, fim)} style={estiloSelect}>
        <option value="">{opcoes[0]}</option>
        {opcoes.map((mc) => (
          <option key={mc} value={mc}>
            {mc}
          </option>
        ))}
      </select>
      <span style={{ fontSize: "0.72rem", color: cores.textoSuave }}>até</span>
      <select value={fim ?? ""} onChange={(e) => mudar(inicio, e.target.value ? Number(e.target.value) : null)} style={estiloSelect}>
        <option value="">{opcoes[opcoes.length - 1]}</option>
        {opcoes.map((mc) => (
          <option key={mc} value={mc}>
            {mc}
          </option>
        ))}
      </select>
      {(inicio !== null || fim !== null) && (
        <button
          onClick={() => mudar(null, null)}
          style={{ background: "transparent", border: "none", color: cores.info, fontSize: "0.72rem", cursor: "pointer", fontWeight: 600 }}
        >
          Ver época toda
        </button>
      )}
    </div>
  );
}
