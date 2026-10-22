"use client";

import { cores, espaco, raio, sombra } from "@/lib/theme";
import { useTr } from "@/lib/i18n/cliente";

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
  const tr = useTr();
  const est = ESTADO_UI[kpi.estado] ?? ESTADO_UI.insuficiente;
  const subiu = (kpi.delta_pct ?? 0) >= 0;
  return (
    <div
      style={{
        background: cores.bgCartao,
        border: `1px solid ${cores.borda}`,
        borderRadius: raio.md,
        boxShadow: sombra.cartao,
        padding: compacto ? espaco.md : espaco.lg,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: espaco.sm }}>
        <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.76rem", color: cores.textoSuave }}>
          <span style={{ width: 7, height: 7, borderRadius: 2, background: kpi.cor }} />
          {tr(kpi.label)}
        </span>
        {kpi.estado !== "normal" && (
          <span
            style={{
              fontSize: "0.68rem",
              fontWeight: 600,
              color: est.cor,
              background: `color-mix(in srgb, ${est.cor} 16%, transparent)`,
              padding: "2px 7px",
              borderRadius: 999,
            }}
          >
            {tr(est.label)}
          </span>
        )}
      </div>
      <div
        className="font-display"
        style={{ fontSize: compacto ? "1.35rem" : "1.6rem", fontWeight: 600, color: cores.textoForte, lineHeight: 1, fontVariantNumeric: "tabular-nums" }}
      >
        {kpi.atual !== null ? kpi.atual.toLocaleString(tr.loc) : "—"}
        <span style={{ fontSize: "0.75rem", fontWeight: 600, color: cores.textoSuave, marginLeft: 4 }}>{kpi.unidade}</span>
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: espaco.sm, marginTop: espaco.sm }}>
        {kpi.delta_pct !== null ? (
          <span style={{ fontSize: "0.8rem", fontWeight: 700, color: kpi.estado === "normal" ? cores.textoSuave : est.cor }}>
            {subiu ? "▲" : "▼"} {Math.abs(kpi.delta_pct).toFixed(1)}%
          </span>
        ) : (
          <span style={{ fontSize: "0.72rem", color: cores.textoFraco }}>{tr("sem histórico")}</span>
        )}
        <span style={{ fontSize: "0.7rem", color: cores.textoSuave }}>
          {tr("base")}{" "}{kpi.baseline !== null ? kpi.baseline.toLocaleString(tr.loc) : "—"}
        </span>
      </div>
    </div>
  );
}
