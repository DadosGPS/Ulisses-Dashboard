"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { cores, espaco, raio } from "@/lib/theme";
import type { EstadoJogador } from "@/lib/types";

async function token(): Promise<string | null> {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

/** CRUD do plantel: adicionar jogador, editar nome/posição, ativar/desativar.
 * O estado de disponibilidade (apto/lesionado…) gere-se logo abaixo, na mesma
 * página (componente EstadoAtletas). */
export function EditorJogadores({ teamId, jogadoresIniciais }: { teamId: string; jogadoresIniciais: EstadoJogador[] }) {
  const [jogadores, setJogadores] = useState<EstadoJogador[]>(jogadoresIniciais);
  const [novoNome, setNovoNome] = useState("");
  const [novaPos, setNovaPos] = useState("");
  const [aGuardar, setAGuardar] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const base = `${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}`;

  async function adicionar() {
    if (!novoNome.trim()) return;
    setAGuardar("novo");
    setErro(null);
    const t = await token();
    if (!t) { setErro("Sessão expirada."); setAGuardar(null); return; }
    try {
      const res = await fetch(`${base}/configuracoes/jogadores`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${t}` },
        body: JSON.stringify({ nome: novoNome, posicao: novaPos }),
      });
      if (res.ok) {
        const novo: EstadoJogador = await res.json();
        setJogadores((a) => [...a, novo].sort((x, y) => Number(y.ativo) - Number(x.ativo) || x.nome.localeCompare(y.nome)));
        setNovoNome(""); setNovaPos("");
      } else {
        const err = await res.json().catch(() => ({}));
        setErro(err.detail || "Não foi possível adicionar.");
      }
    } finally { setAGuardar(null); }
  }

  async function guardar(j: EstadoJogador, nome: string, posicao: string) {
    setAGuardar(j.player_id); setErro(null);
    const t = await token();
    if (!t) { setErro("Sessão expirada."); setAGuardar(null); return; }
    try {
      const res = await fetch(`${base}/configuracoes/jogadores/${j.player_id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${t}` },
        body: JSON.stringify({ nome, posicao }),
      });
      if (res.ok) {
        const upd: EstadoJogador = await res.json();
        setJogadores((a) => a.map((x) => (x.player_id === j.player_id ? upd : x)));
      } else {
        const err = await res.json().catch(() => ({}));
        setErro(err.detail || "Não foi possível guardar.");
      }
    } finally { setAGuardar(null); }
  }

  async function alternarAtivo(j: EstadoJogador) {
    setAGuardar(j.player_id); setErro(null);
    const t = await token();
    if (!t) { setErro("Sessão expirada."); setAGuardar(null); return; }
    try {
      const res = await fetch(`${base}/jogadores/${j.player_id}/ativo`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${t}` },
        body: JSON.stringify({ ativo: !j.ativo }),
      });
      if (res.ok) {
        const upd: EstadoJogador = await res.json();
        setJogadores((a) => a.map((x) => (x.player_id === j.player_id ? upd : x)).sort((x, y) => Number(y.ativo) - Number(x.ativo) || x.nome.localeCompare(y.nome)));
      }
    } finally { setAGuardar(null); }
  }

  return (
    <div>
      {/* Adicionar */}
      <div style={{ display: "flex", gap: espaco.sm, flexWrap: "wrap", alignItems: "flex-end", marginBottom: espaco.lg, background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
        <label style={{ flex: "2 1 180px" }}>
          <div style={rotulo}>Nome do jogador</div>
          <input value={novoNome} onChange={(e) => setNovoNome(e.target.value)} placeholder="Ex: João Silva" style={input} />
        </label>
        <label style={{ flex: "1 1 100px" }}>
          <div style={rotulo}>Posição</div>
          <input value={novaPos} onChange={(e) => setNovaPos(e.target.value)} placeholder="Ex: CM" style={input} />
        </label>
        <button
          onClick={adicionar}
          disabled={!novoNome.trim() || aGuardar === "novo"}
          style={{ background: cores.sucesso, color: "white", border: "none", borderRadius: raio.sm, padding: "9px 16px", fontSize: "0.85rem", fontWeight: 700, cursor: novoNome.trim() ? "pointer" : "not-allowed", opacity: aGuardar === "novo" ? 0.6 : 1 }}
        >
          + Adicionar
        </button>
      </div>

      {erro && <p style={{ color: cores.perigo, fontSize: "0.82rem", marginBottom: espaco.md, fontWeight: 600 }}>{erro}</p>}

      {/* Lista */}
      <div style={{ overflowX: "auto", border: `1px solid ${cores.borda}`, borderRadius: raio.md, background: cores.bgCartao }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "rgba(255,255,255,0.04)" }}>
              <th style={th}>Nome</th>
              <th style={th}>Posição</th>
              <th style={th}>Estado</th>
              <th style={{ ...th, textAlign: "right" }}>Ações</th>
            </tr>
          </thead>
          <tbody>
            {jogadores.map((j) => (
              <LinhaJogador key={j.player_id} j={j} aGuardar={aGuardar === j.player_id} onGuardar={guardar} onAlternarAtivo={alternarAtivo} />
            ))}
            {jogadores.length === 0 && (
              <tr><td colSpan={4} style={{ padding: espaco.lg, color: cores.textoSuave, fontSize: "0.85rem", textAlign: "center" }}>Sem jogadores. Adiciona o primeiro acima.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function LinhaJogador({
  j, aGuardar, onGuardar, onAlternarAtivo,
}: {
  j: EstadoJogador;
  aGuardar: boolean;
  onGuardar: (j: EstadoJogador, nome: string, posicao: string) => void;
  onAlternarAtivo: (j: EstadoJogador) => void;
}) {
  const [nome, setNome] = useState(j.nome);
  const [posicao, setPosicao] = useState(j.posicao ?? "");
  const alterado = nome !== j.nome || posicao !== (j.posicao ?? "");

  return (
    <tr style={{ borderTop: `1px solid ${cores.borda}`, opacity: j.ativo ? (aGuardar ? 0.5 : 1) : 0.55 }}>
      <td style={{ padding: "6px 10px" }}>
        <input value={nome} onChange={(e) => setNome(e.target.value)} style={{ ...input, minWidth: 140 }} />
      </td>
      <td style={{ padding: "6px 10px" }}>
        <input value={posicao} onChange={(e) => setPosicao(e.target.value)} style={{ ...input, minWidth: 70, maxWidth: 90 }} />
      </td>
      <td style={{ padding: "6px 10px", fontSize: "0.78rem", color: j.estado === "apto" ? cores.sucesso : cores.atencao, fontWeight: 600, whiteSpace: "nowrap" }}>
        {j.ativo ? j.estado : "Fora do plantel"}
      </td>
      <td style={{ padding: "6px 10px", textAlign: "right", whiteSpace: "nowrap" }}>
        {alterado && (
          <button onClick={() => onGuardar(j, nome, posicao)} disabled={aGuardar || !nome.trim()} style={btn(cores.sucesso)}>Guardar</button>
        )}
        <button onClick={() => onAlternarAtivo(j)} disabled={aGuardar} style={btn("transparent", j.ativo ? cores.textoSuave : cores.info)}>
          {j.ativo ? "Remover" : "Reativar"}
        </button>
      </td>
    </tr>
  );
}

const th: React.CSSProperties = { padding: "10px 12px", fontSize: "0.62rem", letterSpacing: "0.06em", textTransform: "uppercase", color: cores.textoSuave, textAlign: "left", whiteSpace: "nowrap" };
const rotulo: React.CSSProperties = { fontSize: "0.68rem", textTransform: "uppercase", letterSpacing: "0.04em", color: cores.textoSuave, marginBottom: 4, fontWeight: 600 };
const input: React.CSSProperties = { width: "100%", background: cores.bg, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: "white", fontSize: "0.85rem", padding: "7px 10px" };

function btn(bg: string, cor = "white"): React.CSSProperties {
  return { background: bg, color: cor, border: bg === "transparent" ? `1px solid ${cores.borda}` : "none", borderRadius: raio.sm, padding: "6px 12px", fontSize: "0.75rem", fontWeight: 600, cursor: "pointer", marginLeft: 6 };
}
