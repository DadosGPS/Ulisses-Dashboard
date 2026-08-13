"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { NomeJogador } from "@/components/ui/NomeJogador";
import { cores, espaco, raio } from "@/lib/theme";
import type { EstadoJogador } from "@/lib/types";

const OPCOES_ESTADO: { valor: EstadoJogador["estado"]; label: string }[] = [
  { valor: "apto", label: "Apto" },
  { valor: "lesionado", label: "Lesionado" },
  { valor: "em_recuperacao", label: "Em recuperação" },
  { valor: "ausente", label: "Ausente" },
];

/** Gestão do estado de disponibilidade dos atletas — sem isto a app não
 * distinguia "jogador sem sessões porque está lesionado" de "falta de dados". */
export function EstadoAtletas({ teamId, estadosIniciais }: { teamId: string; estadosIniciais: EstadoJogador[] }) {
  const [estados, setEstados] = useState(estadosIniciais);
  const [aGuardar, setAGuardar] = useState<string | null>(null);

  async function autorizar() {
    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();
    return session?.access_token ?? null;
  }

  async function guardar(playerId: string, estado: EstadoJogador["estado"], motivo: string | null) {
    setAGuardar(playerId);
    const token = await autorizar();
    if (!token) {
      setAGuardar(null);
      return;
    }
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/jogadores/${playerId}/estado`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ estado, motivo: motivo || null }),
      });
      if (res.ok) {
        const atualizado: EstadoJogador = await res.json();
        setEstados((atual) => atual.map((e) => (e.player_id === playerId ? atualizado : e)));
      }
    } finally {
      setAGuardar(null);
    }
  }

  async function alternarAtivo(playerId: string, ativo: boolean) {
    setAGuardar(playerId);
    const token = await autorizar();
    if (!token) {
      setAGuardar(null);
      return;
    }
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/jogadores/${playerId}/ativo`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ ativo }),
      });
      if (res.ok) {
        const atualizado: EstadoJogador = await res.json();
        setEstados((atual) => atual.map((e) => (e.player_id === playerId ? atualizado : e)));
      }
    } finally {
      setAGuardar(null);
    }
  }

  if (estados.length === 0) return null;

  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, overflow: "hidden" }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ background: "rgba(255,255,255,0.04)" }}>
            <th style={th("left")}>Jogador</th>
            <th style={th("left")}>Estado</th>
            <th style={th("left")}>Motivo</th>
            <th style={th("left")}>Plantel</th>
          </tr>
        </thead>
        <tbody>
          {estados.map((e) => (
            <tr
              key={e.player_id}
              style={{ borderTop: `1px solid ${cores.borda}`, opacity: aGuardar === e.player_id ? 0.5 : e.ativo ? 1 : 0.55 }}
            >
              <td style={{ padding: "8px 14px", fontSize: "0.8rem", fontWeight: 600, color: "rgba(255,255,255,0.9)", whiteSpace: "nowrap" }}>
                <NomeJogador nome={e.nome} />
              </td>
              <td style={{ padding: "6px 8px" }}>
                <select
                  value={e.estado}
                  disabled={!e.ativo}
                  onChange={(ev) => guardar(e.player_id, ev.target.value as EstadoJogador["estado"], e.estado_motivo)}
                  style={{
                    background: cores.bg,
                    border: `1px solid ${cores.bordaForte}`,
                    borderRadius: raio.sm,
                    color: e.estado === "apto" ? cores.sucesso : cores.atencao,
                    fontWeight: 600,
                    fontSize: "0.78rem",
                    padding: "5px 8px",
                  }}
                >
                  {OPCOES_ESTADO.map((o) => (
                    <option key={o.valor} value={o.valor}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </td>
              <td style={{ padding: "6px 8px" }}>
                <input
                  type="text"
                  defaultValue={e.estado_motivo ?? ""}
                  placeholder="opcional"
                  disabled={!e.ativo}
                  onBlur={(ev) => {
                    if (ev.target.value !== (e.estado_motivo ?? "")) guardar(e.player_id, e.estado, ev.target.value);
                  }}
                  style={{
                    width: "100%",
                    background: cores.bg,
                    border: `1px solid ${cores.borda}`,
                    borderRadius: raio.sm,
                    color: "rgba(255,255,255,0.85)",
                    fontSize: "0.78rem",
                    padding: "5px 8px",
                  }}
                />
              </td>
              <td style={{ padding: "6px 8px" }}>
                <button
                  onClick={() => alternarAtivo(e.player_id, !e.ativo)}
                  style={{
                    background: "transparent",
                    border: `1px solid ${cores.borda}`,
                    borderRadius: raio.sm,
                    color: e.ativo ? cores.textoSuave : cores.info,
                    fontWeight: 600,
                    fontSize: "0.72rem",
                    padding: "5px 10px",
                    cursor: "pointer",
                    whiteSpace: "nowrap",
                  }}
                >
                  {e.ativo ? "Remover do plantel" : "Reativar"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function th(align: "left" | "center"): React.CSSProperties {
  return { padding: "9px 12px", fontSize: "0.62rem", letterSpacing: "0.06em", textTransform: "uppercase", color: cores.textoSuave, textAlign: align, whiteSpace: "nowrap" };
}
