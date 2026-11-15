/** Peças de leitura rápida partilhadas por toda a app: número grande (KPI) com
 * explicação de um clique, e a legenda da linguagem de cor (ver theme.ts). */
import { cores, desvio, espaco, estado, raio } from "@/lib/theme";
import type { Tr } from "@/lib/i18n/core";
import { Ajuda } from "./Ajuda";

/** Cartão de número grande. `ajuda` = como se calcula / como se lê (ícone «i»). */
export function Kpi({ rotulo, valor, unidade, rodape, cor, destaque, ajuda }: {
  rotulo: string; valor: string; unidade?: string; rodape?: React.ReactNode; cor?: string; destaque?: string; ajuda?: React.ReactNode;
}) {
  return (
    <div style={{
      background: destaque ? `color-mix(in srgb, ${destaque} 9%, ${cores.bgCartao})` : cores.bgCartao,
      border: `1px solid ${destaque ? `color-mix(in srgb, ${destaque} 40%, transparent)` : cores.borda}`,
      borderRadius: raio.md, padding: `${espaco.md}px ${espaco.lg}px`, minWidth: 0,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.68rem", fontWeight: 600, letterSpacing: "0.04em", textTransform: "uppercase", color: cores.textoSuave }}>
        <span>{rotulo}</span>{ajuda && <Ajuda>{ajuda}</Ajuda>}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 5, marginTop: 4 }}>
        <span className="font-display" style={{ fontSize: "1.65rem", fontWeight: 700, color: cor ?? cores.textoForte, letterSpacing: "-0.02em", lineHeight: 1.1 }}>{valor}</span>
        {unidade && <span style={{ fontSize: "0.8rem", color: cores.textoSuave }}>{unidade}</span>}
      </div>
      {rodape && <div style={{ fontSize: "0.74rem", color: cores.textoSuave, marginTop: 4 }}>{rodape}</div>}
    </div>
  );
}

function Item({ cor, texto }: { cor: string; texto: string }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 5, whiteSpace: "nowrap" }}>
      <span style={{ width: 9, height: 9, borderRadius: 3, background: cor }} />{texto}
    </span>
  );
}

/** Legenda da linguagem de cor. `tipos`: estado (agir/vigiar/normal/feito),
 * alvo (% do alvo) e/ou desvio (acima/abaixo do habitual). */
export function LegendaCores({ tr, tipos }: { tr: Tr; tipos: ("estado" | "alvo" | "desvio")[] }) {
  return (
    <div style={{ display: "flex", gap: espaco.md, flexWrap: "wrap", fontSize: "0.72rem", color: cores.textoSuave }}>
      {tipos.includes("estado") && <>
        <Item cor={estado.agir} texto={tr("agir")} /><Item cor={estado.vigiar} texto={tr("vigiar")} />
        <Item cor={estado.normal} texto={tr("normal")} /><Item cor={estado.ok} texto={tr("feito")} />
      </>}
      {tipos.includes("alvo") && <>
        <Item cor={estado.ok} texto={tr("90–110 % do alvo")} /><Item cor={estado.vigiar} texto={tr("80–90 / 110–120 %")} />
        <Item cor={estado.agir} texto={tr("< 80 / > 120 %")} />
      </>}
      {tipos.includes("desvio") && <>
        <Item cor={desvio.acima} texto={tr("acima do habitual")} /><Item cor={desvio.abaixo} texto={tr("abaixo do habitual")} />
      </>}
    </div>
  );
}
