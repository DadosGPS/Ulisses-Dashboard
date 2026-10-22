"use client";

import { useMemo, useState } from "react";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { espaco, raio, cores } from "@/lib/theme";
import type { MapaCalorResponse } from "@/lib/types";
import { useTr } from "@/lib/i18n/cliente";

// Cores do tema (escuro/claro).
const TINTA = cores.texto;
const TINTA_SUAVE = cores.textoSuave;

type Linha = { jogador: string; valores: Record<string, number | null> };

// Mistura a cor da escala com o fundo do cartão (funciona nos dois temas).
function mistura(cor: string, t: number) {
  return `color-mix(in srgb, ${cor} ${Math.round(Math.max(0, Math.min(1, t)) * 100)}%, var(--bg-cartao))`;
}
const AZUL = "rgb(37, 99, 235)";
const VERMELHO = "rgb(220, 38, 38)";

// Cor de fundo da célula conforme o tipo da métrica.
function corCelula(v: number | null, tipo: string, min: number, max: number): { bg: string; fg: string } {
  if (v === null || v === undefined || Number.isNaN(v)) return { bg: cores.superficie, fg: cores.textoFraco };

  if (tipo === "diverging") {
    // Variação semanal: azul (desce) → neutro (0) → vermelho (sobe). Limita a ±50%.
    const t = Math.max(-1, Math.min(1, v / 50));
    const k = Math.abs(t);
    return { bg: mistura(t >= 0 ? VERMELHO : AZUL, k), fg: k > 0.55 ? "#ffffff" : TINTA };
  }

  // sequential / ratio: neutro → azul, escalado ao min–max da métrica.
  const span = max - min || 1;
  const t = Math.max(0, Math.min(1, (v - min) / span));
  return { bg: mistura(AZUL, t), fg: t > 0.55 ? "#ffffff" : TINTA };
}

export function MapaCalorEpoca({ dados }: { dados: MapaCalorResponse }) {
  const tr = useTr();
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
    return <p style={{ color: cores.textoSuave, fontSize: "0.85rem" }}>{tr("Sem dados suficientes para o mapa de calor.")}</p>;
  }

  const celW = 46;
  const nomeW = 150;

  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
      <div style={{ display: "flex", alignItems: "center", gap: espaco.md, flexWrap: "wrap", marginBottom: espaco.md }}>
        <label style={{ fontSize: "0.82rem", fontWeight: 600, color: TINTA_SUAVE }}>{tr("Métrica:")}</label>
        <select
          value={metrica}
          onChange={(e) => setMetrica(e.target.value)}
          style={{ background: cores.bgCartao, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: TINTA, fontSize: "0.85rem", padding: "6px 10px" }}
        >
          {dados.metricas.map((m) => (
            <option key={m.chave} value={m.chave}>{tr(m.label)}</option>
          ))}
        </select>
        <span style={{ fontSize: "0.75rem", color: cores.textoSuave }}>
          {cfg?.tipo === "diverging"
            ? tr("Azul = menos que a semana anterior · Vermelho = mais")
            : tr("Mais claro = valor mais baixo · Mais escuro = mais alto")}
        </span>
      </div>

      <div style={{ overflowX: "auto" }}>
        <table style={{ borderCollapse: "separate", borderSpacing: 2 }}>
          <thead>
            <tr>
              <th style={{ position: "sticky", left: 0, background: cores.bgCartao, zIndex: 1, minWidth: nomeW, textAlign: "left", padding: "4px 8px", fontSize: "0.72rem", color: TINTA_SUAVE }}>
                {tr("Jogador")}</th>
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
                <td style={{ position: "sticky", left: 0, background: cores.bgCartao, zIndex: 1, minWidth: nomeW, padding: "4px 8px", fontSize: "0.78rem", fontWeight: 600, color: TINTA, whiteSpace: "nowrap" }}>
                  {nomeOuOculto(l.jogador, oculto)}
                </td>
                {dados.microciclos.map((mc) => {
                  const v = l.valores[String(mc)];
                  const { bg, fg } = corCelula(v ?? null, cfg?.tipo ?? "sequential", min, max);
                  const txt = v === null || v === undefined ? "" : v.toLocaleString(tr.loc, { maximumFractionDigits: cfg?.casas ?? 0 });
                  return (
                    <td
                      key={mc}
                      title={tr("{0} · Semana {1}: {2}{3}", [l.jogador, mc, txt || "—", txt && cfg?.unidade ? " " + cfg.unidade : ""])}
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
      <p style={{ fontSize: "0.72rem", color: cores.textoSuave, marginTop: espaco.sm }}>
        {tr("Colunas = microciclos (semanas).")}{" "}{cfg?.label}{cfg?.unidade ? ` (${cfg.unidade})` : ""}.
      </p>
    </div>
  );
}
