"use client";

import { cores } from "@/lib/theme";
import { mudarLingua, useTr } from "@/lib/i18n/cliente";

/** Botões PT / EN no canto do ecrã — para páginas sem menu lateral (entrar, criar conta, convite). */
export function TrocaLingua() {
  const tr = useTr();
  return (
    <div style={{ position: "fixed", top: 14, right: 16, display: "flex", gap: 4, zIndex: 10 }}>
      {(["pt", "en"] as const).map((l) => {
        const ativo = tr.lingua === l;
        return (
          <button key={l} onClick={() => !ativo && mudarLingua(l)} aria-pressed={ativo} title={l === "pt" ? "Português" : "English"}
            style={{ padding: "4px 9px", fontSize: "0.74rem", fontWeight: 700, borderRadius: 6, cursor: ativo ? "default" : "pointer",
              border: `1px solid ${ativo ? cores.acento : cores.borda}`, background: ativo ? cores.acento : "transparent",
              color: ativo ? "#fff" : cores.textoSuave }}>
            {l.toUpperCase()}
          </button>
        );
      })}
    </div>
  );
}
