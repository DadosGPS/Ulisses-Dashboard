/** Cálculos da calculadora de HIIT (puros, sem React). */

/** Limiar fixo a que o GPS conta os metros de HSR. */
export const LIMIAR_GPS_HSR_KMH = 19.8;
/** Recorde de velocidade com mais do que isto pode já não ser o atual. */
export const MSS_VELHA_DIAS = 42;
/** Teste de 1 km com mais do que isto: reteste recomendado (nesta idade a MAS muda depressa). */
export const MAS_VELHA_DIAS = 60;

/** Constante de tempo da aceleração (modelo mono-exponencial v(t) = MSS·(1 − e^(−t/τ))). */
const TAU_S = 1.1;

export function diasDesde(iso: string | null | undefined, hoje = new Date()): number | null {
  if (!iso) return null;
  const d = new Date(`${iso.slice(0, 10)}T00:00:00`);
  if (Number.isNaN(d.getTime())) return null;
  return Math.floor((hoje.getTime() - d.getTime()) / 86_400_000);
}

/** Distância (m) para chegar a `pct`% da MSS. Em treino o arranque é submáximo,
 * por isso duplica-se a distância de uma aceleração máxima, arredonda-se a
 * 5 m e nunca fica abaixo de 10 m. É uma estimativa para pôr o cone. */
export function distanciaArranque(mssKmh: number, pct: number): number {
  const r = Math.min(pct, 95) / 100;
  const t = -TAU_S * Math.log(1 - r);
  const d = (mssKmh / 3.6) * (t - TAU_S * r);
  return Math.max(10, Math.round((d * 2) / 5) * 5);
}

export type LinhaHsr = {
  velKmh: number;
  distM: number;
  arranqueM: number;
  coneFinalM: number;
  reps: number;
  abaixoGps: boolean;
};

/** Modo HSR: correr `tempoS` segundos a `pct`% da MSS, até somar `volumeM` metros. */
export function calcularHsr(mssKmh: number, pct: number, tempoS: number, volumeM: number): LinhaHsr {
  const velKmh = (mssKmh * pct) / 100;
  const distM = Math.round((velKmh / 3.6) * tempoS);
  const arranqueM = distanciaArranque(mssKmh, pct);
  return {
    velKmh,
    distM,
    arranqueM,
    coneFinalM: arranqueM + distM,
    reps: distM > 0 ? Math.ceil(volumeM / distM) : 0,
    abaixoGps: velKmh < LIMIAR_GPS_HSR_KMH,
  };
}

export type FormatoMas = { id: string; label: string; trabalhoS: number; pausaS: number; vaivem20: boolean };
export const FORMATOS_MAS: FormatoMas[] = [
  { id: "15-15", label: '15"/15" em linha', trabalhoS: 15, pausaS: 15, vaivem20: false },
  { id: "30-30", label: '30"/30" em linha', trabalhoS: 30, pausaS: 30, vaivem20: false },
  { id: "15-15v", label: '15"/15" vaivém 20 m', trabalhoS: 15, pausaS: 15, vaivem20: true },
];
/** Tempo perdido em cada mudança de direção de 180° (estimativa). */
const PERDA_COD_S = 0.7;

export type LinhaMas = { velKmh: number; distM: number; cones: string; pctMss: number | null; repsPorSerie: number; totalM: number };

/** Modo % MAS: distância por repetição de cada jogador. No vaivém de 20 m
 * desconta-se o tempo das mudanças de direção (itera até estabilizar). */
export function calcularMas(
  masKmh: number, mssKmh: number | null, pct: number, f: FormatoMas, series: number, minutosSerie: number,
): LinhaMas {
  const velKmh = (masKmh * pct) / 100;
  const ms = velKmh / 3.6;
  let d = ms * f.trabalhoS;
  let cones = "";
  if (f.vaivem20) {
    for (let i = 0; i < 6; i++) d = ms * (f.trabalhoS - PERDA_COD_S * Math.floor(d / 20));
    const n = Math.floor(d / 20);
    cones = `${n} × 20 m + ${Math.round(d - n * 20)} m`;
  } else {
    cones = `${Math.round(d)} m`;
  }
  const distM = Math.round(d);
  const repsPorSerie = Math.floor((minutosSerie * 60) / (f.trabalhoS + f.pausaS));
  return {
    velKmh,
    distM,
    cones,
    pctMss: mssKmh ? Math.round((velKmh / mssKmh) * 100) : null,
    repsPorSerie,
    totalM: distM * repsPorSerie * series,
  };
}

/** Junta jogadores com o cone final a menos de `passo` m uns dos outros,
 * para montar poucos corredores no campo. */
export function agruparCorredores<T>(itens: T[], distancia: (x: T) => number, passo = 5): { distM: number; itens: T[] }[] {
  const mapa = new Map<number, T[]>();
  for (const x of itens) {
    const k = Math.round(distancia(x) / passo) * passo;
    mapa.set(k, [...(mapa.get(k) ?? []), x]);
  }
  return [...mapa.entries()].sort((a, b) => b[0] - a[0]).map(([distM, itens]) => ({ distM, itens }));
}
