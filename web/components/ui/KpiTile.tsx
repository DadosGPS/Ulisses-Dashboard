import { alphaHex } from "@/lib/theme";

/** Porta direta de team_kpi_tile() em utils/ui_safe.py. */
export function KpiTile({
  label,
  valor,
  unidade,
  subLabel,
  cor,
}: {
  label: string;
  valor: number | string;
  unidade: string;
  subLabel: string;
  cor: string;
}) {
  return (
    <div
      style={{
        background: `${cor}${alphaHex(0.08)}`,
        border: `1px solid ${cor}${alphaHex(0.22)}`,
        borderRadius: 12,
        padding: "14px 16px",
        height: "100%",
      }}
    >
      <div
        style={{
          fontSize: "0.64rem",
          color: "rgba(255,255,255,0.5)",
          letterSpacing: "1.2px",
          textTransform: "uppercase",
          marginBottom: 6,
        }}
      >
        {label}
      </div>
      <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "white", lineHeight: 1.1 }}>
        {typeof valor === "number" ? valor.toLocaleString("pt-PT") : valor}{" "}
        <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "rgba(255,255,255,0.5)" }}>
          {unidade}
        </span>
      </div>
      <div style={{ fontSize: "0.68rem", color: cor, marginTop: 4, fontWeight: 600 }}>
        {subLabel}
      </div>
    </div>
  );
}
