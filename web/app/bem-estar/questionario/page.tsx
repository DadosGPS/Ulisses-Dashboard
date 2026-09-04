"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { cores, espaco, raio } from "@/lib/theme";

// Os quatro sub-scores que o esquema/alertas usam. Cada um 1 (mau) a 5 (ótimo);
// o Hooper Index = Σ(5 − score) é calculado no backend.
const METRICAS = [
  { key: "sono", label: "Qualidade do Sono", emoji: "😴" },
  { key: "dor_musc", label: "Dor Muscular", emoji: "💪" },
  { key: "stress", label: "Stress", emoji: "😰" },
  { key: "humor", label: "Humor", emoji: "😊" },
] as const;

type Chave = (typeof METRICAS)[number]["key"];
type Scores = Record<Chave, number>;

interface Jogador {
  id: string;
  nome: string;
}

export default function WellnessQuestionnairePage() {
  const router = useRouter();
  const [teamId, setTeamId] = useState<string | null>(null);
  const [jogadores, setJogadores] = useState<Jogador[]>([]);
  const [carregado, setCarregado] = useState(false);

  const [playerId, setPlayerId] = useState("");
  const [data, setData] = useState(() => new Date().toISOString().slice(0, 10));
  const [scores, setScores] = useState<Scores>({ sono: 3, dor_musc: 3, stress: 3, humor: 3 });
  const [notas, setNotas] = useState("");

  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const supabase = createClient();
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        const { data: membro } = await supabase
          .from("team_members").select("team_id").eq("user_id", user.id).limit(1).single();
        if (membro) {
          setTeamId(membro.team_id);
          const { data: js } = await supabase
            .from("players").select("id, nome").eq("team_id", membro.team_id).eq("ativo", true).order("nome");
          if (js) setJogadores(js as Jogador[]);
        }
      }
      setCarregado(true);
    })();
  }, []);

  const totalScore = (scores.sono + scores.dor_musc + scores.stress + scores.humor) / 4;

  async function handleSubmit() {
    setErro(null);
    if (!playerId) { setErro("Escolhe o jogador."); return; }
    if (!teamId) { setErro("Sem equipa associada."); return; }
    setLoading(true);
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) { setErro("Sessão expirada. Volta a entrar."); return; }
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/wellness`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ player_id: playerId, data, ...scores, notas }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => null);
        setErro(d?.detail ?? "Não foi possível registar o bem-estar.");
        return;
      }
      setSubmitted(true);
      setTimeout(() => router.push("/dashboard"), 1800);
    } catch {
      setErro("Não foi possível ligar à API.");
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: cores.bg, padding: espaco.xl }}>
        <div style={{ textAlign: "center", background: cores.bgElevado, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.xxl }}>
          <div style={{ fontSize: "3rem", marginBottom: espaco.lg }}>✅</div>
          <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: cores.sucesso, marginBottom: espaco.md }}>Obrigado!</h2>
          <p style={{ color: cores.textoSuave, fontSize: "1rem" }}>Bem-estar registado. A redirecionar…</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: cores.bg, padding: espaco.lg }}>
      <div style={{ maxWidth: 600, margin: "0 auto", marginBottom: espaco.xl, textAlign: "center" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, color: "white", marginBottom: espaco.md }}>Questionário de Bem-Estar</h1>
        <p style={{ fontSize: "1rem", color: cores.textoSuave }}>Como te sentes hoje? (1 = Muito Mau · 5 = Excelente)</p>
      </div>

      {/* Jogador + data */}
      <div style={{ maxWidth: 600, margin: "0 auto", marginBottom: espaco.xl, display: "flex", gap: espaco.md, flexWrap: "wrap" }}>
        <select
          value={playerId}
          onChange={(e) => setPlayerId(e.target.value)}
          disabled={!carregado || jogadores.length === 0}
          style={{ ...campo, flex: "1 1 260px" }}
          aria-label="Jogador"
        >
          <option value="">{!carregado ? "A carregar…" : jogadores.length === 0 ? "Sem jogadores" : "Escolhe o jogador"}</option>
          {jogadores.map((j) => (
            <option key={j.id} value={j.id}>{j.nome}</option>
          ))}
        </select>
        <input type="date" value={data} onChange={(e) => setData(e.target.value)} style={{ ...campo, flex: "0 0 160px" }} aria-label="Data" />
      </div>

      {/* Métricas */}
      <div style={{ maxWidth: 600, margin: "0 auto", marginBottom: espaco.xl }}>
        {METRICAS.map((m) => (
          <div key={m.key} style={{ background: cores.bgElevado, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.lg, marginBottom: espaco.lg }}>
            <div style={{ display: "flex", alignItems: "center", gap: espaco.md, marginBottom: espaco.md }}>
              <span style={{ fontSize: "2rem" }}>{m.emoji}</span>
              <h3 style={{ fontSize: "1.125rem", fontWeight: 700, color: "white" }}>{m.label}</h3>
              <div style={{ marginLeft: "auto", fontSize: "1.5rem", fontWeight: 700, color: cores.destaque }}>{scores[m.key]}/5</div>
            </div>
            <input
              type="range" min="1" max="5" step="1" value={scores[m.key]}
              onChange={(e) => setScores({ ...scores, [m.key]: parseInt(e.currentTarget.value) })}
              style={{ width: "100%", height: 8, borderRadius: 4, background: cores.bg, outline: "none", WebkitAppearance: "none" }}
            />
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: espaco.sm, fontSize: "0.75rem", color: cores.textoSuave }}>
              <span>Muito Mau</span><span>Mau</span><span>Normal</span><span>Bom</span><span>Excelente</span>
            </div>
          </div>
        ))}
      </div>

      {/* Notas */}
      <div style={{ maxWidth: 600, margin: "0 auto", marginBottom: espaco.xl }}>
        <div style={{ background: cores.bgElevado, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.lg }}>
          <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "white", marginBottom: espaco.md }}>Notas Adicionais (opcional)</h3>
          <textarea
            value={notas} onChange={(e) => setNotas(e.currentTarget.value)}
            placeholder="Alguma observação?"
            style={{ width: "100%", minHeight: 90, padding: espaco.md, borderRadius: raio.sm, background: cores.bg, border: `1px solid ${cores.borda}`, color: "white", fontSize: "1rem", fontFamily: "inherit", resize: "none" }}
          />
        </div>
      </div>

      {/* Resumo */}
      <div style={{ maxWidth: 600, margin: "0 auto", marginBottom: espaco.xl }}>
        <div style={{ background: totalScore >= 4 ? "rgba(34,197,94,0.12)" : totalScore >= 3 ? "rgba(234,179,8,0.12)" : "rgba(239,68,68,0.12)", border: `1px solid ${totalScore >= 4 ? cores.sucesso : totalScore >= 3 ? cores.atencao : cores.cargaInterna}`, borderRadius: raio.md, padding: espaco.lg, textAlign: "center" }}>
          <div style={{ fontSize: "0.875rem", color: cores.textoSuave, marginBottom: espaco.sm }}>Bem-estar geral</div>
          <div style={{ fontSize: "2.5rem", fontWeight: 700, color: totalScore >= 4 ? cores.sucesso : totalScore >= 3 ? cores.atencao : cores.cargaInterna, marginBottom: espaco.sm }}>{totalScore.toFixed(1)}/5</div>
          <div style={{ fontSize: "0.875rem", color: cores.textoSuave }}>
            {totalScore >= 4 ? "Excelente estado" : totalScore >= 3 ? "Estado normal" : "Necessário descanso"}
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 600, margin: "0 auto" }}>
        {erro && <p style={{ color: cores.perigo, fontSize: "0.9rem", fontWeight: 600, marginBottom: espaco.md, textAlign: "center" }}>{erro}</p>}
        <button
          onClick={handleSubmit} disabled={loading}
          style={{ width: "100%", padding: `${espaco.lg}px ${espaco.xl}px`, borderRadius: raio.md, background: cores.sucesso, color: "white", border: "none", fontSize: "1.125rem", fontWeight: 700, cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.7 : 1 }}
        >
          {loading ? "A enviar…" : "Enviar Bem-Estar"}
        </button>
      </div>

      <style>{`
        input[type="range"]::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; width: 24px; height: 24px; border-radius: 50%; background: ${cores.cargaInterna}; cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
        input[type="range"]::-moz-range-thumb { width: 24px; height: 24px; border-radius: 50%; background: ${cores.cargaInterna}; cursor: pointer; border: none; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
      `}</style>
    </div>
  );
}

const campo: React.CSSProperties = {
  background: cores.bgElevado,
  border: `1px solid ${cores.borda}`,
  borderRadius: raio.sm,
  color: "white",
  padding: "10px 12px",
  fontSize: "0.95rem",
  fontWeight: 600,
};
