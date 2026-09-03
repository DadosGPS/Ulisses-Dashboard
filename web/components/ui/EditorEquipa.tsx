"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { cores, espaco, raio } from "@/lib/theme";

/** Edição do nome e desporto da equipa. */
export function EditorEquipa({ teamId, nomeInicial, desportoInicial }: { teamId: string; nomeInicial: string; desportoInicial: string }) {
  const [nome, setNome] = useState(nomeInicial);
  const [desporto, setDesporto] = useState(desportoInicial || "Futebol");
  const [aGuardar, setAGuardar] = useState(false);
  const [msg, setMsg] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);

  async function guardar() {
    setAGuardar(true);
    setMsg(null);
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) { setMsg({ tipo: "erro", texto: "Sessão expirada." }); return; }

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/configuracoes/equipa`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ nome, desporto }),
      });
      if (res.ok) {
        setMsg({ tipo: "ok", texto: "Guardado." });
      } else {
        const err = await res.json().catch(() => ({}));
        setMsg({ tipo: "erro", texto: err.detail || "Não foi possível guardar." });
      }
    } finally {
      setAGuardar(false);
    }
  }

  const alterado = nome !== nomeInicial || desporto !== (desportoInicial || "Futebol");

  return (
    <div style={{ maxWidth: 480, background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.lg }}>
      <Campo label="Nome da equipa">
        <input value={nome} onChange={(e) => setNome(e.target.value)} style={input} />
      </Campo>
      <Campo label="Desporto">
        <input value={desporto} onChange={(e) => setDesporto(e.target.value)} style={input} />
      </Campo>

      <div style={{ display: "flex", alignItems: "center", gap: espaco.md, marginTop: espaco.md }}>
        <button
          onClick={guardar}
          disabled={!alterado || aGuardar || !nome.trim()}
          style={{
            background: !alterado || !nome.trim() ? cores.bgElevado : cores.sucesso,
            color: "white",
            border: "none",
            borderRadius: raio.sm,
            padding: "9px 18px",
            fontSize: "0.85rem",
            fontWeight: 700,
            cursor: !alterado || aGuardar || !nome.trim() ? "not-allowed" : "pointer",
            opacity: aGuardar ? 0.6 : 1,
          }}
        >
          {aGuardar ? "A guardar…" : "Guardar"}
        </button>
        {msg && (
          <span style={{ fontSize: "0.82rem", fontWeight: 600, color: msg.tipo === "ok" ? cores.sucesso : cores.perigo }}>{msg.texto}</span>
        )}
      </div>
    </div>
  );
}

const input: React.CSSProperties = {
  width: "100%",
  background: cores.bg,
  border: `1px solid ${cores.bordaForte}`,
  borderRadius: raio.sm,
  color: "white",
  fontSize: "0.9rem",
  padding: "9px 12px",
};

function Campo({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ display: "block", marginBottom: espaco.md }}>
      <div style={{ fontSize: "0.72rem", textTransform: "uppercase", letterSpacing: "0.04em", color: cores.textoSuave, marginBottom: 6, fontWeight: 600 }}>{label}</div>
      {children}
    </label>
  );
}
