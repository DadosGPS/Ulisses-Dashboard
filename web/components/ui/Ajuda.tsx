"use client";

import { useEffect, useRef, useState } from "react";
import { cores, raio, sombra } from "@/lib/theme";
import { useTr } from "@/lib/i18n/cliente";

/** Ícone «i» com uma explicação que abre ao passar o rato ou ao clicar.
 * Substitui os parágrafos explicativos que enchiam as páginas. */
export function Ajuda({ children, largura = 320 }: { children: React.ReactNode; largura?: number }) {
  const tr = useTr();
  const [aberto, setAberto] = useState(false);
  const [fixo, setFixo] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!fixo) return;
    const fora = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) { setFixo(false); setAberto(false); } };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") { setFixo(false); setAberto(false); } };
    document.addEventListener("mousedown", fora);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", fora); document.removeEventListener("keydown", esc); };
  }, [fixo]);

  const visivel = aberto || fixo;
  return (
    <span ref={ref} style={{ position: "relative", display: "inline-flex", verticalAlign: "middle" }}
      onMouseEnter={() => setAberto(true)} onMouseLeave={() => setAberto(false)}>
      <button type="button" aria-label={tr("Como se lê")} aria-expanded={visivel} onClick={() => setFixo(!fixo)}
        style={{ width: 17, height: 17, borderRadius: "50%", border: `1px solid ${cores.bordaForte}`, background: "transparent",
          color: cores.textoSuave, fontSize: "0.66rem", fontWeight: 700, fontStyle: "italic", fontFamily: "Georgia, serif",
          lineHeight: 1, cursor: "pointer", display: "inline-flex", alignItems: "center", justifyContent: "center", padding: 0 }}>
        i
      </button>
      {visivel && (
        <span role="tooltip" data-no-print style={{
          position: "absolute", top: "calc(100% + 6px)", left: -8, zIndex: 50, width: largura, maxWidth: "80vw",
          background: cores.bgCartao, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.md, boxShadow: sombra.cartao,
          padding: "10px 12px", fontSize: "0.76rem", fontWeight: 400, lineHeight: 1.5, color: cores.texto, textAlign: "left",
          letterSpacing: 0, textTransform: "none", whiteSpace: "normal",
        }}>
          {children}
        </span>
      )}
    </span>
  );
}
