/** Espelha o JSON devolvido por GET /api/teams/{team_id}/dashboard (api/app/services/dashboard_service.py). */

export interface AlertaDashboard {
  jogador: string;
  posicao: string;
  tipo: "ACWR" | "Wellness";
  valor: number;
  estado: string;
}

export interface RankingItem {
  jogador: string;
  valor: number;
}

export interface RankingMetrica {
  metrica: string;
  cor: string;
  unidade: string;
  top3: RankingItem[];
  bottom3: RankingItem[];
}

export interface ComparacaoMetrica {
  metrica: string;
  valor: number;
  media_historica: number | null;
  variacao_pct: number | null;
}

export interface Resumo5W1H {
  data: string;
  dia_md: string | null;
  who: { n_jogadores: number; jogadores: string[] };
  where: string;
  why: string;
  how: string;
  what: ComparacaoMetrica[];
}

export interface DashboardResponse {
  tem_dados: boolean;
  microciclo_recente: number | null;
  microciclo_selecionado: number | null;
  microciclos_disponiveis: number[];
  kpis: {
    carga_interna_media: number | null;
    acwr_medio: number | null;
    hooper_medio: number | null;
    em_risco: number;
  };
  alertas: AlertaDashboard[];
  rankings: RankingMetrica[];
  resumo_5w1h: Resumo5W1H | null;
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
  };
  evolucao_carga?: { data: string; carga_interna: number }[];
  evolucao_acwr?: { data: string; acwr: number }[];
  sessoes_recentes?: SessaoJogador[];
}

/** Espelha GET /api/teams/{team_id}/planeamento (api/app/services/planeamento_service.py). */
export interface PlaneamentoResponse {
  tem_dados: boolean;
  tem_jogos: boolean;
  referencia: Record<string, number>;
  dias: { dia_md: string; valores: Record<string, number> }[];
  metricas: string[];
}

/** Espelha GET /api/teams/{team_id}/avancado (api/app/services/avancado_service.py). */
export interface AvancadoResponse {
  tem_dados: boolean;
  microciclo: number | null;
  metricas: {
    metrica: string;
    jogadores: { jogador: string; valor: number; zscore: number }[];
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
  load_profile: {
    colunas: { chave: string; label: string; cor: string; casas: number }[];
    linhas: { jogador: string; valores: Record<string, number | null> }[];
  };
}
