import { cores, espaco, raio } from "@/lib/theme";

export interface KpiCarga {
  chave: string;
  label: string;
  unidade: string;
  cor: string;
  atual: number | null;
  baseline: number | null;
  delta_pct: number | null;
  estado: string;
  n_baseline: number;
}

const ESTADO_UI: Record<string, { label: string; cor: string }> = {
  alto: { label: "Alto", cor: cores.cargaInterna },
  baixo: { label: "Baixo", cor: cores.info },
  normal: { label: "Normal", cor: cores.sucesso },
  insuficiente: { label: "Sem base", cor: cores.textoSuave },
};

/** Cartão de KPI de carga (atual vs baseline, delta %, estado). Partilhado
 * entre o Dashboard e a secção Carga Externa. Componente de apresentação —
 * seguro em server e client components. */
export function KpiCargaCard({ kpi, compacto = false }: { kpi: KpiCarga; compacto?: boolean }) {
  const est = ESTADO_UI[kpi.estado] ?? ESTADO_UI.insuficiente;
  const subiu = (kpi.delta_pct ?? 0) >= 0;
  return (
    <div
      style={{
        background: cores.bgCartao,
        border: `1px solid ${cores.borda}`,
        borderLeft: `3px solid ${kpi.cor}`,
        borderRadius: raio.md,
        padding: compacto ? espaco.md : espaco.lg,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: espaco.sm }}>
        <span style={{ fontSize: "0.7rem", letterSpacing: "0.04em", textTransform: "uppercase", color: cores.textoSuave }}>
          {kpi.label}
        </span>
        <span
          style={{
            fontSize: "0.6rem",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.04em",
            color: est.cor,
            background: `color-mix(in srgb, ${est.cor} 16%, transparent)`,
            padding: "2px 7px",
            borderRadius: 999,
          }}
        >
          {est.label}
        </span>
      </div>
      <div
        className="font-display"
        style={{ fontSize: compacto ? "1.4rem" : "1.7rem", fontWeight: 800, color: "white", lineHeight: 1, fontVariantNumeric: "tabular-nums" }}
      >
        {kpi.atual !== null ? kpi.atual.toLocaleString("pt-PT") : "—"}
        <span style={{ fontSize: "0.75rem", fontWeight: 600, color: cores.textoSuave, marginLeft: 4 }}>{kpi.unidade}</span>
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: espaco.sm, marginTop: espaco.sm }}>
        {kpi.delta_pct !== null ? (
          <span style={{ fontSize: "0.8rem", fontWeight: 700, color: kpi.estado === "normal" ? cores.textoSuave : est.cor }}>
            {subiu ? "▲" : "▼"} {Math.abs(kpi.delta_pct).toFixed(1)}%
          </span>
        ) : (
          <span style={{ fontSize: "0.72rem", color: cores.textoFraco }}>sem histórico</span>
        )}
        <span style={{ fontSize: "0.7rem", color: cores.textoSuave }}>
          base {kpi.baseline !== null ? kpi.baseline.toLocaleString("pt-PT") : "—"}
        </span>
      </div>
    </div>
  );
}
