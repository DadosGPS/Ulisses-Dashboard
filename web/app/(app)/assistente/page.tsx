"use client";

import { useEffect, useRef, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { PageHeader } from "@/components/layout/PageHeader";
import { cores, espaco, raio } from "@/lib/theme";

interface Msg {
  role: "user" | "assistant";
  content: string;
}

const SUGESTOES = [
  "Resume a semana para o treinador.",
  "Quem precisa de atenção antes do próximo jogo?",
  "Que jogadores estão pouco expostos ao sprint?",
  "Como está a exposição de HSR face ao jogo?",
];

export default function AssistentePage() {
  const [teamId, setTeamId] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const fimRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    (async () => {
      const supabase = createClient();
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;
      const { data } = await supabase.from("team_members").select("team_id").eq("user_id", user.id).limit(1).single();
      if (data) setTeamId(data.team_id);
    })();
  }, []);

  useEffect(() => { fimRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, loading]);

  async function token(): Promise<string | null> {
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    return session?.access_token ?? null;
  }

  async function gerarResumo() {
    if (!teamId || loading) return;
    setErro(null); setLoading(true);
    setMsgs((m) => [...m, { role: "user", content: "📋 Resumo para o treinador" }]);
    try {
      const t = await token();
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/ia/resumo`, {
        method: "POST", headers: { Authorization: `Bearer ${t}` },
      });
      const d = await res.json().catch(() => null);
      if (!res.ok) { setErro(d?.detail ?? "Assistente indisponível."); return; }
      setMsgs((m) => [...m, { role: "assistant", content: d.resposta }]);
    } catch { setErro("Não foi possível ligar à API."); }
    finally { setLoading(false); }
  }

  async function enviar(texto?: string) {
    const pergunta = (texto ?? input).trim();
    if (!pergunta || !teamId || loading) return;
    setErro(null); setInput("");
    const historico = msgs.slice(-10);
    setMsgs((m) => [...m, { role: "user", content: pergunta }]);
    setLoading(true);
    try {
      const t = await token();
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/ia/perguntar`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${t}` },
        body: JSON.stringify({ pergunta, historico }),
      });
      const d = await res.json().catch(() => null);
      if (!res.ok) { setErro(d?.detail ?? "Assistente indisponível."); return; }
      setMsgs((m) => [...m, { role: "assistant", content: d.resposta }]);
    } catch { setErro("Não foi possível ligar à API."); }
    finally { setLoading(false); }
  }

  return (
    <div>
      <PageHeader titulo="Assistente" subtitulo="Apoio à decisão sobre carga — apoio, não substitui o teu julgamento" />
      <div style={{ maxWidth: 820, margin: "0 auto", padding: `${espaco.lg}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        <div style={{ display: "flex", gap: espaco.sm, flexWrap: "wrap", marginBottom: espaco.lg }}>
          <button onClick={gerarResumo} disabled={loading || !teamId} style={btnPrimario}>📋 Resumo para o treinador</button>
        </div>

        {msgs.length === 0 && (
          <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.lg, marginBottom: espaco.lg }}>
            <p style={{ color: cores.textoSuave, fontSize: "0.85rem", margin: `0 0 ${espaco.md}px` }}>Pergunta o que quiseres sobre a carga da equipa. Por exemplo:</p>
            <div style={{ display: "flex", gap: espaco.sm, flexWrap: "wrap" }}>
              {SUGESTOES.map((s) => (
                <button key={s} onClick={() => enviar(s)} disabled={loading || !teamId} style={chip}>{s}</button>
              ))}
            </div>
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: espaco.md, marginBottom: espaco.lg }}>
          {msgs.map((m, i) => (
            <div key={i} style={{ alignSelf: m.role === "user" ? "flex-end" : "flex-start", maxWidth: "88%" }}>
              <div style={{
                background: m.role === "user" ? cores.destaque : cores.bgCartao,
                border: `1px solid ${m.role === "user" ? cores.destaque : cores.borda}`,
                borderRadius: raio.md, padding: `${espaco.md}px ${espaco.lg}px`,
                color: "white", fontSize: "0.9rem", lineHeight: 1.5, whiteSpace: "pre-wrap",
              }}>
                {m.content}
              </div>
            </div>
          ))}
          {loading && <div style={{ alignSelf: "flex-start", color: cores.textoSuave, fontSize: "0.85rem" }}>A analisar…</div>}
          {erro && <div style={{ color: cores.perigo, fontSize: "0.85rem", fontWeight: 600 }}>{erro}</div>}
          <div ref={fimRef} />
        </div>

        <div style={{ display: "flex", gap: espaco.sm, position: "sticky", bottom: espaco.md }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") enviar(); }}
            placeholder={teamId ? "Escreve uma pergunta…" : "A carregar equipa…"}
            disabled={loading || !teamId}
            style={{ flex: 1, background: cores.bgCartao, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: "white", padding: "11px 14px", fontSize: "0.9rem" }}
          />
          <button onClick={() => enviar()} disabled={loading || !teamId || !input.trim()} style={btnPrimario}>Enviar</button>
        </div>

        <p style={{ color: cores.textoFraco, fontSize: "0.72rem", marginTop: espaco.md }}>
          As respostas são apoio à decisão a partir dos dados da equipa. Não são diagnóstico médico nem previsão de lesão.
        </p>
      </div>
    </div>
  );
}

const btnPrimario: React.CSSProperties = {
  background: cores.cargaInterna, color: "white", border: "none", borderRadius: raio.sm,
  padding: "10px 16px", fontSize: "0.85rem", fontWeight: 700, cursor: "pointer",
};
const chip: React.CSSProperties = {
  background: "transparent", color: cores.info, border: `1px solid ${cores.bordaForte}`,
  borderRadius: 999, padding: "6px 12px", fontSize: "0.8rem", fontWeight: 600, cursor: "pointer",
};
