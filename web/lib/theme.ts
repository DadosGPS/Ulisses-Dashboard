/**
 * Sistema de design — tokens partilhados por toda a app, com tema escuro e
 * claro (variáveis CSS em app/globals.css, alternadas pelo atributo
 * data-theme do <html>). Estilo sóbrio: neutros, um só acento, cor reservada
 * para métricas e estados.
 */

export const cores = {
  // Neutros — apontam para as variáveis CSS de app/globals.css, por isso
  // mudam sozinhos entre o tema escuro e o claro.
  bg: "var(--bg)",
  bgElevado: "var(--bg-elevado)",
  bgCartao: "var(--bg-cartao)",
  superficie: "var(--surface)",          // fundo subtil (inputs, linhas alternadas, chips)
  superficieHover: "var(--surface-hover)",
  textoForte: "var(--text-strong)",     // títulos e valores em destaque
  texto: "var(--text)",
  textoSuave: "var(--text-dim)",
  textoFraco: "var(--text-faint)",
  borda: "var(--border)",
  bordaForte: "var(--border-strong)",
  acento: "var(--accent)",              // um só acento estrutural (estados ativos, botões principais)
  acentoSuave: "var(--accent-soft)",
  sobreAcento: "var(--on-accent)",

  // Paleta de métricas (mesma usada em dashboard.py METRICAS / ui_safe.py —
  // mantida por continuidade visual com o que já foi validado)
  cargaInterna: "#db2777", // rosa — distinta do vermelho do sprint
  distanciaTotal: "#2563eb",
  hsr: "#d97706",
  sprint: "#dc2626",
  velMax: "#7c3aed",
  acc: "#0d9488",
  dcc: "#059669",

  sucesso: "#16a34a", // verde-600 e âmbar-600: legíveis no tema claro e no escuro
  atencao: "#d97706",
  perigo: "#ef4444",
  info: "#3b82f6",

  destaque: "var(--accent)",
} as const;

/** Cor de cada métrica — a mesma em todos os gráficos, cartões e tabelas. */
export const COR_METRICA: Record<string, string> = {
  distancia_total_m: cores.distanciaTotal,
  hsr_m: cores.hsr,
  sprint_m: cores.sprint,
  acc_n: cores.acc,
  dcc_n: cores.dcc,
  vel_max_kmh: cores.velMax,
  carga_interna: cores.cargaInterna,
};

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
  cartao: "var(--shadow-card)",
  elevado: "0 8px 24px rgb(0 0 0 / 0.25)",
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
    linecolor: "rgb(var(--ink) / 0.16)",
    tickfont: { size: 10, color: cores.textoSuave },
  },
  yaxis: {
    showgrid: false,
    zeroline: false,
    linecolor: "rgb(var(--ink) / 0.16)",
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
