"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { cores, espaco, raio } from "@/lib/theme";

export function RelatorioEditor({ teamId, textoInicial }: { teamId: string; textoInicial: string }) {
  const [texto, setTexto] = useState(textoInicial);
  const [aGerar, setAGerar] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function exportarPdf() {
    setAGerar(true);
    setErro(null);

    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (!session) {
      setErro("A tua sessão expirou — atualiza a página e entra outra vez.");
      setAGerar(false);
      return;
    }

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/relatorio/pdf`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ texto }),
      });

      if (!res.ok) {
        const detalhe = await res.json().catch(() => null);
        setErro(detalhe?.detail || "Não foi possível gerar o PDF.");
        return;
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `relatorio_dia.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      setErro("Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr.");
    } finally {
      setAGerar(false);
    }
  }

  return (
    <div>
      <label style={{ display: "block", fontSize: "0.78rem", color: cores.textoSuave, marginBottom: espaco.sm }}>
        Podes editar o texto antes de exportar — ajusta o tom, acrescenta observações, ou reescreve como preferires.
      </label>
      <textarea
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        rows={8}
        style={{
          width: "100%",
          background: cores.bgCartao,
          border: `1px solid ${cores.bordaForte}`,
          borderRadius: raio.md,
          color: "white",
          padding: espaco.md,
          fontSize: "0.9rem",
          lineHeight: 1.6,
          fontFamily: "inherit",
          resize: "vertical",
        }}
      />

      {erro && (
        <p style={{ color: cores.perigo, fontSize: "0.82rem", marginTop: espaco.sm }}>{erro}</p>
      )}

      <button
        onClick={exportarPdf}
        disabled={aGerar}
        style={{
          marginTop: espaco.md,
          padding: "10px 22px",
          background: aGerar ? `${cores.cargaInterna}80` : cores.cargaInterna,
          border: "none",
          borderRadius: raio.sm,
          color: "white",
          fontWeight: 700,
          fontSize: "0.85rem",
          cursor: aGerar ? "default" : "pointer",
        }}
      >
        {aGerar ? "A gerar PDF…" : "📄 Exportar PDF"}
      </button>
    </div>
  );
}
