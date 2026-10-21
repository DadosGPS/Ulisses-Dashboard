/** Khamis-Roche (1994; errata 1995) — estatura adulta prevista (PAH) de rapazes.
 * Mesma tabela e regras de api/app/services/khamis_roche.py, para calcular em
 * tempo real enquanto se escrevem os valores (o servidor recalcula ao guardar).
 *   PAH (pol.) = β0 + β1·altura (pol.) + β2·peso (lb) + β3·média dos pais (pol.)
 * %PAH = altura atual ÷ PAH × 100 → estado (Cumming et al. 2017). */
const COEF: Record<number, [number, number, number, number]> = {
  4.0: [-10.2567, 1.23812, -0.087235, 0.50286],
  4.5: [-10.7190, 1.15964, -0.074454, 0.52887],
  5.0: [-11.0213, 1.10674, -0.064778, 0.53919],
  5.5: [-11.1556, 1.07480, -0.057760, 0.53691],
  6.0: [-11.1138, 1.05923, -0.052947, 0.52513],
  6.5: [-11.0221, 1.05542, -0.049892, 0.50692],
  7.0: [-10.9984, 1.05877, -0.048144, 0.48538],
  7.5: [-11.0214, 1.06467, -0.047256, 0.46361],
  8.0: [-11.0696, 1.06853, -0.046778, 0.44469],
  8.5: [-11.1220, 1.06572, -0.046261, 0.43171],
  9.0: [-11.1571, 1.05166, -0.045254, 0.42776],
  9.5: [-11.1405, 1.02174, -0.043311, 0.43593],
  10.0: [-11.0380, 0.97135, -0.039981, 0.45932],
  10.5: [-10.8286, 0.89589, -0.034814, 0.50101],
  11.0: [-10.4917, 0.81239, -0.029050, 0.54781],
  11.5: [-10.0065, 0.74134, -0.024167, 0.58409],
  12.0: [-9.3522, 0.68325, -0.020076, 0.60927],
  12.5: [-8.6055, 0.63869, -0.016681, 0.62279],
  13.0: [-7.8632, 0.60818, -0.013895, 0.62407],
  13.5: [-7.1348, 0.59228, -0.011624, 0.61253],
  14.0: [-6.4299, 0.59151, -0.009776, 0.58762],
  14.5: [-5.7578, 0.60643, -0.008261, 0.54875],
  15.0: [-5.1282, 0.63757, -0.006988, 0.49536],
  15.5: [-4.5092, 0.68548, -0.005863, 0.42687],
  16.0: [-3.9292, 0.75069, -0.004795, 0.34271],
  16.5: [-3.4873, 0.83375, -0.003695, 0.24231],
  17.0: [-3.2830, 0.93520, -0.002470, 0.12510],
  17.5: [-3.4156, 1.05558, -0.001027, -0.00950],
};

const CM_POR_POL = 2.54;
const LB_POR_KG = 2.20462;

export type ResultadoKR = {
  pah_cm: number;
  pct_pah: number;
  falta_cm: number;
  categoria: string;
};

export function categoriaCumming(pct: number) {
  if (pct < 85) return "Pré-púbere";
  if (pct < 90) return "Início da puberdade";
  if (pct < 95) return "Meio da puberdade";
  return "Fim da puberdade";
}

export function idadeEm(nascimento: string | null, dia: string): number | null {
  if (!nascimento) return null;
  return (new Date(`${dia}T00:00:00`).getTime() - new Date(`${nascimento}T00:00:00`).getTime()) / (365.25 * 86400000);
}

export function khamisRoche(idade: number | null, altura: number | null, peso: number | null, pai: number | null, mae: number | null): ResultadoKR | null {
  if (idade == null || !altura || !peso || !pai || !mae) return null;
  const a = Math.round(idade * 2) / 2;
  const c = COEF[a];
  if (!c) return null;
  const [b0, b1, b2, b3] = c;
  const pol = b0 + b1 * (altura / CM_POR_POL) + b2 * (peso * LB_POR_KG) + b3 * ((pai + mae) / 2 / CM_POR_POL);
  const pah = pol * CM_POR_POL;
  const pct = (altura / pah) * 100;
  return {
    pah_cm: Math.round(pah * 10) / 10,
    pct_pah: Math.round(pct * 10) / 10,
    falta_cm: Math.round(Math.max(0, pah - altura) * 10) / 10,
    categoria: categoriaCumming(pct),
  };
}
