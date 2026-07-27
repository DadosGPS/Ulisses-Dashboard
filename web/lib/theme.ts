/**
 * Paleta e template de gráficos — porta direta de utils/ui_safe.py
 * (aplicar_tema_graficos + as cores usadas em team_kpi_tile/ranking_metric_card).
 * Fonte de verdade visual: ver o plano de migração, secção "Componentes visuais".
 */

export const cores = {
  bg: "#0d1117",
  texto: "rgba(255,255,255,0.85)",
  textoSuave: "rgba(255,255,255,0.5)",
  borda: "rgba(255,255,255,0.08)",
  cartao: "rgba(255,255,255,0.02)",

  // Paleta de métricas (mesma usada em dashboard.py METRICAS / ui_safe.py)
  cargaInterna: "#e63946",
  distanciaTotal: "#2563eb",
  hsr: "#f59e0b",
  sprint: "#dc2626",
  velMax: "#8b5cf6",
  acc: "#14b8a6",
  dcc: "#10b981",

  sucesso: "#22c55e",
  perigo: "#ef4444",
} as const;

/** Layout partilhado por todos os gráficos Plotly.js (Fase 6+), equivalente
 * ao template "lm_professional" registado em aplicar_tema_graficos(). */
export const plotlyLayoutBase = {
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: { family: "Inter, Segoe UI, Arial, sans-serif", color: cores.texto },
  margin: { l: 50, r: 20, t: 55, b: 40 },
  xaxis: {
    showgrid: false,
    zeroline: false,
    linecolor: "rgba(255,255,255,0.16)",
    tickfont: { size: 10, color: cores.textoSuave },
  },
  yaxis: {
    showgrid: false,
    zeroline: false,
    linecolor: "rgba(255,255,255,0.16)",
    tickfont: { size: 10, color: cores.textoSuave },
  },
  colorway: ["#e63946", "#2563eb", "#10b981", "#f59e0b", "#8b5cf6", "#14b8a6", "#64748b"],
};

/** Converte 0..1 num sufixo hex de 2 dígitos — mesmo truque de utils/ui_safe.py
 * (_alpha_hex) para compor cores #RRGGBBAA em CSS. */
export function alphaHex(alpha: number): string {
  const v = Math.max(0, Math.min(255, Math.round(alpha * 255)));
  return v.toString(16).padStart(2, "0");
}
