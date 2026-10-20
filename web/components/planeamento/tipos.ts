export interface Microciclo {
  id: string;
  numero: number;
  nome: string;
  tipo: string;
  perfil: string | null;
  fase: string | null;
  data_inicio: string;
  data_fim: string;
  fatores: Record<string, number>;
  dias: Record<string, { dia_md: string | null; tipo: string; objetivo?: string }>;
  notas: string | null;
  reais?: Record<string, number>;
  n_treinos?: number;
}

export interface ListaMicrociclos {
  disponivel: boolean;
  motivo?: string;
  referencia: Record<string, number>;
  fatores: { chave: string; label: string; unidade: string }[];
  tipos: string[];
  perfis: string[];
  fases: string[];
  microciclos: Microciclo[];
}

export interface Plano {
  pse: number | null;
  duracao_min: number | null;
  distancia_m: number | null;
  hsr_m: number | null;
  sprint_m: number | null;
}

export interface DiaSessao {
  data: string;
  dia_md: string | null;
  tipo: "Treino" | "Jogo" | "Folga";
  objetivo: string;
  planeado: Plano;
  real: (Plano & { n_jogadores: number; tipo: string; dia_md: string | null }) | null;
}

export interface SessoesMicrociclo {
  microciclo: Microciclo;
  referencia: Record<string, number>;
  dias: DiaSessao[];
  tem_duracao: boolean;
  reais: Record<string, number>;
}

export const COR_PERFIL: Record<string, string> = {
  "Introdutório": "#3b82f6",
  Carga: "#f59e0b",
  Choque: "#ef4444",
  Competitivo: "#22c55e",
  "Recuperação": "#14b8a6",
  Taper: "#8b5cf6",
};

export function dataCurta(iso: string) {
  const [a, m, d] = iso.split("-");
  return `${d}/${m}/${a}`;
}

export function fmtFator(v: number | null | undefined) {
  return v == null ? "—" : `×${v.toLocaleString("pt-PT", { minimumFractionDigits: 1, maximumFractionDigits: 2 })}`;
}

export function mediaFatores(f: Record<string, number> | undefined) {
  const v = Object.values(f ?? {});
  return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
}
