"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { cores, raio } from "@/lib/theme";
import { useTr } from "@/lib/i18n/cliente";

/** Escolha da sessão (ou jogo) do relatório: muda ?data= e mantém o resto. */
export function SeletorSessao({ opcoes, atual, rotulo }: {
  opcoes: { valor: string; texto: string }[]; atual: string; rotulo: string;
}) {
  const tr = useTr();
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: "0.68rem", fontWeight: 600, color: cores.textoSuave, textTransform: "uppercase", letterSpacing: "0.04em" }}>
      {tr(rotulo)}
      <select
        value={atual}
        aria-label={tr(rotulo)}
        onChange={(e) => {
          const q = new URLSearchParams(params.toString());
          q.set("data", e.target.value);
          router.push(`${pathname}?${q.toString()}`);
        }}
        style={{ minWidth: 230, background: cores.bgCartao, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: cores.textoForte, fontSize: "0.85rem", padding: "7px 10px", textTransform: "none", letterSpacing: 0, fontWeight: 500 }}
      >
        {opcoes.map((o) => <option key={o.valor} value={o.valor}>{o.texto}</option>)}
      </select>
    </label>
  );
}

/** Botão de imprimir / guardar em PDF (usa o diálogo do browser). */
export function BotaoImprimir() {
  const tr = useTr();
  return (
    <button onClick={() => window.print()} data-no-print
      style={{ alignSelf: "flex-end", background: cores.bgCartao, color: cores.texto, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, padding: "8px 14px", fontSize: "0.82rem", fontWeight: 600, cursor: "pointer" }}>
      {tr("Imprimir / PDF")}
    </button>
  );
}
