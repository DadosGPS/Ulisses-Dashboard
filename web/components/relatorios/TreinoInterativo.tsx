"use client";

/** Relatório de treino — a parte interativa: o gráfico principal (quem ficou
 * dentro/fora do alvo, ou acima/abaixo do habitual), o detalhe do jogador ao
 * clicar e a intensidade de cada exercício face à média da época. */
import { useMemo, useState } from "react";
import { BarrasJogadores, Escolha, type LinhaBarra } from "@/components/graficos/Graficos";
import { NomeJogador } from "@/components/ui/NomeJogador";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { useTr } from "@/lib/i18n/cliente";
import { corAlvo, corDesvio, cores, desvio, espaco, estado, raio, letra } from "@/lib/theme";
import { COR, fmt, fmtPct, type Banda, type Estado, type MetricaDesc } from "./comum";

interface Valor { valor: number | null; alvo: number | null; pct: number | null; banda: Banda | null; habitual: number | null; habitual_dp?: number | null; vs_habitual: Estado; delta_pct: number | null }
interface Linha { jogador: string; posicao: string; minutos: number | null; dist_min: number | null; pct_vmax: number | null; recorde_vmax: number | null; valores: Record<string, Valor> }
interface ItemEx { exercicio: string; n_jogadores: number | null; duracao_min: number | null; media_epoca_min?: number | null; vs_epoca_pct?: number | null; n_epoca?: number; [k: string]: unknown }
interface LinhaEx { jogador: string; exercicio: string; minutos: number | null; dist_min: number | null; vs_equipa_pct: number | null; [k: string]: unknown }
export interface DadosTreino {
  dia_md?: string | null; n_habitual?: number; fonte_alvo?: "individual" | "equipa" | null;
  metricas?: MetricaDesc[]; jogadores?: Linha[];
  exercicios?: { itens: ItemEx[]; por_jogador: LinhaEx[] } | null; fonte_exercicios?: "jogador" | "equipa" | null;
}

type Vista = "alvo" | "habitual";

export function TreinoInterativo({ r }: { r: DadosTreino }) {
  const tr = useTr();
  const loc = tr.loc;
  const { oculto } = usePrivacidade();
  const metricas = r.metricas ?? [];
  const jogadores = r.jogadores ?? [];
  const temAlvo = !!r.fonte_alvo;
  const [chave, setChave] = useState(metricas[0]?.chave ?? "distancia");
  const [vista, setVista] = useState<Vista>(temAlvo ? "alvo" : "habitual");
  const [sel, setSel] = useState<string | null>(null);
  const m = metricas.find((x) => x.chave === chave) ?? metricas[0];
  const usaAlvo = vista === "alvo" && m?.chave !== "vmax" && jogadores.some((j) => j.valores[m?.chave ?? ""]?.pct != null);

  const linhas: LinhaBarra[] = useMemo(() => {
    if (!m) return [];
    const ls = jogadores.map((j): LinhaBarra & { _ord: number } => {
      const v = j.valores[m.chave];
      const nome = nomeOuOculto(j.jogador, oculto);
      if (m.chave === "vmax") {
        const p = j.pct_vmax;
        return {
          id: j.jogador, rotulo: nome, sub: j.posicao, _ord: p ?? -1,
          segmentos: [{ valor: p ?? 0, cor: (p ?? 0) >= 90 ? estado.ok : COR.vmax }],
          texto: p != null ? `${fmt(p, 0, loc)} %` : "—", corTexto: (p ?? 0) >= 90 ? estado.ok : cores.texto,
          dica: <><b>{nome}</b><br />{tr("Vel. máx.")}: {fmt(v?.valor, 1, loc)} km/h · {tr("recorde")} {fmt(j.recorde_vmax, 1, loc)} km/h<br />{tr("≥ 90 % do recorde = estímulo de velocidade")}</>,
        };
      }
      if (usaAlvo) {
        const p = v?.pct ?? null;
        return {
          id: j.jogador, rotulo: nome, sub: j.posicao, _ord: p ?? -1,
          segmentos: [{ valor: p ?? 0, cor: corAlvo(p) }],
          texto: p != null ? `${fmt(p, 0, loc)} %` : "—", corTexto: corAlvo(p),
          dica: <><b>{nome}</b><br />{tr(m.label)}: {fmt(v?.valor, m.casas, loc)} {m.unidade !== "n" ? m.unidade : ""} · {tr("alvo")} {fmt(v?.alvo, 0, loc)}<br />{v?.habitual != null ? tr("Habitual neste dia MD: {0}", [fmt(v.habitual, m.casas, loc)]) : ""}</>,
        };
      }
      const hab = v?.habitual ?? null, dp = v?.habitual_dp ?? null;
      return {
        id: j.jogador, rotulo: nome, sub: j.posicao, _ord: v?.valor ?? -1,
        segmentos: [{ valor: v?.valor ?? 0, cor: COR[m.chave] }],
        marcador: hab, faixaLinha: hab != null && dp != null ? [Math.max(0, hab - dp), hab + dp] : null,
        texto: fmt(v?.valor, m.casas, loc), corTexto: corDesvio(v?.delta_pct, 10),
        dica: <><b>{nome}</b><br />{tr(m.label)}: {fmt(v?.valor, m.casas, loc)}<br />{hab != null ? <>{tr("Habitual neste dia MD: {0}", [fmt(hab, m.casas, loc)])} ({fmtPct(v?.delta_pct, loc)})</> : tr("Sem histórico neste dia MD")}</>,
      };
    });
    return ls.sort((a, b) => b._ord - a._ord);
  }, [m, jogadores, usaAlvo, oculto, loc, tr]);

  const contagem = usaAlvo ? {
    abaixo: jogadores.filter((j) => (j.valores[m!.chave]?.pct ?? 100) < 90).length,
    dentro: jogadores.filter((j) => { const p = j.valores[m!.chave]?.pct; return p != null && p >= 90 && p <= 110; }).length,
    acima: jogadores.filter((j) => (j.valores[m!.chave]?.pct ?? 100) > 110).length,
  } : null;

  const jSel = jogadores.find((j) => j.jogador === sel) ?? null;
  if (!m) return null;

  return (
    <div style={{ display: "grid", gridTemplateColumns: jSel ? "minmax(0, 1.4fr) minmax(300px, 1fr)" : "minmax(0, 1fr)", gap: espaco.lg, alignItems: "start" }} className="treino-interativo">
      <div style={cartao}>
        <div style={{ display: "flex", alignItems: "center", gap: espaco.md, flexWrap: "wrap", marginBottom: espaco.md }}>
          <h2 className="font-display" style={titulo}>{tr("Num relance")}</h2>
          <Escolha rotulo={tr("Métrica")} valor={m.chave} onChange={(v) => setChave(v)}
            opcoes={metricas.map((x) => ({ valor: x.chave, texto: tr(x.chave === "vmax" ? "Vel. máx." : x.label) }))} />
          {temAlvo && m.chave !== "vmax" && (
            <Escolha rotulo={tr("Comparar com")} valor={vista} onChange={setVista}
              opcoes={[{ valor: "alvo", texto: tr("Alvo do dia") }, { valor: "habitual", texto: tr("Habitual dele") }]} />
          )}
        </div>
        <p style={legenda}>
          {m.chave === "vmax"
            ? tr("% do recorde de velocidade de cada jogador hoje. Verde = ≥ 90 % (estímulo de velocidade).")
            : usaAlvo
              ? tr("% do alvo do dia de cada jogador. Faixa verde = 90–110 %; linha = 100 %.")
              : tr("Valor de hoje; o traço é o habitual do jogador em {0} e a faixa cinzenta ± 1 DP. Número a azul = bem acima, violeta = bem abaixo.", [r.dia_md ?? "—"])}
          {" "}{tr("Clica num jogador para o detalhe.")}
        </p>
        {contagem && (
          <div style={{ display: "flex", gap: espaco.lg, marginBottom: espaco.sm, fontSize: letra.texto }}>
            <span><b style={{ color: estado.ok, fontSize: letra.realce }}>{contagem.dentro}</b> {tr("dentro")}</span>
            <span><b style={{ color: estado.vigiar, fontSize: letra.realce }}>{contagem.abaixo}</b> {tr("abaixo")}</span>
            <span><b style={{ color: estado.vigiar, fontSize: letra.realce }}>{contagem.acima}</b> {tr("acima")}</span>
          </div>
        )}
        <BarrasJogadores linhas={linhas} faixa={usaAlvo ? [90, 110] : m.chave === "vmax" ? [90, 100] : null}
          referencia={usaAlvo ? 100 : null} max={usaAlvo ? 130 : m.chave === "vmax" ? 100 : undefined} larguraRotulo={190}
          onClick={(id) => setSel(sel === id ? null : id)} selecionado={sel} />
      </div>

      {jSel && <DetalheJogador j={jSel} metricas={metricas} r={r} fechar={() => setSel(null)} />}

      {r.exercicios && r.exercicios.itens.length > 0 && (
        <div style={{ ...cartao, gridColumn: "1 / -1" }}>
          <Exercicios ex={r.exercicios} jogadorSel={sel} />
        </div>
      )}
    </div>
  );
}

function DetalheJogador({ j, metricas, r, fechar }: { j: Linha; metricas: MetricaDesc[]; r: DadosTreino; fechar: () => void }) {
  const tr = useTr();
  const loc = tr.loc;
  const meus = r.exercicios?.por_jogador.filter((x) => x.jogador === j.jogador) ?? [];
  const principal = metricas.find((m) => j.valores[m.chave]?.pct != null);
  const pp = principal ? j.valores[principal.chave].pct : null;
  return (
    <div style={{ ...cartao, position: "sticky", top: 12 }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: espaco.md }}>
        <div style={{ width: 58, height: 58, borderRadius: "50%", flexShrink: 0, display: "grid", placeItems: "center",
          background: `conic-gradient(${corAlvo(pp)} ${Math.min(100, pp ?? 0) * 3.6}deg, ${cores.superficie} 0)` }}>
          <div style={{ width: 46, height: 46, borderRadius: "50%", background: cores.bgCartao, display: "grid", placeItems: "center", fontSize: letra.pequeno, fontWeight: 700, color: cores.textoForte }}>
            {pp != null ? `${fmt(pp, 0, loc)}%` : "—"}
          </div>
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: letra.realce, fontWeight: 700, color: cores.textoForte }}><NomeJogador nome={j.jogador} /></div>
          <div style={{ fontSize: letra.pequeno, color: cores.textoSuave }}>
            {j.posicao} · {fmt(j.minutos, 0, loc)} min · {fmt(j.dist_min, 0, loc)} m/min{principal ? ` · ${tr("{0} do alvo de {1}", [pp != null ? `${fmt(pp, 0, loc)} %` : "—", tr(principal.label)])}` : ""}
          </div>
        </div>
        <button onClick={fechar} aria-label={tr("Fechar")} style={{ background: "none", border: "none", color: cores.textoSuave, cursor: "pointer", fontSize: letra.realce }}>×</button>
      </div>

      <div style={{ fontSize: letra.legenda, fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase", color: cores.textoSuave, margin: `${espaco.lg}px 0 ${espaco.sm}px` }}>
        {tr("vs o habitual dele em {0}", [r.dia_md ?? "—"])}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {metricas.map((m) => {
          const v = j.valores[m.chave];
          if (!v) return null;
          const hab = v.habitual, dp = v.habitual_dp ?? null;
          const topo = Math.max(v.valor ?? 0, (hab ?? 0) + (dp ?? 0), 1) * 1.15;
          const p = (x: number) => `${Math.max(0, Math.min(100, (x / topo) * 100))}%`;
          const est = v.vs_habitual === "alto" ? tr("Acima") : v.vs_habitual === "baixo" ? tr("Abaixo") : v.vs_habitual === "normal" ? tr("Normal") : tr("Sem histórico");
          const corE = v.vs_habitual === "alto" ? desvio.acima : v.vs_habitual === "baixo" ? desvio.abaixo : cores.textoSuave;
          return (
            <div key={m.chave}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: letra.pequeno }}>
                <span style={{ color: cores.texto }}>{tr(m.label)} <b>{fmt(v.valor, m.casas, loc)}</b>{hab != null && <span style={{ color: cores.textoSuave }}> {tr("vs")} {fmt(hab, m.casas, loc)}</span>}</span>
                <span style={{ fontWeight: 700, color: corE }}>{est}</span>
              </div>
              <div style={{ position: "relative", height: 8, background: cores.superficie, borderRadius: 4, marginTop: 4 }}>
                {hab != null && dp != null && <div style={{ position: "absolute", top: 0, bottom: 0, left: p(Math.max(0, hab - dp)), width: `calc(${p(hab + dp)} - ${p(Math.max(0, hab - dp))})`, background: `color-mix(in srgb, ${cores.textoSuave} 25%, transparent)`, borderRadius: 4 }} />}
                {v.valor != null && <div style={{ position: "absolute", top: -3, width: 12, height: 14, borderRadius: "50%", left: `calc(${p(v.valor)} - 6px)`, background: corE === cores.textoSuave ? COR[m.chave] : corE, border: `2px solid ${cores.bgCartao}` }} />}
              </div>
            </div>
          );
        })}
      </div>

      {meus.length > 0 && (
        <>
          <div style={{ fontSize: letra.legenda, fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase", color: cores.textoSuave, margin: `${espaco.lg}px 0 ${espaco.sm}px` }}>{tr("Os exercícios dele")}</div>
          <BarrasJogadores larguraRotulo={130} altura={14}
            linhas={meus.map((x) => ({
              id: x.exercicio, rotulo: x.exercicio, segmentos: [{ valor: x.dist_min ?? 0, cor: COR.distancia }],
              texto: `${fmt(x.dist_min, 0, loc)}`, corTexto: corDesvio(x.vs_equipa_pct, 10),
              dica: <>{x.exercicio}: {fmt(x.dist_min, 0, loc)} m/min · {fmtPct(x.vs_equipa_pct, loc)} {tr("vs equipa")}</>,
            }))} />
          <p style={legenda}>{tr("m/min em cada exercício; número a azul/violeta = bem acima/abaixo da equipa no mesmo exercício.")}</p>
        </>
      )}
    </div>
  );
}

function Exercicios({ ex, jogadorSel }: { ex: NonNullable<DadosTreino["exercicios"]>; jogadorSel: string | null }) {
  const tr = useTr();
  const loc = tr.loc;
  const { oculto } = usePrivacidade();
  const [aberto, setAberto] = useState<string | null>(null);
  const itens = ex.itens;
  const linhas: LinhaBarra[] = itens.map((i) => ({
    id: i.exercicio, rotulo: i.exercicio, sub: `${fmt(i.duracao_min, 0, loc)}′`,
    segmentos: [{ valor: (i.distancia_min as number) ?? 0, cor: COR.distancia }],
    marcador: i.media_epoca_min ?? null,
    texto: `${fmt(i.distancia_min as number, 0, loc)}`, corTexto: corDesvio(i.vs_epoca_pct ?? null, 10),
    dica: <><b>{i.exercicio}</b> · {fmt(i.duracao_min, 0, loc)} min · {fmt(i.n_jogadores, 0, loc)} {tr("jog.")}<br />
      {fmt(i.distancia_min as number, 1, loc)} m/min · HSR {fmt(i.hsr_min as number, 1, loc)}/min<br />
      {i.media_epoca_min != null ? tr("Média da época: {0} m/min ({1})", [fmt(i.media_epoca_min, 1, loc), fmtPct(i.vs_epoca_pct ?? null, loc)]) : tr("Primeira vez deste exercício")}</>,
  }));
  const doEx = ex.por_jogador.filter((p) => p.exercicio === aberto);
  const mediaEx = itens.find((i) => i.exercicio === aberto)?.distancia_min as number | undefined;
  return (
    <>
      <div style={{ display: "flex", alignItems: "baseline", gap: espaco.md, flexWrap: "wrap" }}>
        <h2 className="font-display" style={titulo}>{tr("Intensidade dos exercícios")}</h2>
        <span style={legenda}>{tr("m/min de cada exercício hoje; o traço é a média desse exercício na época. Clica num exercício para ver os jogadores.")}</span>
      </div>
      <div style={{ display: "flex", height: 10, borderRadius: 4, overflow: "hidden", margin: `${espaco.sm}px 0 ${espaco.md}px` }}>
        {itens.map((i, n) => (
          <div key={i.exercicio} title={`${i.exercicio} · ${i.duracao_min ?? "—"} min`}
            style={{ flex: i.duracao_min ?? 1, background: [cores.distanciaTotal, cores.hsr, cores.acc, cores.velMax, cores.sprint, cores.dcc][n % 6], opacity: aberto && aberto !== i.exercicio ? 0.3 : 1 }} />
        ))}
      </div>
      <BarrasJogadores linhas={linhas} onClick={(id) => setAberto(aberto === id ? null : id)} selecionado={aberto} larguraRotulo={190} />
      {aberto && doEx.length > 0 && (
        <div style={{ marginTop: espaco.lg }}>
          <div style={{ fontSize: letra.texto, fontWeight: 600, color: cores.textoForte, marginBottom: espaco.sm }}>{aberto} · {tr("m/min por jogador (traço = média da equipa)")}</div>
          <BarrasJogadores selecionado={jogadorSel}
            linhas={[...doEx].sort((a, b) => (b.dist_min ?? 0) - (a.dist_min ?? 0)).map((p) => ({
              id: p.jogador, rotulo: nomeOuOculto(p.jogador, oculto), segmentos: [{ valor: p.dist_min ?? 0, cor: COR.distancia }],
              marcador: mediaEx ?? null, texto: fmt(p.dist_min, 0, loc), corTexto: corDesvio(p.vs_equipa_pct, 10),
              dica: <>{nomeOuOculto(p.jogador, oculto)} · {fmt(p.minutos, 0, loc)} min · {fmtPct(p.vs_equipa_pct, loc)} {tr("vs equipa")}</>,
            }))} />
        </div>
      )}
    </>
  );
}

const cartao: React.CSSProperties = { background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.lg, minWidth: 0 };
const titulo: React.CSSProperties = { margin: 0, fontSize: letra.realce, fontWeight: 600, color: cores.textoForte };
const legenda: React.CSSProperties = { fontSize: letra.pequeno, color: cores.textoSuave, margin: `0 0 ${espaco.sm}px`, lineHeight: 1.45 };
