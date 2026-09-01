/**
 * Alert System Utilities
 * 
 * Categorizes players into status levels based on multiple metrics
 * Priority: Information hierarchy from spec
 * 1. What is happening? (status)
 * 2. Why? (reason)
 * 3. What data supports it? (metrics)
 * 4. Advanced analysis (if needed)
 */

export type AlertStatus = 'normal' | 'attention' | 'high-attention';
export type AlertReason = 
  | 'high-load-change'
  | 'poor-wellness'
  | 'high-hsr-exposure'
  | 'velocity-drop'
  | 'divergence'
  | 'absence'
  | 'data-missing';

export interface Alert {
  playerId: string;
  playerName: string;
  status: AlertStatus;
  primaryReason: AlertReason;
  reasons: AlertReason[];
  metrics: {
    acwr?: number;
    weeklyLoadChange?: number; // percentage
    wellnessScore?: number;
    wellnessChange?: number; // percentage
    hsrExposure?: number;
    velocityChange?: number; // percentage
    lastDataDate?: Date;
  };
  actionableText: string; // Human-readable explanation
  recommendation?: string;
}

interface ThresholdConfig {
  acwrAttention: number; // e.g., 1.3
  acwrHigh: number; // e.g., 1.5
  loadChangeAttention: number; // e.g., 30% 
  loadChangeHigh: number; // e.g., 50%
  wellnessAttention: number; // e.g., 10% drop
  wellnessHigh: number; // e.g., 20% drop
  velocityDropAttention: number; // e.g., 8%
  velocityDropHigh: number; // e.g., 12%
  hsrBaselineAttention: number; // e.g., 25% above baseline
  hsrBaselineHigh: number; // e.g., 40% above baseline
}

const DEFAULT_THRESHOLDS: ThresholdConfig = {
  acwrAttention: 1.3,
  acwrHigh: 1.5,
  loadChangeAttention: 30,
  loadChangeHigh: 50,
  wellnessAttention: 10,
  wellnessHigh: 20,
  velocityDropAttention: 8,
  velocityDropHigh: 12,
  hsrBaselineAttention: 25,
  hsrBaselineHigh: 40,
};

interface PlayerMetrics {
  playerId: string;
  playerName: string;
  acwr?: number;
  weeklyLoadChange?: number; // week-over-week percentage
  wellnessScore?: number;
  wellnessBaseline?: number;
  hsrExposure?: number;
  hsrBaseline?: number;
  velocityTrend?: number; // percentage change from 3-session mean
  isAbsent?: boolean;
  lastDataDate?: Date;
  dataFreshnessHours?: number;
}

/**
 * Evaluate player metrics and return alert status
 */
export function evaluatePlayerAlert(
  metrics: PlayerMetrics,
  thresholds: Partial<ThresholdConfig> = {}
): Alert {
  const config = { ...DEFAULT_THRESHOLDS, ...thresholds };
  const reasons: AlertReason[] = [];
  let severityCount = { high: 0, moderate: 0, mild: 0 };

  // 1. Check ACWR
  let acwrSeverity: 'high' | 'moderate' | 'mild' | null = null;
  if (metrics.acwr) {
    if (metrics.acwr >= config.acwrHigh) {
      reasons.push('high-load-change');
      acwrSeverity = 'high';
      severityCount.high++;
    } else if (metrics.acwr >= config.acwrAttention) {
      reasons.push('high-load-change');
      acwrSeverity = 'moderate';
      severityCount.moderate++;
    }
  }

  // 2. Check Load change
  if (
    metrics.weeklyLoadChange &&
    Math.abs(metrics.weeklyLoadChange) > config.loadChangeAttention
  ) {
    if (Math.abs(metrics.weeklyLoadChange) > config.loadChangeHigh) {
      severityCount.high++;
    } else {
      severityCount.moderate++;
    }
  }

  // 3. Check Wellness
  let wellnessChange = 0;
  if (metrics.wellnessScore && metrics.wellnessBaseline) {
    wellnessChange = ((metrics.wellnessBaseline - metrics.wellnessScore) / metrics.wellnessBaseline) * 100;
    if (wellnessChange > config.wellnessHigh) {
      reasons.push('poor-wellness');
      severityCount.high++;
    } else if (wellnessChange > config.wellnessAttention) {
      reasons.push('poor-wellness');
      severityCount.moderate++;
    }
  }

  // 4. Check HSR exposure
  if (metrics.hsrExposure && metrics.hsrBaseline) {
    const hsrChange = ((metrics.hsrExposure - metrics.hsrBaseline) / metrics.hsrBaseline) * 100;
    if (hsrChange > config.hsrBaselineHigh) {
      reasons.push('high-hsr-exposure');
      severityCount.high++;
    } else if (hsrChange > config.hsrBaselineAttention) {
      reasons.push('high-hsr-exposure');
      severityCount.moderate++;
    }
  }

  // 5. Check Velocity trend
  if (metrics.velocityTrend && metrics.velocityTrend < 0) {
    const velocityDrop = Math.abs(metrics.velocityTrend);
    if (velocityDrop > config.velocityDropHigh) {
      reasons.push('velocity-drop');
      severityCount.high++;
    } else if (velocityDrop > config.velocityDropAttention) {
      reasons.push('velocity-drop');
      severityCount.moderate++;
    }
  }

  // 6. Check absence
  if (metrics.isAbsent) {
    reasons.push('absence');
    severityCount.mild++;
  }

  // 7. Check data freshness
  if (
    metrics.dataFreshnessHours &&
    metrics.dataFreshnessHours > 48
  ) {
    reasons.push('data-missing');
    severityCount.mild++;
  }

  // Determine status
  let status: AlertStatus = 'normal';
  let primaryReason: AlertReason = 'data-missing';

  if (
    severityCount.high >= 2 ||
    (severityCount.high === 1 && severityCount.moderate >= 1)
  ) {
    status = 'high-attention';
    primaryReason = reasons[0] || 'high-load-change';
  } else if (severityCount.high >= 1 || severityCount.moderate >= 2) {
    status = 'attention';
    primaryReason = reasons[0] || 'high-load-change';
  } else if (severityCount.moderate >= 1 || severityCount.mild >= 2) {
    status = 'attention';
    primaryReason = reasons[0] || 'data-missing';
  }

  // Generate actionable text
  const actionableText = generateActionableText(
    metrics.playerName,
    status,
    primaryReason,
    metrics
  );

  return {
    playerId: metrics.playerId,
    playerName: metrics.playerName,
    status,
    primaryReason,
    reasons: [...new Set(reasons)],
    metrics: {
      acwr: metrics.acwr,
      weeklyLoadChange: metrics.weeklyLoadChange,
      wellnessScore: metrics.wellnessScore,
      wellnessChange,
      hsrExposure: metrics.hsrExposure,
      velocityChange: metrics.velocityTrend,
      lastDataDate: metrics.lastDataDate,
    },
    actionableText,
    recommendation: generateRecommendation(primaryReason, metrics),
  };
}

/**
 * Generate human-readable description of alert
 */
function generateActionableText(
  playerName: string,
  status: AlertStatus,
  reason: AlertReason,
  metrics: PlayerMetrics
): string {
  const statusLabel = {
    'normal': '🟢 Normal',
    'attention': '🟡 Atenção',
    'high-attention': '🔴 Atenção Alta',
  }[status];

  const reasonText = {
    'high-load-change': `Carga semanal elevada (ACWR: ${metrics.acwr?.toFixed(2)}${
      metrics.weeklyLoadChange ? ` | +${metrics.weeklyLoadChange.toFixed(0)}% vs semana passada` : ''
    })`,
    'poor-wellness': `Bem-estar reduzido (${metrics.wellnessScore}/20${
      metrics.wellnessBaseline ? ` | -${((metrics.wellnessBaseline - metrics.wellnessScore!) / metrics.wellnessBaseline) * 100}% vs baseline` : ''
    })`,
    'high-hsr-exposure': `Exposição HSR elevada (+${metrics.hsrExposure ? ((metrics.hsrExposure - (metrics.hsrBaseline || 0)) / (metrics.hsrBaseline || 1)) * 100 : 0}% vs baseline)`,
    'velocity-drop': `Queda de velocidade (${metrics.velocityTrend?.toFixed(1)}%)`,
    'divergence': 'Divergência PSE ↔ GPS observada',
    'absence': 'Jogador ausente ou lesionado',
    'data-missing': 'Sem dados recentes',
  };

  return `${statusLabel} - ${reasonText[reason]}`;
}

/**
 * Generate actionable recommendation
 */
function generateRecommendation(
  reason: AlertReason,
  metrics: PlayerMetrics
): string | undefined {
  const recommendations = {
    'high-load-change': `Monitorizar recuperação e exposição de alta intensidade próxima. Considerar redução de carga nos próximos treinos.`,
    'poor-wellness': `Wellness reduzido. Priorizar sono e recuperação. Considerar treino adaptado.`,
    'high-hsr-exposure': `Exposição HSR elevada. Monitorizar carga cumulativa. Planejar recuperação.`,
    'velocity-drop': `Queda de velocidade detectada. Pode indicar fadiga. Monitorizar nos próximos dias.`,
    'divergence': `PSE e GPS divergem. Verificar questão de perceção de esforço vs carga real.`,
    'absence': `Jogador indisponível. Planejar integração no retorno.`,
    'data-missing': `Sem dados recentes. Solicitar importação de dados.`,
  };

  return recommendations[reason];
}

/**
 * Get squad status summary
 */
export function getSquadStatusSummary(alerts: Alert[]): {
  normal: number;
  attention: number;
  highAttention: number;
} {
  return {
    normal: alerts.filter((a) => a.status === 'normal').length,
    attention: alerts.filter((a) => a.status === 'attention').length,
    highAttention: alerts.filter((a) => a.status === 'high-attention').length,
  };
}

/**
 * Get players sorted by alert priority
 */
export function sortPlayersByAlert(alerts: Alert[]): Alert[] {
  const priorityMap = { 'high-attention': 0, 'attention': 1, 'normal': 2 };
  return [...alerts].sort(
    (a, b) =>
      priorityMap[a.status as AlertStatus] - priorityMap[b.status as AlertStatus]
  );
}
