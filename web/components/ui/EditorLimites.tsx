"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { cores, espaco, raio } from "@/lib/theme";

export type Limites = Record<string, number>;

const PARES: { label: string; unidade: string; alto: string; muito: string }[] = [
  { label: "ACWR", unidade: "", alto: "acwr_alto", muito: "acwr_muito_alto" },
  { label: "Δ Carga semanal", unidade: "%", alto: "carga_change_alto", muito: "carga_change_muito_alto" },
  { label: "Δ Wellness (Hooper)", unidade: "%", alto: "wellness_change_alto", muito: "wellness_change_muito_alto" },
  { label: "Δ HSR", unidade: "%", alto: "hsr_change_alto", muito: "hsr_change_muito_alto" },
  { label: "Queda de velocidade", unidade: "%", alto: "velocidade_queda_alto", muito: "velocidade_queda_muito_alto" },
];

// Zonas de exposição da SEMANA (carga acumulada do microciclo ÷ jogo mais
// exigente). Fora do intervalo [baixo, alto] gera aviso no dashboard.
const ZONAS_SEMANA: { label: string; baixo: string; alto: string }[] = [
  { label: "HSR semana ÷ jogo", baixo: "hsr_semana_baixo", alto: "hsr_semana_alto" },
  { label: "Sprint semana ÷ jogo", baixo: "sprint_semana_baixo", alto: "sprint_semana_alto" },
];

// Limiares de valor único (um só limiar). "dados_horas" alimenta o dashboard;
// os restantes alimentam a deteção de risco da página Análise.
const SIMPLES: { label: string; unidade: string; chave: string; step: string }[] = [
  { label: "Wellness em risco (Hooper)", unidade: "índice ≥", chave: "hooper_alto", step: "0.5" },
  { label: "Jogador sem dados", unidade: "dias ≥", chave: "dias_sem_dados", step: "1" },
  { label: "Queda de velocidade sustentada", unidade: "% ≥", chave: "velocidade_queda_sustentada", step: "0.5" },
];

/** Edição dos limiares de alerta. Cada métrica tem um limiar de "atenção" e
 * outro de "atenção alta"; a partir deles os alertas do dashboard mudam. */
export function EditorLimites({ teamId, iniciais }: { teamId: string; iniciais: Limites }) {
  const [vals, setVals] = useState<Limites>(iniciais);
  const [aGuardar, setAGuardar] = useState(false);
  const [msg, setMsg] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);

  function set(k: string, v: string) {
    setVals((a) => ({ ...a, [k]: v === "" ? NaN : Number(v) }));
    setMsg(null);
  }

  async function guardar() {
    setAGuardar(true);
    setMsg(null);
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) { setMsg({ tipo: "erro", texto: "Sessão expirada." }); return; }
      const limpos: Limites = {};
      for (const [k, v] of Object.entries(vals)) if (Number.isFinite(v)) limpos[k] = v;
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/configuracoes/limites`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(limpos),
      });
      if (res.ok) {
        setVals(await res.json());
        setMsg({ tipo: "ok", texto: "Guardado. Os alertas do dashboard e da Análise passam a usar estes limiares." });
      } else {
        setMsg({ tipo: "erro", texto: "Não foi possível guardar." });
      }
    } finally {
      setAGuardar(false);
    }
  }

  return (
    <div style={{ maxWidth: 640 }}>
      <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, overflow: "hidden" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 1fr", gap: 0, background: "rgba(255,255,255,0.04)", padding: `9px ${espaco.md}px` }}>
          <span style={cab}>Métrica</span>
          <span style={{ ...cab, textAlign: "center", color: cores.atencao }}>Atenção ≥</span>
          <span style={{ ...cab, textAlign: "center", color: cores.cargaInterna }}>Atenção alta ≥</span>
        </div>
        {PARES.map((p) => (
          <div key={p.alto} style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 1fr", gap: 0, alignItems: "center", padding: `8px ${espaco.md}px`, borderTop: `1px solid ${cores.borda}` }}>
            <span style={{ fontSize: "0.85rem", color: "rgba(255,255,255,0.9)", fontWeight: 600 }}>{p.label} {p.unidade && <span style={{ color: cores.textoSuave, fontWeight: 400 }}>({p.unidade})</span>}</span>
            <input type="number" step="0.1" value={fmt(vals[p.alto])} onChange={(e) => set(p.alto, e.target.value)} style={inp} />
            <input type="number" step="0.1" value={fmt(vals[p.muito])} onChange={(e) => set(p.muito, e.target.value)} style={inp} />
          </div>
        ))}
        <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 1fr", gap: 0, alignItems: "center", padding: `8px ${espaco.md}px`, borderTop: `1px solid ${cores.borda}` }}>
          <span style={{ fontSize: "0.85rem", color: "rgba(255,255,255,0.9)", fontWeight: 600 }}>Dados em falta <span style={{ color: cores.textoSuave, fontWeight: 400 }}>(horas)</span></span>
          <input type="number" step="1" value={fmt(vals["dados_horas"])} onChange={(e) => set("dados_horas", e.target.value)} style={inp} />
          <span />
        </div>
      </div>

      <p style={{ fontSize: "0.78rem", color: cores.textoSuave, margin: `${espaco.lg}px 0 ${espaco.sm}px` }}>
        Deteção de risco da página <strong style={{ color: "rgba(255,255,255,0.85)" }}>Análise</strong> — o mesmo motor de alertas do dashboard.
      </p>
      <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, overflow: "hidden" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1.9fr 1fr", gap: 0, background: "rgba(255,255,255,0.04)", padding: `9px ${espaco.md}px` }}>
          <span style={cab}>Sinal</span>
          <span style={{ ...cab, textAlign: "center", color: cores.atencao }}>Limiar</span>
        </div>
        {SIMPLES.map((s) => (
          <div key={s.chave} style={{ display: "grid", gridTemplateColumns: "1.9fr 1fr", gap: 0, alignItems: "center", padding: `8px ${espaco.md}px`, borderTop: `1px solid ${cores.borda}` }}>
            <span style={{ fontSize: "0.85rem", color: "rgba(255,255,255,0.9)", fontWeight: 600 }}>{s.label} {s.unidade && <span style={{ color: cores.textoSuave, fontWeight: 400 }}>({s.unidade})</span>}</span>
            <input type="number" step={s.step} value={fmt(vals[s.chave])} onChange={(e) => set(s.chave, e.target.value)} style={inp} />
          </div>
        ))}
      </div>

      <p style={{ fontSize: "0.78rem", color: cores.textoSuave, margin: `${espaco.lg}px 0 ${espaco.sm}px` }}>
        Exposição da <strong style={{ color: "rgba(255,255,255,0.85)" }}>semana</strong> (carga acumulada do microciclo) face ao jogo mais exigente. Fora do intervalo de referência gera aviso no dashboard.
      </p>
      <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, overflow: "hidden" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 1fr", gap: 0, background: "rgba(255,255,255,0.04)", padding: `9px ${espaco.md}px` }}>
          <span style={cab}>Métrica</span>
          <span style={{ ...cab, textAlign: "center", color: cores.info }}>Baixo &lt;</span>
          <span style={{ ...cab, textAlign: "center", color: cores.atencao }}>Elevado &gt;</span>
        </div>
        {ZONAS_SEMANA.map((z) => (
          <div key={z.baixo} style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 1fr", gap: 0, alignItems: "center", padding: `8px ${espaco.md}px`, borderTop: `1px solid ${cores.borda}` }}>
            <span style={{ fontSize: "0.85rem", color: "rgba(255,255,255,0.9)", fontWeight: 600 }}>{z.label} <span style={{ color: cores.textoSuave, fontWeight: 400 }}>(×)</span></span>
            <input type="number" step="0.05" value={fmt(vals[z.baixo])} onChange={(e) => set(z.baixo, e.target.value)} style={inp} />
            <input type="number" step="0.05" value={fmt(vals[z.alto])} onChange={(e) => set(z.alto, e.target.value)} style={inp} />
          </div>
        ))}
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: espaco.md, marginTop: espaco.lg }}>
        <button onClick={guardar} disabled={aGuardar} style={{ background: cores.sucesso, color: "white", border: "none", borderRadius: raio.sm, padding: "9px 18px", fontSize: "0.85rem", fontWeight: 700, cursor: "pointer", opacity: aGuardar ? 0.6 : 1 }}>
          {aGuardar ? "A guardar…" : "Guardar limiares"}
        </button>
        {msg && <span style={{ fontSize: "0.82rem", fontWeight: 600, color: msg.tipo === "ok" ? cores.sucesso : cores.perigo }}>{msg.texto}</span>}
      </div>
    </div>
  );
}

const fmt = (v: number | undefined) => (v === undefined || Number.isNaN(v) ? "" : String(v));
const cab: React.CSSProperties = { fontSize: "0.62rem", letterSpacing: "0.06em", textTransform: "uppercase", color: cores.textoSuave, fontWeight: 600 };
const inp: React.CSSProperties = { width: "100%", maxWidth: 110, justifySelf: "center", background: cores.bg, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: "white", fontSize: "0.85rem", padding: "6px 8px", textAlign: "center" };
