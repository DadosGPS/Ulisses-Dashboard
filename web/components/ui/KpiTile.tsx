import { alphaHex, cores, espaco, raio, sombra, letra } from "@/lib/theme";
import { obterTr } from "@/lib/i18n/servidor";

/** Porta e refinamento de team_kpi_tile() em utils/ui_safe.py — visual estilo BI (cartão com sombra/profundidade). */
export async function KpiTile({
  label,
  valor,
  unidade,
  subLabel,
  cor,
}: {
  label: string;
  valor: number | string;
  unidade: string;
  subLabel: React.ReactNode;
  cor: string;
}) {
  const tr = await obterTr();
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
          fontSize: letra.legenda,
          color: cores.textoSuave,
          letterSpacing: "0.04em",
          textTransform: "uppercase",
          fontWeight: 600,
          marginBottom: espaco.sm,
        }}
      >
        {label}
      </div>
      <div className="font-display" style={{ fontSize: letra.titulo, fontWeight: 700, color: cores.textoForte, lineHeight: 1.1 }}>
        {typeof valor === "number" ? valor.toLocaleString(tr.loc) : valor}{" "}
        <span style={{ fontSize: letra.pequeno, fontWeight: 600, color: cores.textoSuave }}>{unidade}</span>
      </div>
      <div style={{ fontSize: letra.pequeno, color: `${cor}${alphaHex(0.9)}`, marginTop: espaco.xs, fontWeight: 600 }}>
        {subLabel}
      </div>
    </div>
  );
}
