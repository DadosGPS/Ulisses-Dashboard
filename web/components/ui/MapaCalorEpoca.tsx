"use client";

/** Mapa de calor da época — jogadores × microciclos.
 *
 * Primeiro escolhe-se a PERGUNTA (volume da semana · exposição vs jogo ·
 * mudanças de carga), depois a métrica. Por omissão cada linha é colorida
 * FACE AO PRÓPRIO JOGADOR (não um ranking entre jogadores). As cores seguem a linguagem da app:
 *  · volume: escala azul; «face ao próprio jogador» realça a semana atípica de
 *    cada um (em vez de quem faz sempre mais);
 *  · exposição e semana vs normal: zonas — vermelho agir, laranja vigiar, verde na zona;
 *  · variação semanal: azul subiu / violeta desceu. */
import { useMemo, useState } from "react";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { cores, desvio, espaco, estado, raio } from "@/lib/theme";
import type { MapaCalorResponse } from "@/lib/types";
import { useTr } from "@/lib/i18n/cliente";
import { Escolha } from "@/components/graficos/Graficos";

type Metrica = MapaCalorResponse["metricas"][number];
type Escala = "equipa" | "jogador";

const mistura = (cor: string, t: number) => `color-mix(in srgb, ${cor} ${Math.round(Math.max(0, Math.min(1, t)) * 100)}%, var(--bg-cartao))`;
const AZUL = desvio.acima;

function corZona(v: number, chave: string, zonas: MapaCalorResponse["zonas"]): { bg: string; fg: string } {
  const z = zonas?.[chave];
  if (!z) return { bg: cores.superficie, fg: cores.texto };
  const [lo, hi] = z.ok;
  let cor: string;
  if (chave === "vs_normal") cor = v > (z.agir ?? 50) ? estado.agir : v > hi ? estado.vigiar : v < lo ? desvio.abaixo : estado.normal;
  else cor = v < lo ? estado.agir : v > hi ? estado.vigiar : estado.ok;
  return { bg: mistura(cor, 0.38), fg: cores.textoForte };
}

export function MapaCalorEpoca({ dados }: { dados: MapaCalorResponse }) {
  const tr = useTr();
  const { oculto } = usePrivacidade();
  const grupos = dados.grupos ?? [];
  const [grupo, setGrupo] = useState(grupos[0]?.chave ?? "volume");
  const doGrupo = dados.metricas.filter((m) => m.grupo === grupo);
  const [porGrupo, setPorGrupo] = useState<Record<string, string>>({});
  const chave = porGrupo[grupo] ?? doGrupo[0]?.chave;
  const cfg: Metrica | undefined = dados.metricas.find((m) => m.chave === chave);
  const [escala, setEscala] = useState<Escala>("jogador");
  const linhas = dados.dados[chave ?? ""] ?? [];

  // Escalas: global (min–max da equipa) e por jogador (média ± 2 DP da linha).
  const { min, max, porLinha } = useMemo(() => {
    const vals: number[] = [];
    const pl: Record<string, { m: number; dp: number }> = {};
    for (const l of linhas) {
      const vs = dados.microciclos.map((mc) => l.valores[String(mc)]).filter((v): v is number => v != null);
      vals.push(...vs);
      if (vs.length >= 2) {
        const m = vs.reduce((a, b) => a + b, 0) / vs.length;
        pl[l.jogador] = { m, dp: Math.sqrt(vs.reduce((a, b) => a + (b - m) ** 2, 0) / (vs.length - 1)) || 1 };
      }
    }
    return { min: vals.length ? Math.min(...vals) : 0, max: vals.length ? Math.max(...vals) : 1, porLinha: pl };
  }, [linhas, dados.microciclos]);

  if (!dados.tem_dados || dados.microciclos.length === 0 || !cfg) {
    return <p style={{ color: cores.textoSuave, fontSize: "0.85rem" }}>{tr("Sem dados suficientes para o mapa de calor.")}</p>;
  }

  function cor(v: number | null | undefined, jogador: string | null): { bg: string; fg: string } {
    if (v == null) return { bg: cores.superficie, fg: cores.textoFraco };
    if (cfg!.tipo === "zonas") return corZona(v, cfg!.chave, dados.zonas);
    if (cfg!.tipo === "diverging") {
      const t = Math.max(-1, Math.min(1, v / 50));
      return { bg: mistura(t >= 0 ? desvio.acima : desvio.abaixo, Math.abs(t) * 0.85), fg: Math.abs(t) > 0.6 ? "#fff" : cores.texto };
    }
    if (escala === "jogador" && jogador && porLinha[jogador]) {
      const { m, dp } = porLinha[jogador];
      const z = Math.max(-2, Math.min(2, (v - m) / dp));
      return { bg: mistura(z >= 0 ? desvio.acima : desvio.abaixo, Math.abs(z) / 2 * 0.85), fg: Math.abs(z) > 1.3 ? "#fff" : cores.texto };
    }
    const t = (v - min) / (max - min || 1);
    return { bg: mistura(AZUL, 0.08 + t * 0.8), fg: t > 0.6 ? "#fff" : cores.texto };
  }

  const fmt = (v: number | null | undefined) => (v == null ? "" : cfg.chave === "vs_normal" ? `${v > 0 ? "+" : ""}${v}%` : v.toLocaleString(tr.loc, { maximumFractionDigits: cfg.casas, minimumFractionDigits: cfg.tipo === "zonas" ? cfg.casas : 0 }));
  const celW = cfg.tipo === "zonas" ? 48 : 52;
  const nomeW = 170;
  const g = grupos.find((x) => x.chave === grupo);

  // Agrupar por posição (a API já ordena por posição e nome).
  const blocos: { posicao: string; linhas: typeof linhas }[] = [];
  for (const l of linhas) {
    const ult = blocos[blocos.length - 1];
    if (ult && ult.posicao === l.posicao) ult.linhas.push(l);
    else blocos.push({ posicao: l.posicao, linhas: [l] });
  }

  const legenda = cfg.tipo === "zonas"
    ? (() => {
        const z = dados.zonas?.[cfg.chave];
        if (!z) return null;
        const it = (c: string, t: string) => <span key={t} style={{ display: "inline-flex", alignItems: "center", gap: 5 }}><span style={{ width: 10, height: 10, borderRadius: 3, background: mistura(c, 0.5) }} />{t}</span>;
        return cfg.chave === "vs_normal"
          ? [it(estado.normal, tr("dentro de ±{0}% do normal dele", [z.ok[1]])), it(estado.vigiar, `+${z.ok[1]}–${z.agir ?? 50}%`), it(estado.agir, `> +${z.agir ?? 50}%`), it(desvio.abaixo, tr("abaixo de {0}%", [z.ok[0]]))]
          : [it(estado.agir, tr("abaixo de {0}× (falta estímulo)", [z.ok[0]])), it(estado.ok, `${z.ok[0]}–${z.ok[1]}×`), it(estado.vigiar, tr("acima de {0}×", [z.ok[1]]))];
      })()
    : cfg.tipo === "diverging"
      ? [<span key="a" style={{ color: desvio.acima }}>■ {tr("subiu")}</span>, <span key="b" style={{ color: desvio.abaixo }}>■ {tr("desceu")}</span>]
      : escala === "jogador"
        ? [<span key="a" style={{ color: desvio.acima }}>■ {tr("acima do normal dele")}</span>, <span key="b" style={{ color: desvio.abaixo }}>■ {tr("abaixo do normal dele")}</span>]
        : [<span key="a">{tr("mais claro = menos · mais escuro = mais")}</span>];

  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.lg }}>
      <div style={{ display: "flex", gap: espaco.md, flexWrap: "wrap", alignItems: "center" }}>
        <Escolha rotulo={tr("Pergunta")} valor={grupo} onChange={setGrupo} opcoes={grupos.map((x) => ({ valor: x.chave, texto: tr(x.label) }))} />
        {doGrupo.length > 1 && (
          <Escolha rotulo={tr("Métrica")} valor={chave!} onChange={(v) => setPorGrupo({ ...porGrupo, [grupo]: v })}
            opcoes={doGrupo.map((m) => ({ valor: m.chave, texto: tr(m.label) }))} />
        )}
        {cfg.tipo === "sequential" && (
          <Escolha rotulo={tr("Cor face a")} valor={escala} onChange={setEscala}
            opcoes={[{ valor: "jogador", texto: tr("Ao próprio jogador") }, { valor: "equipa", texto: tr("Toda a equipa") }]} />
        )}
      </div>
      <div style={{ margin: `${espaco.md}px 0`, fontSize: "0.8rem", color: cores.texto }}>
        <b>{g ? tr(g.pergunta) : ""}</b> <span style={{ color: cores.textoSuave }}>{tr(cfg.descricao)}{cfg.unidade && cfg.unidade !== "×" ? ` (${cfg.unidade})` : ""}</span>
        <div style={{ display: "flex", gap: espaco.md, flexWrap: "wrap", marginTop: 6, fontSize: "0.74rem", color: cores.textoSuave }}>{legenda}</div>
      </div>

      <div style={{ overflowX: "auto" }}>
        <table style={{ borderCollapse: "separate", borderSpacing: 2 }}>
          <thead>
            <tr>
              <th style={{ ...celNome, minWidth: nomeW, fontSize: "0.72rem", color: cores.textoSuave, textAlign: "left" }}>{tr("Semana")}</th>
              {dados.microciclos.map((mc) => (
                <th key={mc} title={dados.datas?.[String(mc)] ? tr("Começa a {0}", [dados.datas[String(mc)]]) : undefined}
                  style={{ minWidth: celW, width: celW, textAlign: "center", padding: "4px 0", fontSize: "0.7rem", color: cores.textoSuave, fontWeight: 600 }}>
                  {mc}
                  {dados.datas?.[String(mc)] && <div style={{ fontSize: "0.6rem", fontWeight: 400, color: cores.textoFraco }}>{dados.datas[String(mc)].slice(8, 10)}/{dados.datas[String(mc)].slice(5, 7)}</div>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dados.equipa?.[cfg.chave] && (
              <tr>
                <td style={{ ...celNome, minWidth: nomeW, fontWeight: 700, color: cores.textoForte, fontSize: "0.78rem", borderBottom: `2px solid ${cores.bordaForte}` }}>{tr("Média da equipa")}</td>
                {dados.microciclos.map((mc) => {
                  const v = dados.equipa![cfg.chave][String(mc)];
                  const c = cfg.tipo === "sequential" && escala === "jogador" ? { bg: cores.superficie, fg: cores.textoForte } : cor(v, null);
                  return <td key={mc} style={{ ...cel(celW), background: c.bg, color: c.fg, fontWeight: 700, borderBottom: `2px solid ${cores.bordaForte}` }}>{fmt(v)}</td>;
                })}
              </tr>
            )}
            {blocos.map((b) => [
              <tr key={`pos-${b.posicao}`}>
                <td colSpan={dados.microciclos.length + 1} style={{ ...celNome, paddingTop: 10, fontSize: "0.66rem", fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", color: cores.textoFraco }}>{b.posicao}</td>
              </tr>,
              ...b.linhas.map((l) => (
                <tr key={l.jogador}>
                  <td style={{ ...celNome, minWidth: nomeW, fontSize: "0.78rem", fontWeight: 600, color: cores.texto, whiteSpace: "nowrap" }}>{nomeOuOculto(l.jogador, oculto)}</td>
                  {dados.microciclos.map((mc) => {
                    const v = l.valores[String(mc)];
                    const c = cor(v, l.jogador);
                    const txt = fmt(v);
                    return (
                      <td key={mc} title={`${nomeOuOculto(l.jogador, oculto)} · ${tr("Semana {0}", [mc])}: ${txt || "—"}${txt && cfg.unidade ? ` ${cfg.unidade}` : ""}`}
                        style={{ ...cel(celW), background: c.bg, color: c.fg }}>{txt}</td>
                    );
                  })}
                </tr>
              )),
            ])}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const celNome: React.CSSProperties = { position: "sticky", left: 0, background: "var(--bg-cartao)", zIndex: 1, padding: "4px 8px" };
const cel = (w: number): React.CSSProperties => ({ minWidth: w, width: w, height: 26, textAlign: "center", fontSize: "0.68rem", borderRadius: 4, fontVariantNumeric: "tabular-nums" });
