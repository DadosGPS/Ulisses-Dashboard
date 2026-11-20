"use client";

/** Relatório de jogo — partes interativas: o gráfico principal do plantel,
 * o perfil por posição e, no relatório individual, os mostradores face à
 * época e a evolução jogo a jogo. */
import { useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { BarrasAgrupadas, BarrasJogadores, Escolha, Mostrador, type LinhaBarra } from "@/components/graficos/Graficos";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { useTr } from "@/lib/i18n/cliente";
import { corDesvio, cores, desvio, espaco, raio, letra } from "@/lib/theme";
import { COR, dataCurta, fmt, fmtPct, type Estado, type MetricaDesc } from "./comum";

interface ValorJ { valor: number | null; por_min: number | null; media_epoca_min: number | null; media_epoca: number | null; estado: Estado; delta_pct: number | null }
interface LinhaJ { jogador: string; posicao: string; minutos: number | null; n_jogos_epoca: number; dist_min: number | null; valores: Record<string, ValorJ> }
type Pos = { posicao: string } & Record<string, { jogo: number | null; epoca: number | null; delta_pct: number | null } | string>;

type Lente = "alta" | "distancia" | "acc_dcc" | "vmax";

export function PlantelJogo({ jogadores, metricas, data, selecionado }: { jogadores: LinhaJ[]; metricas: MetricaDesc[]; data: string; selecionado?: string | null }) {
  const tr = useTr();
  const loc = tr.loc;
  const router = useRouter();
  const pathname = usePathname();
  const { oculto } = usePrivacidade();
  const tem = (k: string) => metricas.some((m) => m.chave === k);
  const lentes: { valor: Lente; texto: string }[] = [
    ...(tem("hsr") ? [{ valor: "alta" as Lente, texto: tr("HSR + sprint") }] : []),
    ...(tem("distancia") ? [{ valor: "distancia" as Lente, texto: tr("Distância") }] : []),
    ...(tem("acc") || tem("dcc") ? [{ valor: "acc_dcc" as Lente, texto: tr("Acc + Dcc") }] : []),
    ...(tem("vmax") ? [{ valor: "vmax" as Lente, texto: tr("Vel. máx.") }] : []),
  ];
  const [lente, setLente] = useState<Lente>(lentes[0]?.valor ?? "distancia");
  const [porMin, setPorMin] = useState(false);

  const linhas: LinhaBarra[] = useMemo(() => {
    const ls = jogadores.map((j) => {
      const v = j.valores;
      const min = j.minutos || null;
      const nome = nomeOuOculto(j.jogador, oculto);
      const div = (x: number | null | undefined) => (x == null ? 0 : porMin && min ? x / min : x);
      const casas = porMin ? 1 : 0;
      let segs: { valor: number; cor: string; rotulo: string }[] = [];
      let delta: number | null = null;
      let marcador: number | null = null;
      if (lente === "alta") {
        segs = [{ valor: div(v.hsr?.valor), cor: COR.hsr, rotulo: "HSR" }, ...(v.sprint ? [{ valor: div(v.sprint.valor), cor: COR.sprint, rotulo: "Sprint" }] : [])];
        delta = v.hsr?.delta_pct ?? null;
        marcador = porMin && v.hsr?.media_epoca_min != null ? v.hsr.media_epoca_min + (v.sprint?.media_epoca_min ?? 0) : null;
      } else if (lente === "distancia") {
        segs = [{ valor: div(v.distancia?.valor), cor: COR.distancia, rotulo: tr("Distância") }];
        delta = v.distancia?.delta_pct ?? null;
        marcador = porMin ? v.distancia?.media_epoca_min ?? null : null;
      } else if (lente === "acc_dcc") {
        segs = [{ valor: div(v.acc?.valor), cor: COR.acc, rotulo: "Acc" }, { valor: div(v.dcc?.valor), cor: COR.dcc, rotulo: "Dcc" }];
        delta = v.acc?.delta_pct ?? null;
        marcador = porMin && v.acc?.media_epoca_min != null ? v.acc.media_epoca_min + (v.dcc?.media_epoca_min ?? 0) : null;
      } else {
        segs = [{ valor: v.vmax?.valor ?? 0, cor: COR.vmax, rotulo: tr("Vel. máx.") }];
        delta = v.vmax?.delta_pct ?? null;
        marcador = v.vmax?.media_epoca ?? null;
      }
      const total = segs.reduce((s, x) => s + x.valor, 0);
      const txt = lente === "vmax" ? fmt(total, 1, loc) : fmt(total, casas, loc);
      return {
        id: j.jogador, rotulo: nome, sub: `${j.posicao} · ${fmt(j.minutos, 0, loc)}′`, _t: total,
        segmentos: segs, marcador, texto: txt, corTexto: corDesvio(delta, 10), esmaecido: (j.minutos ?? 0) < 30,
        dica: <><b>{nome}</b> · {fmt(j.minutos, 0, loc)} min<br />{segs.map((s) => <span key={s.rotulo}>{s.rotulo}: {fmt(s.valor, lente === "vmax" ? 1 : casas, loc)}{porMin && lente !== "vmax" ? "/min" : ""}<br /></span>)}
          {delta != null ? <>{tr("Ritmo vs a época dele")}: {fmtPct(delta, loc)}</> : tr("Sem jogos suficientes para comparar")}</>,
      };
    });
    return ls.sort((a, b) => b._t - a._t);
  }, [jogadores, lente, porMin, oculto, loc, tr]);

  return (
    <div style={cartao}>
      <div style={{ display: "flex", alignItems: "center", gap: espaco.md, flexWrap: "wrap", marginBottom: espaco.sm }}>
        <h2 className="font-display" style={titulo}>{tr("Num relance")}</h2>
        <Escolha rotulo={tr("Métrica")} valor={lente} onChange={setLente} opcoes={lentes} />
        {lente !== "vmax" && <Escolha rotulo={tr("Unidade")} valor={porMin ? "min" : "total"} onChange={(v) => setPorMin(v === "min")}
          opcoes={[{ valor: "total", texto: tr("Totais") }, { valor: "min", texto: tr("Por minuto") }]} />}
      </div>
      <p style={legenda}>
        {lente === "alta" ? tr("HSR (laranja) + sprint (vermelho) de cada jogador. ") : lente === "acc_dcc" ? tr("Acelerações + desacelerações de cada jogador. ") : ""}
        {porMin || lente === "vmax" ? tr("O traço é a média dele na época. ") : ""}
        {tr("Número a azul/violeta = ritmo bem acima/abaixo da época dele. Menos de 30 min a esbatido. Clica para o relatório individual.")}
      </p>
      <BarrasJogadores linhas={linhas} selecionado={selecionado} larguraRotulo={200}
        onClick={(id) => router.push(`${pathname}?data=${data}&jogador=${encodeURIComponent(id)}#individual`, { scroll: false })} />
    </div>
  );
}

export function PosicoesJogo({ posicoes }: { posicoes: Pos[] }) {
  const tr = useTr();
  const loc = tr.loc;
  const [k, setK] = useState<"distancia" | "hsr" | "sprint">("hsr");
  const disponiveis = (["distancia", "hsr", "sprint"] as const).filter((c) => posicoes.some((p) => p[c]));
  return (
    <>
      <div style={{ marginBottom: espaco.sm }}>
        <Escolha rotulo={tr("Métrica")} valor={k} onChange={setK}
          opcoes={disponiveis.map((c) => ({ valor: c, texto: tr(c === "distancia" ? "Distância" : c === "hsr" ? "HSR" : "Sprint") }))} />
      </div>
      <BarrasAgrupadas altura={150} formato={(v) => fmt(v, 0, loc)}
        categorias={posicoes.map((p) => {
          const v = p[k] as { jogo: number | null; epoca: number | null; delta_pct: number | null } | undefined;
          return {
            rotulo: p.posicao,
            sub: <span style={{ color: corDesvio(v?.delta_pct), fontWeight: 600 }}>{fmtPct(v?.delta_pct, loc)}</span>,
            series: [
              { valor: v?.epoca ?? null, cor: `color-mix(in srgb, ${cores.textoSuave} 45%, transparent)`, rotulo: tr("Média da época") },
              { valor: v?.jogo ?? null, cor: COR[k], rotulo: tr("Este jogo") },
            ],
          };
        })} />
      <div style={{ display: "flex", gap: espaco.md, fontSize: letra.pequeno, color: cores.textoSuave, marginTop: 4 }}>
        <span><span style={{ ...quadrado, background: COR[k] }} />{tr("Este jogo")}</span>
        <span><span style={{ ...quadrado, background: `color-mix(in srgb, ${cores.textoSuave} 45%, transparent)` }} />{tr("Média da época")}</span>
      </div>
    </>
  );
}

interface Gauge { valor: number | null; total: number | null; media: number | null; dp: number | null; min: number | null; max: number | null; rank: number | null; n: number; estado: string }
interface JogoInd { data: string; adversario: string | null; minutos: number | null; atual: boolean; valores: Record<string, { valor: number | null; estado: Estado }> }

export function MostradoresJogo({ gauges, metricas, minutos }: { gauges: Record<string, Gauge>; metricas: MetricaDesc[]; minutos: number | null }) {
  const tr = useTr();
  const loc = tr.loc;
  return (
    <>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: espaco.sm }}>
        {metricas.map((m) => {
          const g = gauges[m.chave];
          if (!g) return null;
          const vm = m.chave === "vmax";
          return (
            <Mostrador key={m.chave} titulo={vm ? tr(m.label) : tr("{0} / min", [tr(m.label)])}
              valor={g.valor} texto={fmt(g.valor, vm ? 1 : m.chave === "distancia" ? 0 : 1, loc)} unidade={vm ? "km/h" : undefined}
              media={g.media} dp={g.dp} min={g.min} max={g.max} estadoTxt={g.estado}
              rodape={<>{vm ? "" : <>{tr("Total")} {fmt(g.total, m.casas, loc)} · </>}{tr("média")} {fmt(g.media, vm ? 1 : 1, loc)}{g.rank ? ` · #${g.rank}/${g.n}` : ""}</>} />
          );
        })}
      </div>
      <p style={legenda}>
        {tr("Ponteiro = este jogo ({0} min), por minuto (a velocidade em bruto). Faixa cinzenta = a época dele ± 1 DP; traço = a média. ▲ azul / ▼ violeta = fora da faixa.", [fmt(minutos, 0, loc)])}
      </p>
    </>
  );
}

export function JogoAJogo({ jogos, metricas, jogador }: { jogos: JogoInd[]; metricas: MetricaDesc[]; jogador: string }) {
  const tr = useTr();
  const loc = tr.loc;
  const router = useRouter();
  const pathname = usePathname();
  const [k, setK] = useState(metricas.find((m) => m.chave === "hsr")?.chave ?? metricas[0]?.chave);
  const m = metricas.find((x) => x.chave === k)!;
  const cron = [...jogos].reverse();
  const max = Math.max(1, ...cron.map((g) => g.valores[k]?.valor ?? 0)) * 1.1;
  return (
    <div>
      <div style={{ marginBottom: espaco.sm }}>
        <Escolha rotulo={tr("Métrica")} valor={k} onChange={setK} opcoes={metricas.map((x) => ({ valor: x.chave, texto: tr(x.label) }))} />
      </div>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 4, height: 130, padding: "0 2px", overflowX: "auto" }}>
        {cron.map((g) => {
          const v = g.valores[k];
          const cor = v?.estado === "alto" ? desvio.acima : v?.estado === "baixo" ? desvio.abaixo : COR[k];
          return (
            <button key={g.data} title={`${dataCurta(g.data, loc)}${g.adversario ? ` · ${g.adversario}` : ""} · ${fmt(g.minutos, 0, loc)}′ · ${fmt(v?.valor, m.casas, loc)}`}
              onClick={() => router.push(`${pathname}?data=${g.data}&jogador=${encodeURIComponent(jogador)}#individual`, { scroll: false })}
              style={{ flex: "1 0 18px", maxWidth: 38, height: "100%", display: "flex", flexDirection: "column", justifyContent: "flex-end", alignItems: "center", background: "none", border: "none", padding: 0, cursor: "pointer" }}>
              <div style={{ width: "100%", height: `${((v?.valor ?? 0) / max) * 100}%`, minHeight: v?.valor ? 2 : 0, background: cor, opacity: (g.minutos ?? 0) < 30 ? 0.35 : 1,
                borderRadius: "3px 3px 0 0", outline: g.atual ? `2px solid ${cores.textoForte}` : "none", outlineOffset: 1 }} />
            </button>
          );
        })}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: letra.legenda, color: cores.textoFraco, marginTop: 4 }}>
        <span>{cron[0] ? dataCurta(cron[0].data, loc) : ""}</span><span>{tr("contorno = jogo escolhido · esbatido = < 30 min · clica para abrir o jogo")}</span>
        <span>{cron.length ? dataCurta(cron[cron.length - 1].data, loc) : ""}</span>
      </div>
    </div>
  );
}

const cartao: React.CSSProperties = { background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.lg, minWidth: 0 };
const titulo: React.CSSProperties = { margin: 0, fontSize: letra.realce, fontWeight: 600, color: cores.textoForte };
const legenda: React.CSSProperties = { fontSize: letra.pequeno, color: cores.textoSuave, margin: `${espaco.sm}px 0`, lineHeight: 1.45 };
const quadrado: React.CSSProperties = { display: "inline-block", width: 9, height: 9, borderRadius: 2, marginRight: 4 };
