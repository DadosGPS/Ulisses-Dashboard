/**
 * Sistema de design — porta e evolução de utils/ui_safe.py, com a densidade e
 * o rigor de grelha de uma ferramenta de BI (Power BI/STATSports como
 * referência), mantendo o tema escuro já validado com o utilizador.
 */

export const cores = {
  bg: "#0a0e14",
  bgElevado: "#0d1117",
  bgCartao: "#12171f",
  texto: "rgba(255,255,255,0.92)",
  textoSuave: "rgba(255,255,255,0.55)",
  textoFraco: "rgba(255,255,255,0.38)",
  borda: "rgba(255,255,255,0.08)",
  bordaForte: "rgba(255,255,255,0.14)",

  // Paleta de métricas (mesma usada em dashboard.py METRICAS / ui_safe.py —
  // mantida por continuidade visual com o que já foi validado)
  cargaInterna: "#e63946",
  distanciaTotal: "#2563eb",
  hsr: "#f59e0b",
  sprint: "#dc2626",
  velMax: "#8b5cf6",
  acc: "#14b8a6",
  dcc: "#10b981",

  sucesso: "#22c55e",
  atencao: "#f59e0b",
  perigo: "#ef4444",
  info: "#3498db",

  destaque: "#7c3aed", // acento estrutural (sidebar, estados ativos) — distinto das cores de métrica
} as const;

/** Escala de espaçamento consistente — evita valores arbitrários espalhados pelo código. */
export const espaco = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

export const raio = {
  sm: 8,
  md: 12,
  lg: 16,
} as const;

/** Sombras subtis — dão profundidade aos cartões sem parecer "flutuante" a mais. */
export const sombra = {
  cartao: "0 1px 2px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.04) inset",
  elevado: "0 8px 24px rgba(0,0,0,0.45), 0 0 0 1px rgba(255,255,255,0.05) inset",
} as const;

/** Layout partilhado por todos os gráficos Plotly.js, equivalente ao template
 * "lm_professional" registado em aplicar_tema_graficos() (utils/ui_safe.py). */
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

/** Estilo base para um "visual" tipo BI — cartão com borda, sombra e cantos consistentes. */
export const estiloCartao: React.CSSProperties = {
  background: cores.bgCartao,
  border: `1px solid ${cores.borda}`,
  borderRadius: raio.md,
  boxShadow: sombra.cartao,
};
