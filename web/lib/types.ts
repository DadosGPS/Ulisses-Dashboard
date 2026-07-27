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

export interface DashboardResponse {
  tem_dados: boolean;
  microciclo_recente: number | null;
  kpis: {
    carga_interna_media: number | null;
    acwr_medio: number | null;
    hooper_medio: number | null;
    em_risco: number;
  };
  alertas: AlertaDashboard[];
  rankings: RankingMetrica[];
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

export interface EquipaResponse {
  tem_dados: boolean;
  acwr: AcwrJogador[];
  ci_evolucao: PontoEvolucaoCI[];
  load_profile: {
    colunas: { chave: string; label: string; cor: string; casas: number }[];
    linhas: { jogador: string; valores: Record<string, number | null> }[];
  };
}
