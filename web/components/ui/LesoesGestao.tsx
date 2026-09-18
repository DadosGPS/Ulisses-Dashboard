"use client";

import { useMemo, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { espaco, raio } from "@/lib/theme";
import { BodyMap, ZONAS } from "@/components/ui/BodyMap";
import type { LesoesResponse, LesoesJogador } from "@/lib/types";

const TINTA = "#1e293b";
const SUAVE = "#64748b";
const cartao: React.CSSProperties = { background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: raio.md, padding: espaco.md };
const inputEstilo: React.CSSProperties = { background: "#ffffff", border: "1px solid #cbd5e1", borderRadius: raio.sm, color: TINTA, padding: "6px 8px", fontSize: "0.82rem" };

const LADOS = ["esquerdo", "direito", "central"];
const TIPOS = ["muscular", "articular", "ligamentar", "tendão", "óssea", "outro"];
const GRAVIDADES = ["leve", "moderada", "grave"];
const hoje = () => new Date().toISOString().slice(0, 10);

export function LesoesGestao({ teamId, dadosIniciais }: { teamId: string; dadosIniciais: LesoesResponse }) {
  const { oculto } = usePrivacidade();
  const [dados, setDados] = useState(dadosIniciais);
  const [selecionado, setSelecionado] = useState<string | null>(dadosIniciais.jogadores[0]?.player_id ?? null);
  const [aGuardar, setAGuardar] = useState(false);
  const [form, setForm] = useState({ player_id: "", zona: "coxa_post", lado: "esquerdo", tipo: "muscular", gravidade: "moderada", data_inicio: hoje(), data_fim: "", notas: "" });

  async function token() {
    const { data: { session } } = await createClient().auth.getSession();
    return session?.access_token ?? null;
  }
  async function recarregar() {
    const t = await token();
    if (!t) return;
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/lesoes`, { headers: { Authorization: `Bearer ${t}` } });
    if (res.ok) setDados(await res.json());
  }

  async function criarLesao() {
    if (!form.player_id || !form.zona || !form.data_inicio) return;
    setAGuardar(true);
    const t = await token();
    if (!t) { setAGuardar(false); return; }
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/lesoes`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${t}` },
        body: JSON.stringify({ ...form, data_fim: form.data_fim || null, notas: form.notas || null }),
      });
      await recarregar();
      setSelecionado(form.player_id);
      setForm((f) => ({ ...f, notas: "" }));
    } finally {
      setAGuardar(false);
    }
  }

  async function fecharLesao(id: string) {
    const t = await token();
    if (!t) return;
    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/lesoes/${id}`, {
      method: "PUT", headers: { "Content-Type": "application/json", Authorization: `Bearer ${t}` },
      body: JSON.stringify({ data_fim: hoje() }),
    });
    await recarregar();
  }
  async function apagarLesao(id: string) {
    if (!window.confirm("Apagar esta lesão?")) return;
    const t = await token();
    if (!t) return;
    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/lesoes/${id}`, {
      method: "DELETE", headers: { Authorization: `Bearer ${t}` },
    });
    await recarregar();
  }

  const jogadorSel = useMemo(() => dados.jogadores.find((j) => j.player_id === selecionado) ?? null, [dados, selecionado]);
  const labelZona = ZONAS.reduce<Record<string, string>>((a, z) => ((a[z.chave] = z.label), a), {});

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: espaco.xl }}>
      {/* Formulário de registo */}
      <div style={cartao}>
        <h3 style={{ fontSize: "0.9rem", fontWeight: 700, color: TINTA, margin: `0 0 ${espaco.sm}px` }}>➕ Registar lesão</h3>
        <div style={{ display: "flex", gap: espaco.sm, flexWrap: "wrap", alignItems: "flex-end" }}>
          <Campo label="Jogador">
            <select value={form.player_id} onChange={(e) => setForm({ ...form, player_id: e.target.value })} style={{ ...inputEstilo, minWidth: 150 }}>
              <option value="">— escolher —</option>
              {dados.jogadores.map((j) => <option key={j.player_id} value={j.player_id}>{nomeOuOculto(j.jogador, oculto)}</option>)}
            </select>
          </Campo>
          <Campo label="Zona">
            <select value={form.zona} onChange={(e) => setForm({ ...form, zona: e.target.value })} style={inputEstilo}>
              {ZONAS.map((z) => <option key={z.chave} value={z.chave}>{z.label}</option>)}
            </select>
          </Campo>
          <Campo label="Lado">
            <select value={form.lado} onChange={(e) => setForm({ ...form, lado: e.target.value })} style={inputEstilo}>
              {LADOS.map((l) => <option key={l} value={l}>{l}</option>)}
            </select>
          </Campo>
          <Campo label="Tipo">
            <select value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })} style={inputEstilo}>
              {TIPOS.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </Campo>
          <Campo label="Gravidade">
            <select value={form.gravidade} onChange={(e) => setForm({ ...form, gravidade: e.target.value })} style={inputEstilo}>
              {GRAVIDADES.map((g) => <option key={g} value={g}>{g}</option>)}
            </select>
          </Campo>
          <Campo label="Início"><input type="date" value={form.data_inicio} onChange={(e) => setForm({ ...form, data_inicio: e.target.value })} style={inputEstilo} /></Campo>
          <Campo label="Fim (vazio = em curso)"><input type="date" value={form.data_fim} onChange={(e) => setForm({ ...form, data_fim: e.target.value })} style={inputEstilo} /></Campo>
          <button onClick={criarLesao} disabled={aGuardar || !form.player_id} style={{ padding: "8px 16px", background: "#2563eb", color: "#fff", border: "none", borderRadius: raio.sm, fontWeight: 700, fontSize: "0.85rem", cursor: "pointer", opacity: aGuardar || !form.player_id ? 0.5 : 1 }}>
            {aGuardar ? "A guardar…" : "Registar"}
          </button>
        </div>
      </div>

      {/* Overview da equipa */}
      <div style={cartao}>
        <h3 style={{ fontSize: "0.9rem", fontWeight: 700, color: TINTA, margin: `0 0 ${espaco.sm}px` }}>Plantel — disponibilidade</h3>
        <div style={{ overflowX: "auto" }}>
          <table style={{ borderCollapse: "collapse", fontSize: "0.82rem", width: "100%", minWidth: 460 }}>
            <thead>
              <tr>{["Jogador", "Posição", "Estado", "Lesões", "Dias perdidos", ""].map((h) => <th key={h} style={th}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {dados.jogadores.map((j) => (
                <tr key={j.player_id} style={{ borderTop: "1px solid #e2e8f0", background: j.player_id === selecionado ? "#eff6ff" : undefined }}>
                  <td style={{ ...td, fontWeight: 600, color: TINTA }}>{nomeOuOculto(j.jogador, oculto)}</td>
                  <td style={{ ...td, color: SUAVE }}>{j.posicao}</td>
                  <td style={td}><Badge estado={j.estado} /></td>
                  <td style={{ ...td, textAlign: "center" }}>{j.n_lesoes}</td>
                  <td style={{ ...td, textAlign: "center" }}>{j.dias_perdidos}</td>
                  <td style={td}><button onClick={() => setSelecionado(j.player_id)} style={verBtn}>ver →</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Painel do jogador selecionado */}
      {jogadorSel && (
        <div style={{ display: "grid", gridTemplateColumns: "minmax(280px, 1fr) minmax(320px, 1.4fr)", gap: espaco.lg }}>
          <div style={cartao}>
            <h3 style={{ fontSize: "0.9rem", fontWeight: 700, color: TINTA, margin: `0 0 ${espaco.sm}px` }}>
              🩹 {nomeOuOculto(jogadorSel.jogador, oculto)} · <Badge estado={jogadorSel.estado} />
            </h3>
            <BodyMap freq={jogadorSel.zonas_freq} />
            <Timeline jogador={jogadorSel} />
          </div>

          <div style={cartao}>
            <h3 style={{ fontSize: "0.9rem", fontWeight: 700, color: TINTA, margin: `0 0 ${espaco.sm}px` }}>Episódios</h3>
            {jogadorSel.lesoes.length === 0 ? (
              <p style={{ color: SUAVE, fontSize: "0.85rem" }}>Sem lesões registadas. 🎉</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: espaco.sm }}>
                {jogadorSel.lesoes.map((l) => (
                  <div key={l.id} style={{ border: "1px solid #e2e8f0", borderRadius: raio.sm, padding: espaco.sm, background: l.em_curso ? "#fef2f2" : "#f8fafc" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: espaco.sm, flexWrap: "wrap" }}>
                      <strong style={{ color: TINTA }}>{labelZona[l.zona] ?? l.zona}{l.lado ? ` (${l.lado})` : ""}</strong>
                      <span style={{ fontSize: "0.72rem", color: SUAVE }}>{l.tipo}{l.gravidade ? ` · ${l.gravidade}` : ""}</span>
                    </div>
                    <div style={{ fontSize: "0.76rem", color: SUAVE, marginTop: 2 }}>
                      {l.data_inicio} → {l.data_fim ?? "em curso"} · {l.dias ?? 0} dias
                    </div>
                    {l.notas && <div style={{ fontSize: "0.76rem", color: TINTA, marginTop: 4 }}>{l.notas}</div>}
                    <div style={{ display: "flex", gap: espaco.sm, marginTop: 6 }}>
                      {l.em_curso && <button onClick={() => fecharLesao(l.id)} style={acaoBtn("#16a34a")}>Marcar como recuperado</button>}
                      <button onClick={() => apagarLesao(l.id)} style={acaoBtn("#dc2626")}>Apagar</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Timeline({ jogador }: { jogador: LesoesJogador }) {
  const comData = jogador.lesoes.filter((l) => l.data_inicio);
  if (comData.length === 0) return <p style={{ fontSize: "0.75rem", color: SUAVE, marginTop: espaco.md }}>Sempre disponível (sem lesões).</p>;
  const inicios = comData.map((l) => new Date(l.data_inicio!).getTime());
  const fim = Date.now();
  const ini = Math.min(...inicios);
  const span = Math.max(1, fim - ini);
  return (
    <div style={{ marginTop: espaco.md }}>
      <div style={{ fontSize: "0.72rem", color: SUAVE, marginBottom: 4 }}>Disponibilidade (verde) vs lesionado (vermelho)</div>
      <div style={{ position: "relative", height: 16, background: "#22c55e", borderRadius: 4, overflow: "hidden" }}>
        {comData.map((l) => {
          const a = new Date(l.data_inicio!).getTime();
          const b = l.data_fim ? new Date(l.data_fim).getTime() : fim;
          const left = ((a - ini) / span) * 100;
          const width = Math.max(1, ((b - a) / span) * 100);
          return <div key={l.id} title={`${l.data_inicio} → ${l.data_fim ?? "em curso"}`} style={{ position: "absolute", left: `${left}%`, width: `${width}%`, top: 0, bottom: 0, background: "#dc2626" }} />;
        })}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.66rem", color: SUAVE, marginTop: 2 }}>
        <span>{new Date(ini).toISOString().slice(0, 10)}</span><span>hoje</span>
      </div>
    </div>
  );
}

function Campo({ label, children }: { label: string; children: React.ReactNode }) {
  return <label style={{ display: "flex", flexDirection: "column", gap: 3, fontSize: "0.68rem", color: SUAVE }}>{label}{children}</label>;
}
function Badge({ estado }: { estado: string }) {
  const lesionado = estado === "lesionado";
  return <span style={{ fontSize: "0.72rem", fontWeight: 700, color: lesionado ? "#dc2626" : "#16a34a", background: lesionado ? "#fef2f2" : "#f0fdf4", border: `1px solid ${lesionado ? "#fecaca" : "#bbf7d0"}`, borderRadius: 999, padding: "2px 8px" }}>{lesionado ? "lesionado" : "disponível"}</span>;
}

const th: React.CSSProperties = { textAlign: "left", padding: "6px 8px", fontSize: "0.66rem", letterSpacing: "0.04em", textTransform: "uppercase", color: SUAVE, fontWeight: 600, whiteSpace: "nowrap" };
const td: React.CSSProperties = { padding: "6px 8px", verticalAlign: "middle" };
const verBtn: React.CSSProperties = { background: "transparent", border: "1px solid #cbd5e1", borderRadius: raio.sm, color: "#2563eb", fontSize: "0.75rem", padding: "3px 8px", cursor: "pointer" };
const acaoBtn = (cor: string): React.CSSProperties => ({ background: "transparent", border: `1px solid ${cor}`, borderRadius: raio.sm, color: cor, fontSize: "0.72rem", padding: "3px 8px", cursor: "pointer" });
