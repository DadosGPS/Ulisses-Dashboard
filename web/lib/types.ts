export interface RankingItem {
  jogador: string;
  valor: number;
}

export interface AlertaPrioritario {
  jogador: string;
  tipo: "ACWR" | "Wellness" | "Dados" | "Velocidade" | "PSE vs GPS";
  valor: number | null;
  estado: string;
}

export interface JogadorIndisponivel {
  jogador: string;
  estado: string;
  motivo: string | null;
  desde: string | null;
}

/** Espelha o JSON devolvido por GET /api/teams/{team_id}/analise (api/app/services/analise_service.py). */
export interface ResumoSemana {
  microciclo: number | null;
  carga_interna_media: number | null;
  carga_por_dia: { dia_md: string; carga_media: number }[];
  pse_por_dia: { dia_md: string; pse_media: number }[];
  monotonia_media: number | null;
  strain_medio: number | null;
}

export interface AnaliseResponse {
  tem_dados: boolean;
  jogador_selecionado: string | null;
  jogadores_disponiveis: string[];
  microciclo_recente: number | null;
  microciclo_selecionado: number | null;
  microciclo_comparar: number | null;
  microciclos_disponiveis: number[];
  comparacao: { a: ResumoSemana; b: ResumoSemana } | null;
  dia_md_selecionado: string | null;
  dias_md_disponiveis: string[];
  carga_interna_media: number | null;
  carga_maxima: RankingItem | null;
  carga_minima: RankingItem | null;
  carga_por_dia: { dia_md: string; carga_media: number }[];
  pse_por_dia: { dia_md: string; pse_media: number }[];
  monotonia_media: number | null;
  strain_medio: number | null;
  ranking_carga: RankingItem[];
  alertas: {
    prioritarios: AlertaPrioritario[];
    indisponiveis: JogadorIndisponivel[];
  };
}

export interface EstadoJogador {
  player_id: string;
  nome: string;
  posicao: string | null;
  estado: "apto" | "lesionado" | "em_recuperacao" | "ausente";
  estado_motivo: string | null;
  estado_desde: string | null;
  ativo: boolean;
}

/** Espelha GET /api/teams/{team_id}/equipa (api/app/services/equipa_service.py). */
export interface AcwrJogador {
  jogador: string;
  posicao: string;
  acwr: number | null;
  estado: string;
}

export interface PontoEvolucaoCI {
  microciclo: number;
  carga_interna_media: number;
}

/** Espelha GET /api/teams/{team_id}/jogador (api/app/services/jogador_service.py). */
export interface SessaoJogador {
  data: string | null;
  tipo: string | null;
  dia_md: string | null;
  microciclo_nr: number | null;
  carga_interna: number | null;
  distancia_total_m: number | null;
  hsr_m: number | null;
  sprint_m: number | null;
  vel_max_kmh: number | null;
  hooper_index: number | null;
}

export interface JogadorResponse {
  jogadores_disponiveis: string[];
  jogador: string | null;
  posicao?: string;
  kpis?: {
    sessoes_total: number;
    carga_interna_media: number | null;
    acwr_atual: number | null;
    hooper_medio: number | null;
    vel_max_recorde: number | null;
    vel_max_recente: number | null;
    vel_max_pct_recorde: number | null;
  };
  evolucao_carga?: { data: string; carga_interna: number }[];
  evolucao_acwr?: { data: string; acwr: number }[];
  metricas_externas?: { chave: string; label: string; unidade: string; cor: string; casas: number }[];
  evolucao_externa?: Record<string, { data: string; valor: number }[]>;
  evolucao_vmax?: { data: string; tipo: string | null; dia_md: string | null; kmh: number; pct: number }[];
  vel_max_recorde?: number | null;
  sessoes_recentes?: SessaoJogador[];
}

/** Espelha GET /api/teams/{team_id}/planeamento (api/app/services/planeamento_service.py). */
export interface PlaneamentoResponse {
  tem_dados: boolean;
  tem_jogos: boolean;
  referencia: Record<string, number>;
  dias: { dia_md: string; valores: Record<string, number> }[];
  evolucao_semanal: { microciclo: number; valores: Record<string, number> }[];
  metricas: string[];
  individual: boolean;
  jogadores_disponiveis: string[];
  jogador_selecionado: string | null;
}

/** Espelha GET /api/teams/{team_id}/planeamento/pse-semana (api/app/services/pse_planeado_service.py). */
export interface PseSemanaResponse {
  tem_dados: boolean;
  microciclo: number | null;
  microciclos_disponiveis: number[];
  dias: { dia_md: string; pse_esperada: number | null; pse_real: number | null }[];
  monotonia_jogadores: { jogador: string; monotonia: number }[];
}

/** Espelha GET /api/teams/{team_id}/avancado (api/app/services/avancado_service.py). */
export interface AvancadoResponse {
  tem_dados: boolean;
  microciclo: number | null;
  metricas: {
    metrica: string;
    jogadores: { jogador: string; valor: number; zscore: number; grupo_comparacao: string; posicao: string }[];
  }[];
}

/** Espelha GET /api/teams/{team_id}/sistema (api/app/services/sistema_service.py). */
export interface SistemaResponse {
  validacao: {
    tem_dados: boolean;
    total_sessoes?: number;
    total_jogadores?: number;
    data_inicio?: string | null;
    data_fim?: string | null;
    microciclos?: number;
    colunas?: { coluna: string; preenchidas: number; total: number; pct: number }[];
  };
  uploads: { filename: string; status: string; row_count: number | null; error: string | null; criado_em: string | null }[];
}

export interface EquipaResponse {
  tem_dados: boolean;
  acwr: AcwrJogador[];
  ci_evolucao: PontoEvolucaoCI[];
  monotonia_evolucao: { microciclo: number; monotonia_media: number }[];
  carga_externa_evolucao: Record<string, { microciclo: number; valor: number }[]>;
  microciclos_disponiveis: number[];
  load_profile: {
    colunas: { chave: string; label: string; cor: string; casas: number }[];
    linhas: { jogador: string; valores: Record<string, number | null> }[];
  };
}
