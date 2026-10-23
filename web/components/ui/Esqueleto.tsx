"use client";

import { cores, espaco, raio } from "@/lib/theme";
import { useTr } from "@/lib/i18n/cliente";

/** Bloco cinzento com brilho a passar — ocupa o lugar do conteúdo enquanto carrega. */
export function Bloco({ altura = 14, largura = "100%", estilo }: { altura?: number; largura?: number | string; estilo?: React.CSSProperties }) {
  return <div className="lm-esqueleto" style={{ height: altura, width: largura, borderRadius: raio.sm, ...estilo }} />;
}

/** Esqueleto de uma secção típica: título, uma fila de cartões e uma tabela. */
export function Carregando({ cartoes = 4, linhas = 6, padding = true }: { cartoes?: number; linhas?: number; padding?: boolean }) {
  const tr = useTr();
  return (
    <div role="status" aria-label={tr("A carregar…")} style={{ padding: padding ? `${espaco.xl}px ${espaco.xxl}px` : 0, display: "flex", flexDirection: "column", gap: espaco.lg }}>
      <Bloco altura={18} largura={220} />
      {cartoes > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: `repeat(${cartoes}, minmax(0, 1fr))`, gap: espaco.md }}>
          {Array.from({ length: cartoes }, (_, i) => (
            <div key={i} style={{ border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md, display: "flex", flexDirection: "column", gap: 10, background: cores.bgCartao }}>
              <Bloco altura={10} largura="50%" />
              <Bloco altura={24} largura="70%" />
              <Bloco altura={10} largura="40%" />
            </div>
          ))}
        </div>
      )}
      <div style={{ border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md, display: "flex", flexDirection: "column", gap: 12, background: cores.bgCartao }}>
        {Array.from({ length: linhas }, (_, i) => <Bloco key={i} altura={12} largura={`${92 - (i % 3) * 14}%`} />)}
      </div>
    </div>
  );
}
