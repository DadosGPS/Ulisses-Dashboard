export interface Metrica {
  chave: string;
  label: string;
  unidade: string;
  grupo: string;
  maior_melhor: boolean | null;
  casas: number;
}

export interface AtletaLista {
  atleta_id: string;
  nome: string;
  data_nascimento: string | null;
  idade: number | null;
  posicao: string | null;
  epocas: number;
  escalao_atual: string | null;
  epoca_atual: string | null;
  n_avaliacoes: number;
  ultima_avaliacao: string | null;
  equipas: { team_id: string; escalao: string | null; epoca: string | null; rotulo: string }[];
  consentimento?: boolean | null;
}

export interface PontoSerie {
  id: string;
  data: string;
  valor: number;
  idade: number | null;
  origem: "ficha" | "importado";
}

export interface Comparacao {
  metrica: string;
  label: string;
  unidade: string;
  grupo: string;
  maior_melhor: boolean | null;
  casas: number;
  entrada: { data: string; valor: number; idade: number | null; percentil: number | null };
  ultima: { data: string; valor: number; idade: number | null; percentil: number | null };
  n_avaliacoes: number;
  variacao: number;
  variacao_pct: number | null;
  melhorou: boolean | null;
}

export interface FichaAtleta {
  atleta: { atleta_id: string; nome: string; data_nascimento: string | null; idade: number | null; posicao: string | null; pe_dominante: string | null; altura_pai_cm: number | null; altura_mae_cm: number | null; altura_pais_medida: boolean | null;
    consentimento?: { data: string | null; por: "atleta" | "encarregado" | null; notas: string | null } | null };
  percurso: { player_id: string; team_id: string; equipa: string; escalao: string | null; epoca: string | null; posicao: string | null; ativo: boolean; sessoes: number; lesoes: number }[];
  catalogo: Metrica[];
  equipas: { team_id: string; rotulo: string }[];
  series: Record<string, PontoSerie[]>;
  bandas: Record<string, { idade: number; n: number; p25: number; p50: number; p75: number }[]>;
  maturacao: { data: string; idade: number; altura_cm: number; estatura_prevista_cm: number; pct_estatura_adulta: number; crescimento_restante_cm: number; categoria: string; idade_tabela: number }[];
  maturacao_disponivel: boolean;
  crescimento?: { data: string; altura_cm: number; desde: string; cm_ano: number; pico: boolean }[];
  crescimento_pico_cm_ano?: number;
  entrada_vs_ultima: Comparacao[];
  carga_jogo: { epoca: string; escalao: string | null; jogos: number; minutos: number | null; jogos_completos: number; distancia_90: number | null; hsr_90: number | null; sprint_90: number | null; vmax: number | null }[];
  sem_data_nascimento: boolean;
}
