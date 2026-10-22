/** Logo LoadMonitorSystem (proposta A · «Microciclo»): cinco colunas de carga
 * a subir até ao dia de jogo, que fica na cor de destaque. As colunas seguem
 * a cor do texto do tema (claras no escuro, escuras no claro). */
export const LARANJA_JOGO = "#F97316";

export function LogoMarca({ tamanho = 32, cor = "var(--text-strong)" }: { tamanho?: number; cor?: string }) {
  return (
    <svg width={tamanho} height={tamanho} viewBox="0 0 64 64" role="img" aria-label="LoadMonitorSystem">
      <rect x="6" y="38" width="8" height="18" rx="2.5" fill={cor} />
      <rect x="17" y="31" width="8" height="25" rx="2.5" fill={cor} />
      <rect x="28" y="24" width="8" height="32" rx="2.5" fill={cor} />
      <rect x="39" y="17" width="8" height="39" rx="2.5" fill={cor} />
      <rect x="50" y="8" width="8" height="48" rx="2.5" fill={LARANJA_JOGO} />
    </svg>
  );
}

/** Marca + nome, na horizontal. */
export function LogoCompleto({ tamanho = 34, mostrarSistema = true }: { tamanho?: number; mostrarSistema?: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: Math.round(tamanho * 0.36) }}>
      <LogoMarca tamanho={tamanho} />
      <div style={{ display: "flex", flexDirection: "column", gap: 2, whiteSpace: "nowrap" }}>
        <div className="font-display" style={{ fontSize: tamanho * 0.62, fontWeight: 700, color: "var(--text-strong)", letterSpacing: "-0.02em", lineHeight: 1 }}>
          LoadMonitor
        </div>
        {mostrarSistema && (
          <div className="font-display" style={{ fontSize: Math.max(9, tamanho * 0.24), fontWeight: 500, color: "var(--text-faint)", letterSpacing: "0.42em", lineHeight: 1.2 }}>
            SYSTEM
          </div>
        )}
      </div>
    </div>
  );
}
