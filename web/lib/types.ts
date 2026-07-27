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
