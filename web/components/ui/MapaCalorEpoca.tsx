"use client";

import { useMemo, useState } from "react";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { espaco, raio } from "@/lib/theme";
import type { MapaCalorResponse } from "@/lib/types";

// Cores de relatório (fundo branco).
const TINTA = "#1e293b";
const TINTA_SUAVE = "#334155";

type Linha = { jogador: string; valores: Record<string, number | null> };

function lerp(a: number, b: number, t: number) {
  return Math.round(a + (b - a) * t);
}
function rgb(r: number, g: number, b: number) {
  return `rgb(${r}, ${g}, ${b})`;
}

// Cor de fundo da célula conforme o tipo da métrica.
function corCelula(v: number | null, tipo: string, min: number, max: number): { bg: string; fg: string } {
  if (v === null || v === undefined || Number.isNaN(v)) return { bg: "#f1f5f9", fg: "#94a3b8" };

  if (tipo === "diverging") {
    // Variação semanal: azul (desce) → branco (0) → vermelho (sobe). Limita a ±50%.
    const t = Math.max(-1, Math.min(1, v / 50));
    if (t >= 0) {
      const [r, g, b] = [lerp(255, 220, t), lerp(255, 38, t), lerp(255, 38, t)];
      return { bg: rgb(r, g, b), fg: t > 0.55 ? "#ffffff" : TINTA };
    }
    const t2 = -t;
    const [r, g, b] = [lerp(255, 37, t2), lerp(255, 99, t2), lerp(255, 235, t2)];
    return { bg: rgb(r, g, b), fg: t2 > 0.55 ? "#ffffff" : TINTA };
  }

  // sequential / ratio: branco → azul, escalado ao min–max da métrica.
  const span = max - min || 1;
  const t = Math.max(0, Math.min(1, (v - min) / span));
  const [r, g, b] = [lerp(255, 37, t), lerp(255, 99, t), lerp(255, 235, t)];
  return { bg: rgb(r, g, b), fg: t > 0.55 ? "#ffffff" : TINTA };
}

export function MapaCalorEpoca({ dados }: { dados: MapaCalorResponse }) {
  const { oculto } = usePrivacidade();
  const [metrica, setMetrica] = useState(dados.metricas[0]?.chave ?? "carga_interna");

  const cfg = dados.metricas.find((m) => m.chave === metrica) ?? dados.metricas[0];
  const linhas: Linha[] = dados.dados[metrica] ?? [];

  const [min, max] = useMemo(() => {
    const vals: number[] = [];
    for (const l of linhas) for (const mc of dados.microciclos) {
      const v = l.valores[String(mc)];
      if (v !== null && v !== undefined && !Number.isNaN(v)) vals.push(v);
    }
    if (vals.length === 0) return [0, 1];
    return [Math.min(...vals), Math.max(...vals)];
  }, [linhas, dados.microciclos]);

  if (!dados.tem_dados || dados.microciclos.length === 0) {
    return <p style={{ color: "#64748b", fontSize: "0.85rem" }}>Sem dados suficientes para o mapa de calor.</p>;
  }

  const celW = 46;
  const nomeW = 150;

  return (
    <div style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: raio.md, padding: espaco.md }}>
      <div style={{ display: "flex", alignItems: "center", gap: espaco.md, flexWrap: "wrap", marginBottom: espaco.md }}>
        <label style={{ fontSize: "0.82rem", fontWeight: 600, color: TINTA_SUAVE }}>Métrica:</label>
        <select
          value={metrica}
          onChange={(e) => setMetrica(e.target.value)}
          style={{ background: "#ffffff", border: "1px solid #cbd5e1", borderRadius: raio.sm, color: TINTA, fontSize: "0.85rem", padding: "6px 10px" }}
        >
          {dados.metricas.map((m) => (
            <option key={m.chave} value={m.chave}>{m.label}</option>
          ))}
        </select>
        <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
          {cfg?.tipo === "diverging"
            ? "Azul = menos que a semana anterior · Vermelho = mais"
            : "Mais claro = valor mais baixo · Mais escuro = mais alto"}
        </span>
      </div>

      <div style={{ overflowX: "auto" }}>
        <table style={{ borderCollapse: "separate", borderSpacing: 2 }}>
          <thead>
            <tr>
              <th style={{ position: "sticky", left: 0, background: "#ffffff", zIndex: 1, minWidth: nomeW, textAlign: "left", padding: "4px 8px", fontSize: "0.72rem", color: TINTA_SUAVE }}>
                Jogador
              </th>
              {dados.microciclos.map((mc) => (
                <th key={mc} style={{ minWidth: celW, width: celW, textAlign: "center", padding: "4px 0", fontSize: "0.7rem", color: TINTA_SUAVE, fontWeight: 600 }}>
                  {mc}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {linhas.map((l) => (
              <tr key={l.jogador}>
                <td style={{ position: "sticky", left: 0, background: "#ffffff", zIndex: 1, minWidth: nomeW, padding: "4px 8px", fontSize: "0.78rem", fontWeight: 600, color: TINTA, whiteSpace: "nowrap" }}>
                  {nomeOuOculto(l.jogador, oculto)}
                </td>
                {dados.microciclos.map((mc) => {
                  const v = l.valores[String(mc)];
                  const { bg, fg } = corCelula(v ?? null, cfg?.tipo ?? "sequential", min, max);
                  const txt = v === null || v === undefined ? "" : v.toLocaleString("pt-PT", { maximumFractionDigits: cfg?.casas ?? 0 });
                  return (
                    <td
                      key={mc}
                      title={`${l.jogador} · Semana ${mc}: ${txt || "—"}${txt && cfg?.unidade ? " " + cfg.unidade : ""}`}
                      style={{ minWidth: celW, width: celW, height: 28, textAlign: "center", background: bg, color: fg, fontSize: "0.68rem", borderRadius: 4 }}
                    >
                      {txt}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p style={{ fontSize: "0.72rem", color: "#64748b", marginTop: espaco.sm }}>
        Colunas = microciclos (semanas). {cfg?.label}{cfg?.unidade ? ` (${cfg.unidade})` : ""}.
      </p>
    </div>
  );
}
