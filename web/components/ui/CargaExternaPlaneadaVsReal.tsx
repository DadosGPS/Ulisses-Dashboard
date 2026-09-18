"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { espaco, raio } from "@/lib/theme";
import type { CargaSemanaResponse } from "@/lib/types";

// Estilo de relatório (fundo branco).
const TINTA = "#1e293b";
const TINTA_SUAVE = "#334155";
const GRELHA = "#e2e8f0";
const COR_PLANEADO = "#2563eb";
const COR_REAL = "#d97706";

type MetricaChave = "distancia_m" | "hsr_m" | "sprint_m";
const METRICAS: { chave: MetricaChave; label: string; unidade: string }[] = [
  { chave: "distancia_m", label: "Distância Total", unidade: "m" },
  { chave: "hsr_m", label: "HSR", unidade: "m" },
  { chave: "sprint_m", label: "Sprint", unidade: "m" },
];

export function CargaExternaPlaneadaVsReal({ teamId, dadosIniciais }: { teamId: string; dadosIniciais: CargaSemanaResponse }) {
  const [dados, setDados] = useState(dadosIniciais);
  const [metrica, setMetrica] = useState<MetricaChave>("distancia_m");
  const [aCarregar, setACarregar] = useState(false);

  async function token() {
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    return session?.access_token ?? null;
  }

  async function mudarMicrociclo(mc: number) {
    setACarregar(true);
    const t = await token();
    if (!t) { setACarregar(false); return; }
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/planeamento/carga-semana?microciclo=${mc}`, {
        headers: { Authorization: `Bearer ${t}` },
      });
      if (res.ok) setDados(await res.json());
    } finally {
      setACarregar(false);
    }
  }

  async function guardar(diaMd: string, chave: MetricaChave, valor: number | null) {
    if (dados.microciclo === null) return;
    const dia = dados.dias.find((d) => d.dia_md === diaMd);
    if (!dia) return;
    const planeado = { ...dia.planeado, [chave]: valor };
    const t = await token();
    if (!t) return;
    // Atualização otimista.
    setDados((atual) => ({
      ...atual,
      dias: atual.dias.map((d) => (d.dia_md === diaMd ? { ...d, planeado } : d)),
    }));
    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/planeamento/carga-planeada`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${t}` },
      body: JSON.stringify({ microciclo: dados.microciclo, dia_md: diaMd, ...planeado }),
    });
  }

  if (!dados.tem_dados) return null;

  const cfg = METRICAS.find((m) => m.chave === metrica)!;
  const dias = dados.dias;

  return (
    <div style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: raio.md, padding: espaco.md }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: espaco.md, flexWrap: "wrap", marginBottom: espaco.md }}>
        <div style={{ display: "flex", alignItems: "center", gap: espaco.sm, flexWrap: "wrap" }}>
          <label style={{ fontSize: "0.82rem", fontWeight: 600, color: TINTA_SUAVE }}>Métrica:</label>
          <select
            value={metrica}
            onChange={(e) => setMetrica(e.target.value as MetricaChave)}
            style={{ background: "#ffffff", border: "1px solid #cbd5e1", borderRadius: raio.sm, color: TINTA, fontSize: "0.85rem", padding: "6px 10px" }}
          >
            {METRICAS.map((m) => <option key={m.chave} value={m.chave}>{m.label}</option>)}
          </select>
        </div>
        {dados.microciclos_disponiveis.length > 0 && (
          <select
            value={dados.microciclo ?? ""}
            disabled={aCarregar}
            onChange={(e) => mudarMicrociclo(Number(e.target.value))}
            style={{ background: "#ffffff", border: "1px solid #cbd5e1", borderRadius: raio.sm, color: TINTA, padding: "6px 10px", fontSize: "0.85rem", fontWeight: 600 }}
          >
            {dados.microciclos_disponiveis.map((mc) => <option key={mc} value={mc}>Semana {mc}</option>)}
          </select>
        )}
      </div>

      <div style={{ opacity: aCarregar ? 0.5 : 1 }}>
        <PlotlyChart
          titulo={`Planeado vs Real — ${cfg.label}`}
          data={[
            {
              x: dias.map((d) => d.dia_md),
              y: dias.map((d) => d.planeado[metrica]),
              type: "bar", name: "Planeado", marker: { color: COR_PLANEADO },
            },
            {
              x: dias.map((d) => d.dia_md),
              y: dias.map((d) => d.real[metrica]),
              type: "bar", name: "Real", marker: { color: COR_REAL },
            },
          ]}
          layout={{
            paper_bgcolor: "#ffffff", plot_bgcolor: "#ffffff",
            font: { family: "Inter, Segoe UI, Arial, sans-serif", color: TINTA },
            barmode: "group",
            legend: { orientation: "h", y: 1.12, font: { color: TINTA_SUAVE } },
            xaxis: { title: { text: "Dia do Microciclo" }, tickfont: { size: 11, color: TINTA_SUAVE } },
            yaxis: { title: { text: `${cfg.label} (${cfg.unidade})` }, gridcolor: GRELHA, tickfont: { size: 11, color: TINTA_SUAVE }, zeroline: false },
            margin: { l: 60, r: 20, t: 36, b: 40 },
          }}
          altura={260}
        />
      </div>

      <p style={{ fontSize: "0.75rem", color: "#64748b", margin: `${espaco.md}px 0 ${espaco.sm}px` }}>
        Define o alvo de cada dia (Planeado). O Real é a média por sessão de treino registada nos uploads dessa semana.
      </p>
      <div style={{ overflowX: "auto" }}>
        <table style={{ borderCollapse: "collapse", fontSize: "0.8rem", minWidth: 420 }}>
          <thead>
            <tr>
              <th style={th}>Dia</th>
              {METRICAS.map((m) => <th key={m.chave} style={th}>{m.label} ({m.unidade})</th>)}
            </tr>
          </thead>
          <tbody>
            {dias.map((d) => (
              <tr key={d.dia_md} style={{ borderTop: "1px solid #e2e8f0" }}>
                <td style={{ ...td, fontWeight: 600, color: TINTA }}>{d.dia_md}</td>
                {METRICAS.map((m) => (
                  <td key={m.chave} style={td}>
                    <input
                      type="number"
                      min={0}
                      step={10}
                      defaultValue={d.planeado[m.chave] ?? ""}
                      placeholder={d.real[m.chave] != null ? `real ${d.real[m.chave]}` : "—"}
                      onBlur={(e) => {
                        const raw = e.target.value.trim();
                        const v = raw === "" ? null : parseFloat(raw);
                        if (v === null || !Number.isNaN(v)) {
                          if (v !== d.planeado[m.chave]) guardar(d.dia_md, m.chave, v);
                        }
                      }}
                      style={{ width: 90, background: "#ffffff", border: "1px solid #cbd5e1", borderRadius: raio.sm, color: TINTA, padding: "5px 6px", fontSize: "0.8rem" }}
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const th: React.CSSProperties = { textAlign: "left", padding: "6px 10px", fontSize: "0.68rem", letterSpacing: "0.04em", textTransform: "uppercase", color: TINTA_SUAVE, fontWeight: 600, whiteSpace: "nowrap" };
const td: React.CSSProperties = { padding: "6px 10px", verticalAlign: "middle" };
