import { alphaHex, cores, espaco, raio, sombra } from "@/lib/theme";

/** Porta e refinamento de team_kpi_tile() em utils/ui_safe.py — visual estilo BI (cartão com sombra/profundidade). */
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
        background: cores.bgCartao,
        border: `1px solid ${cores.borda}`,
        borderTop: `2px solid ${cor}`,
        borderRadius: raio.md,
        boxShadow: sombra.cartao,
        padding: `${espaco.lg}px ${espaco.lg}px`,
        height: "100%",
      }}
    >
      <div
        style={{
          fontSize: "0.68rem",
          color: cores.textoSuave,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
          fontWeight: 600,
          marginBottom: espaco.sm,
        }}
      >
        {label}
      </div>
      <div className="font-display" style={{ fontSize: "1.7rem", fontWeight: 700, color: "white", lineHeight: 1.1 }}>
        {typeof valor === "number" ? valor.toLocaleString("pt-PT") : valor}{" "}
        <span style={{ fontSize: "0.78rem", fontWeight: 500, color: cores.textoSuave }}>{unidade}</span>
      </div>
      <div style={{ fontSize: "0.72rem", color: `${cor}${alphaHex(0.9)}`, marginTop: espaco.xs, fontWeight: 600 }}>
        {subLabel}
      </div>
    </div>
  );
}
