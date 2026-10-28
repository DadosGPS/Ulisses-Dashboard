"use client";

import { useEffect, useState } from "react";
import { pedidoApi } from "@/lib/api-cliente";
import { createClient } from "@/lib/supabase/client";
import { cores, espaco, raio } from "@/lib/theme";
import { useTr, linguaDoCookie } from "@/lib/i18n/cliente";

export type Limites = Record<string, number>;

/** De onde vêm os limiares desta equipa (ver limites_service.origem_limites). */
type Origem = { tipo: "academia" | "pessoal"; escalao: string | null; excecao_escalao: boolean; e_head: boolean; protocolo_ativo: boolean };

const PARES: { label: string; unidade: string; alto: string; muito: string }[] = [
  { label: "ACWR", unidade: "", alto: "acwr_alto", muito: "acwr_muito_alto" },
  { label: "Δ Carga semanal", unidade: "%", alto: "carga_change_alto", muito: "carga_change_muito_alto" },
  { label: "Δ Wellness (Hooper)", unidade: "%", alto: "wellness_change_alto", muito: "wellness_change_muito_alto" },
  { label: "Δ HSR", unidade: "%", alto: "hsr_change_alto", muito: "hsr_change_muito_alto" },
  { label: "Queda de velocidade", unidade: "%", alto: "velocidade_queda_alto", muito: "velocidade_queda_muito_alto" },
  { label: "Queda do CMJ vs média própria", unidade: "%", alto: "cmj_queda_alto", muito: "cmj_queda_muito_alto" },
  { label: "Subida do Hooper vs média própria", unidade: "pontos", alto: "hooper_subida_alto", muito: "hooper_subida_muito_alto" },
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
  { label: "Wellness muito baixo (Hooper)", unidade: "índice ≥", chave: "hooper_alto", step: "0.5" },
  { label: "Jogador sem dados", unidade: "dias ≥", chave: "dias_sem_dados", step: "1" },
  { label: "Velocidade abaixo do recorde (melhor dos últimos 7 dias)", unidade: "% ≥", chave: "velocidade_queda_sustentada", step: "0.5" },
];

/** Edição dos limiares de alerta. Cada métrica tem um limiar de "atenção" e
 * outro de "atenção alta"; a partir deles os alertas do dashboard mudam. */
export function EditorLimites({ teamId, iniciais }: { teamId: string; iniciais: Limites }) {
  const tr = useTr();
  const [vals, setVals] = useState<Limites>(iniciais);
  const [aGuardar, setAGuardar] = useState(false);
  const [msg, setMsg] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);
  const [origem, setOrigem] = useState<Origem | null>(null);
  const [ambito, setAmbito] = useState<"academia" | "escalao">("academia");
  useEffect(() => {
    pedidoApi<Origem>(`/api/teams/${teamId}/configuracoes/limites/origem`)
      .then((o) => { setOrigem(o); if (o.excecao_escalao) setAmbito("escalao"); })
      .catch(() => setOrigem(null));
  }, [teamId]);
  const bloqueado = !!origem?.protocolo_ativo && !origem.e_head;

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
      if (!token) { setMsg({ tipo: "erro", texto: tr("Sessão expirada.") }); return; }
      const limpos: Limites = {};
      for (const [k, v] of Object.entries(vals)) if (Number.isFinite(v)) limpos[k] = v;
      const q = origem?.protocolo_ativo && ambito === "escalao" ? "?ambito=escalao" : "";
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/configuracoes/limites${q}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, "X-Lingua": linguaDoCookie() },
        body: JSON.stringify(limpos),
      });
      if (res.ok) {
        setVals(await res.json());
        setMsg({ tipo: "ok", texto: origem?.protocolo_ativo
          ? (ambito === "escalao" ? tr("Guardado como exceção do {0}.", [origem.escalao ?? ""]) : tr("Guardado no protocolo da academia — vale para todas as equipas."))
          : tr("Guardado. Os alertas do dashboard e da Análise passam a usar estes limiares.") });
      } else {
        const j = await res.json().catch(() => null);
        setMsg({ tipo: "erro", texto: j?.detail ?? tr("Não foi possível guardar.") });
      }
    } finally {
      setAGuardar(false);
    }
  }

  return (
    <div style={{ maxWidth: 640 }}>
      {origem?.protocolo_ativo && (
        <div role="status" style={{ marginBottom: espaco.lg, padding: espaco.md, borderRadius: raio.md, border: `1px solid ${cores.borda}`, borderLeft: `3px solid ${cores.info}`, background: cores.bgCartao, fontSize: "0.82rem", color: cores.texto }}>
          <strong>{tr("Protocolo da academia ativo.")}</strong>{" "}
          {origem.excecao_escalao ? tr("Esta equipa ({0}) tem uma exceção própria; o resto segue a base da academia.", [origem.escalao ?? ""]) : tr("Esta equipa usa os limiares comuns a todas as equipas da academia.")}
          {" "}{bloqueado ? tr("Só o responsável da academia os pode alterar.") : (
            <span style={{ display: "inline-flex", gap: espaco.sm, alignItems: "center", flexWrap: "wrap", marginTop: 6 }}>
              {tr("Guardar para:")}
              <label><input type="radio" name="ambito" checked={ambito === "academia"} onChange={() => setAmbito("academia")} /> {tr("todas as equipas")}</label>
              {origem.escalao && <label><input type="radio" name="ambito" checked={ambito === "escalao"} onChange={() => setAmbito("escalao")} /> {tr("só o {0}", [origem.escalao])}</label>}
            </span>
          )}
        </div>
      )}
      <fieldset disabled={bloqueado} style={{ border: "none", margin: 0, padding: 0, minWidth: 0, opacity: bloqueado ? 0.7 : 1 }}>
      <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, overflow: "hidden" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 1fr", gap: 0, background: "rgb(var(--ink) / 0.04)", padding: `9px ${espaco.md}px` }}>
          <span style={cab}>{tr("Métrica")}</span>
          <span style={{ ...cab, textAlign: "center", color: cores.atencao }}>{tr("Atenção ≥")}</span>
          <span style={{ ...cab, textAlign: "center", color: cores.cargaInterna }}>{tr("Atenção alta ≥")}</span>
        </div>
        {PARES.map((p) => (
          <div key={p.alto} style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 1fr", gap: 0, alignItems: "center", padding: `8px ${espaco.md}px`, borderTop: `1px solid ${cores.borda}` }}>
            <span style={{ fontSize: "0.85rem", color: "rgb(var(--ink) / 0.9)", fontWeight: 600 }}>{tr(p.label)} {p.unidade && <span style={{ color: cores.textoSuave, fontWeight: 400 }}>({tr(p.unidade)})</span>}</span>
            <input type="number" step="0.1" value={fmt(vals[p.alto])} onChange={(e) => set(p.alto, e.target.value)} style={inp} />
            <input type="number" step="0.1" value={fmt(vals[p.muito])} onChange={(e) => set(p.muito, e.target.value)} style={inp} />
          </div>
        ))}
        <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 1fr", gap: 0, alignItems: "center", padding: `8px ${espaco.md}px`, borderTop: `1px solid ${cores.borda}` }}>
          <span style={{ fontSize: "0.85rem", color: "rgb(var(--ink) / 0.9)", fontWeight: 600 }}>{tr("Dados em falta")}{" "}<span style={{ color: cores.textoSuave, fontWeight: 400 }}>{tr("(horas)")}</span></span>
          <input type="number" step="1" value={fmt(vals["dados_horas"])} onChange={(e) => set("dados_horas", e.target.value)} style={inp} />
          <span />
        </div>
      </div>

      <p style={{ fontSize: "0.78rem", color: cores.textoSuave, margin: `${espaco.lg}px 0 ${espaco.sm}px` }}>
        {tr("Deteção de risco da página")}{" "}<strong style={{ color: "rgb(var(--ink) / 0.85)" }}>{tr("Análise")}</strong> {tr("— o mesmo motor de alertas do dashboard.")}</p>
      <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, overflow: "hidden" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1.9fr 1fr", gap: 0, background: "rgb(var(--ink) / 0.04)", padding: `9px ${espaco.md}px` }}>
          <span style={cab}>{tr("Sinal")}</span>
          <span style={{ ...cab, textAlign: "center", color: cores.atencao }}>{tr("Limiar")}</span>
        </div>
        {SIMPLES.map((s) => (
          <div key={s.chave} style={{ display: "grid", gridTemplateColumns: "1.9fr 1fr", gap: 0, alignItems: "center", padding: `8px ${espaco.md}px`, borderTop: `1px solid ${cores.borda}` }}>
            <span style={{ fontSize: "0.85rem", color: "rgb(var(--ink) / 0.9)", fontWeight: 600 }}>{tr(s.label)} {s.unidade && <span style={{ color: cores.textoSuave, fontWeight: 400 }}>({tr(s.unidade)})</span>}</span>
            <input type="number" step={s.step} value={fmt(vals[s.chave])} onChange={(e) => set(s.chave, e.target.value)} style={inp} />
          </div>
        ))}
      </div>

      <p style={{ fontSize: "0.78rem", color: cores.textoSuave, margin: `${espaco.lg}px 0 ${espaco.sm}px` }}>
        {tr("Exposição da")}{" "}<strong style={{ color: "rgb(var(--ink) / 0.85)" }}>{tr("semana")}</strong> {tr("(carga acumulada do microciclo) face à referência de jogo (média por jogo completo da equipa dos últimos jogos completos). A meio da semana o limite inferior é proporcional às sessões já feitas. Fora do intervalo de referência gera aviso no dashboard.")}</p>
      <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, overflow: "hidden" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 1fr", gap: 0, background: "rgb(var(--ink) / 0.04)", padding: `9px ${espaco.md}px` }}>
          <span style={cab}>{tr("Métrica")}</span>
          <span style={{ ...cab, textAlign: "center", color: cores.info }}>{tr("Baixo &lt;")}</span>
          <span style={{ ...cab, textAlign: "center", color: cores.atencao }}>{tr("Elevado &gt;")}</span>
        </div>
        {ZONAS_SEMANA.map((z) => (
          <div key={z.baixo} style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 1fr", gap: 0, alignItems: "center", padding: `8px ${espaco.md}px`, borderTop: `1px solid ${cores.borda}` }}>
            <span style={{ fontSize: "0.85rem", color: "rgb(var(--ink) / 0.9)", fontWeight: 600 }}>{tr(z.label)} <span style={{ color: cores.textoSuave, fontWeight: 400 }}>(×)</span></span>
            <input type="number" step="0.05" value={fmt(vals[z.baixo])} onChange={(e) => set(z.baixo, e.target.value)} style={inp} />
            <input type="number" step="0.05" value={fmt(vals[z.alto])} onChange={(e) => set(z.alto, e.target.value)} style={inp} />
          </div>
        ))}
      </div>

      </fieldset>

      <div style={{ display: "flex", alignItems: "center", gap: espaco.md, marginTop: espaco.lg }}>
        {!bloqueado && <button onClick={guardar} disabled={aGuardar} style={{ background: cores.sucesso, color: "white", border: "none", borderRadius: raio.sm, padding: "9px 18px", fontSize: "0.85rem", fontWeight: 700, cursor: "pointer", opacity: aGuardar ? 0.6 : 1 }}>
          {aGuardar ? tr("A guardar…") : tr("Guardar limiares")}
        </button>}
        {msg && <span style={{ fontSize: "0.82rem", fontWeight: 600, color: msg.tipo === "ok" ? cores.sucesso : cores.perigo }}>{msg.texto}</span>}
      </div>
    </div>
  );
}

const fmt = (v: number | undefined) => (v === undefined || Number.isNaN(v) ? "" : String(v));
const cab: React.CSSProperties = { fontSize: "0.62rem", letterSpacing: "0.06em", textTransform: "uppercase", color: cores.textoSuave, fontWeight: 600 };
const inp: React.CSSProperties = { width: "100%", maxWidth: 110, justifySelf: "center", background: cores.bg, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: cores.textoForte, fontSize: "0.85rem", padding: "6px 8px", textAlign: "center" };
