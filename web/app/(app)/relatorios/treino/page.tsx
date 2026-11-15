import Link from "next/link";
import { PageHeader } from "@/components/layout/PageHeader";
import { Cartao, EstadoVazio, SecaoTitulo } from "@/components/ui/base";
import { NomeJogador } from "@/components/ui/NomeJogador";
import { BotaoImprimir, SeletorSessao } from "@/components/relatorios/Seletores";
import {
  COR, COR_BANDA, CelulaPct, Kpi, LegendaBandas, MarcaEstado, dataCurta, fmt, fmtPct, nota, tabela, td, tdEsq, th, thEsq,
  type Banda, type Estado, type MetricaDesc,
} from "@/components/relatorios/comum";
import { contextoEquipa, getApi } from "@/lib/api-servidor";
import { obterTr } from "@/lib/i18n/servidor";
import { cores, espaco } from "@/lib/theme";

interface Valor { valor: number | null; alvo: number | null; pct: number | null; banda: Banda | null; habitual: number | null; vs_habitual: Estado; delta_pct: number | null }
interface Linha {
  jogador: string; posicao: string; minutos: number | null; dist_min: number | null; pct_vmax: number | null; recorde_vmax: number | null;
  metrica_principal: string | null; pct_alvo: number | null; banda: Banda | null; valores: Record<string, Valor>;
}
interface ItemEx {
  exercicio: string; n_jogadores: number | null; duracao_min: number | null; media_epoca_min?: number | null; vs_epoca_pct?: number | null; n_epoca?: number;
  [k: string]: unknown;
}
interface LinhaEx { jogador: string; exercicio: string; minutos: number | null; dist_min: number | null; vs_equipa_pct: number | null; [k: string]: unknown }
interface Relatorio {
  tem_dados: boolean; sessoes: { data: string; dia_md: string | null }[];
  data?: string; dia_md?: string | null; microciclo?: number | null; duracao_min?: number | null; n_jogadores?: number;
  fonte_alvo?: "individual" | "equipa" | null; n_habitual?: number;
  metricas?: MetricaDesc[]; kpis?: { chave: string; media: number | null; pct_alvo: number | null; abaixo: number; dentro: number; acima: number }[];
  resumo_alvo?: { abaixo: number; dentro: number; acima: number }; jogadores?: Linha[];
  exercicios?: { itens: ItemEx[]; por_jogador: LinhaEx[] } | null; fonte_exercicios?: "jogador" | "equipa" | null;
}

export default async function RelatorioTreinoPage({ searchParams }: { searchParams: Promise<{ data?: string }> }) {
  const tr = await obterTr();
  const loc = tr.loc;
  const { data } = await searchParams;
  const ctx = await contextoEquipa();
  if (!ctx) return null;
  if (ctx === "sem_equipa") return <EstadoVazio mensagem={tr("Ainda não estás associado a nenhuma equipa.")} />;

  let r: Relatorio;
  try {
    r = await getApi<Relatorio>(`/api/teams/${ctx.teamId}/relatorios/treino`, ctx.token, { data });
  } catch {
    return <EstadoVazio mensagem={tr("Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr.")} />;
  }
  if (!r.tem_dados || !r.data) {
    return <EstadoVazio acao={{ href: "/upload", label: tr("Importar GPS") }} mensagem={tr("Ainda não há treinos com dados de GPS para esta equipa.")} />;
  }

  const metricas = r.metricas ?? [];
  const volume = metricas.filter((m) => m.chave !== "vmax");
  const temAlvo = !!r.fonte_alvo;
  const opcoes = r.sessoes.map((s) => ({ valor: s.data, texto: `${dataCurta(s.data, loc)}${s.dia_md ? ` · ${s.dia_md}` : ""}` }));
  const kpi = (k: string) => r.kpis?.find((x) => x.chave === k);
  const ex = r.exercicios;

  return (
    <div>
      <PageHeader
        titulo={tr("Relatório de treino")}
        subtitulo={`${dataCurta(r.data, loc)}${r.dia_md ? ` · ${r.dia_md}` : ""}${r.microciclo ? ` · ${tr("Microciclo {0}", [r.microciclo])}` : ""} · ${tr("{0} jogadores", [r.n_jogadores ?? 0])}`}
        acoes={<><SeletorSessao opcoes={opcoes} atual={r.data} rotulo="Sessão" /><BotaoImprimir /></>}
      />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px`, display: "flex", flexDirection: "column", gap: espaco.xl }}>

        {/* KPIs */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: espaco.md }}>
          {volume.slice(0, 3).map((m) => {
            const k = kpi(m.chave);
            const pct = k?.pct_alvo ?? null;
            const banda: Banda | null = pct === null ? null : pct < 80 ? "muito_abaixo" : pct < 90 ? "abaixo" : pct <= 110 ? "dentro" : pct <= 120 ? "acima" : "muito_acima";
            return (
              <Kpi key={m.chave} rotulo={tr("{0} · média", [tr(m.label)])} valor={fmt(k?.media, m.casas, loc)} unidade={m.unidade}
                destaque={banda ? COR_BANDA[banda] : undefined}
                rodape={pct !== null ? <span style={{ color: banda ? COR_BANDA[banda] : undefined, fontWeight: 600 }}>{tr("{0} % do alvo", [fmt(pct, 0, loc)])}</span> : tr("sem alvo para este dia")} />
            );
          })}
          {temAlvo && r.resumo_alvo && (
            <Kpi rotulo={tr("Alvo do dia")} valor={`${r.resumo_alvo.dentro}`} unidade={tr("dentro")}
              rodape={<span><b style={{ color: cores.info }}>{r.resumo_alvo.abaixo}</b> {tr("abaixo")} · <b style={{ color: cores.atencao }}>{r.resumo_alvo.acima}</b> {tr("acima")}</span>} />
          )}
        </div>

        {/* Tabela por jogador */}
        <Cartao>
          <SecaoTitulo
            subtitulo={temAlvo
              ? (r.fonte_alvo === "individual"
                ? tr("Alvo de cada jogador = % do dia no plano × fator semanal do microciclo × a referência de jogo dele.")
                : tr("Alvo = o planeado da equipa para este dia (igual para todos). Para alvos individuais, planeia o dia em % do objetivo semanal no Calendário."))
              : tr("Sem alvo planeado para este dia — planeia-o no Calendário. A comparação abaixo é com o habitual de cada jogador.")}
            acoes={temAlvo ? <LegendaBandas tr={tr} /> : undefined}
          >{tr("Jogadores")}</SecaoTitulo>
          <div style={{ overflowX: "auto" }}>
            <table style={{ ...tabela, minWidth: 820 }}>
              <thead>
                <tr>
                  <th style={thEsq}>{tr("Jogador")}</th>
                  <th style={th}>{tr("Min")}</th>
                  {volume.map((m) => (
                    <th key={m.chave} style={{ ...th, color: COR[m.chave] }} colSpan={temAlvo ? 2 : 1}>{tr(m.label)} {m.unidade !== "n" ? `(${m.unidade})` : ""}</th>
                  ))}
                  <th style={th}>{tr("m/min")}</th>
                  <th style={th}>{tr("Vel. máx.")}</th>
                  <th style={th}>{tr("% do recorde")}</th>
                </tr>
              </thead>
              <tbody>
                {(r.jogadores ?? []).map((j) => (
                  <tr key={j.jogador}>
                    <td style={tdEsq}>
                      <span style={{ fontWeight: 600, color: cores.textoForte }}><NomeJogador nome={j.jogador} /></span>
                      <span style={{ color: cores.textoSuave, fontSize: "0.72rem", marginLeft: 6 }}>{j.posicao}</span>
                    </td>
                    <td style={td}>{fmt(j.minutos, 0, loc)}</td>
                    {volume.map((m) => {
                      const v = j.valores[m.chave];
                      return [
                        <td key={m.chave} style={td} title={v?.habitual !== null && v?.habitual !== undefined ? tr("Habitual neste dia MD: {0}", [fmt(v.habitual, m.casas, loc)]) : undefined}>
                          {fmt(v?.valor, m.casas, loc)}{v && <MarcaEstado estado={v.vs_habitual} delta={v.delta_pct} tr={tr} />}
                        </td>,
                        temAlvo ? <td key={`${m.chave}-p`} style={{ ...td, paddingLeft: 2 }} title={v?.alvo ? tr("Alvo: {0}", [fmt(v.alvo, 0, loc)]) : undefined}><CelulaPct pct={v?.pct ?? null} banda={v?.banda ?? null} loc={loc} /></td> : null,
                      ];
                    })}
                    <td style={td}>{fmt(j.dist_min, 0, loc)}</td>
                    <td style={td}>{fmt(j.valores.vmax?.valor, 1, loc)}</td>
                    <td style={{ ...td, color: (j.pct_vmax ?? 0) >= 90 ? cores.sucesso : cores.texto, fontWeight: (j.pct_vmax ?? 0) >= 90 ? 650 : 400 }}>
                      {j.pct_vmax !== null ? `${fmt(j.pct_vmax, 0, loc)} %` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p style={nota}>
            {tr("▲ ▼ = acima / abaixo do habitual do próprio jogador nos treinos {0} anteriores ({1} sessões), medido pela variação habitual dele.", [r.dia_md ?? "", r.n_habitual ?? 0])}{" "}
            {tr("% do recorde = velocidade máxima de hoje face ao recorde do jogador (sem picos isolados de GPS); ≥ 90 % conta como estímulo de velocidade.")}
          </p>
        </Cartao>

        {/* Exercícios */}
        <Cartao>
          <SecaoTitulo subtitulo={r.fonte_exercicios === "jogador"
            ? tr("Média por jogador em cada exercício. «vs época» compara a intensidade (m/min) de hoje com a média desse exercício nas outras sessões.")
            : r.fonte_exercicios === "equipa"
              ? tr("Da folha de exercícios da equipa (sem detalhe por jogador). Para o ter, importa o GPS com a coluna do exercício/período mapeada para «Período».")
              : undefined}>{tr("Exercícios")}</SecaoTitulo>
          {!ex || !ex.itens.length ? (
            <p style={{ fontSize: "0.84rem", color: cores.textoSuave, margin: 0 }}>
              {tr("Esta sessão não tem exercícios registados. Importa o export por exercício (drills/períodos) do GPS e mapeia a coluna do nome para «Período».")}{" "}
              <Link href="/upload" style={{ color: cores.acento }}>{tr("Importar GPS")}</Link>
            </p>
          ) : (
            <>
              <BarraExercicios itens={ex.itens} />
              <div style={{ overflowX: "auto", marginTop: espaco.md }}>
                <table style={{ ...tabela, minWidth: 720 }}>
                  <thead>
                    <tr>
                      <th style={thEsq}>{tr("Exercício")}</th><th style={th}>{tr("Min")}</th><th style={th}>{tr("Jog.")}</th>
                      <th style={th}>{tr("Distância")}</th><th style={th}>{tr("m/min")}</th><th style={th}>HSR</th><th style={th}>{tr("HSR/min")}</th>
                      <th style={th}>{tr("Acc")}</th><th style={th}>{tr("Dcc")}</th><th style={th}>{tr("vs época")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ex.itens.map((i) => (
                      <tr key={i.exercicio}>
                        <td style={{ ...tdEsq, fontWeight: 600, color: cores.textoForte }}>{i.exercicio}</td>
                        <td style={td}>{fmt(i.duracao_min, 0, loc)}</td>
                        <td style={td}>{fmt(i.n_jogadores, 0, loc)}</td>
                        <td style={td}>{fmt(i.distancia as number, 0, loc)}</td>
                        <td style={{ ...td, fontWeight: 650 }}>{fmt(i.distancia_min as number, 1, loc)}</td>
                        <td style={td}>{fmt(i.hsr as number, 0, loc)}</td>
                        <td style={td}>{fmt(i.hsr_min as number, 1, loc)}</td>
                        <td style={td}>{fmt(i.acc as number, 0, loc)}</td>
                        <td style={td}>{fmt(i.dcc as number, 0, loc)}</td>
                        <td style={td} title={i.n_epoca ? tr("Média de {0} sessão(ões): {1} m/min", [i.n_epoca, fmt(i.media_epoca_min ?? null, 1, loc)]) : tr("Primeira vez deste exercício")}>
                          <DeltaChip v={i.vs_epoca_pct ?? null} loc={loc} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {ex.por_jogador.length > 0 && <PorJogadorExercicio linhas={ex.por_jogador} exercicios={ex.itens.map((i) => i.exercicio)} loc={loc} tr={tr} />}
            </>
          )}
        </Cartao>
      </div>
    </div>
  );
}

function DeltaChip({ v, loc }: { v: number | null; loc: string }) {
  if (v === null) return <span style={{ color: cores.textoFraco }}>—</span>;
  const cor = Math.abs(v) < 10 ? cores.textoSuave : v > 0 ? cores.perigo : cores.info;
  return <span style={{ fontWeight: 650, fontSize: "0.78rem", color: cor, background: `color-mix(in srgb, ${cor} 12%, transparent)`, borderRadius: 6, padding: "2px 6px" }}>{fmtPct(v, loc)}</span>;
}

/** Barra com a duração de cada exercício (proporção da sessão). */
function BarraExercicios({ itens }: { itens: ItemEx[] }) {
  const paleta = [cores.distanciaTotal, cores.hsr, cores.acc, cores.velMax, cores.sprint, cores.dcc, cores.cargaInterna, cores.textoSuave];
  const total = itens.reduce((s, i) => s + (i.duracao_min ?? 0), 0) || 1;
  return (
    <div style={{ display: "flex", height: 12, borderRadius: 6, overflow: "hidden", border: `1px solid ${cores.borda}` }}>
      {itens.map((i, n) => (
        <div key={i.exercicio} title={`${i.exercicio} · ${i.duracao_min ?? "—"} min`} style={{ width: `${((i.duracao_min ?? 0) / total) * 100}%`, background: paleta[n % paleta.length] }} />
      ))}
    </div>
  );
}

/** Intensidade de cada jogador em cada exercício (m/min), face à média da equipa nesse exercício. */
function PorJogadorExercicio({ linhas, exercicios, loc, tr }: { linhas: LinhaEx[]; exercicios: string[]; loc: string; tr: Awaited<ReturnType<typeof obterTr>> }) {
  const jogadores = Array.from(new Set(linhas.map((l) => l.jogador))).sort();
  const mapa = new Map(linhas.map((l) => [`${l.jogador}|${l.exercicio}`, l]));
  return (
    <div style={{ marginTop: espaco.xl }}>
      <SecaoTitulo margem={espaco.sm} subtitulo={tr("m/min de cada jogador e a diferença para a média da equipa no mesmo exercício (vermelho = bem acima, azul = bem abaixo).")}>
        {tr("Intensidade por jogador")}
      </SecaoTitulo>
      <div style={{ overflowX: "auto" }}>
        <table style={{ ...tabela, minWidth: 160 + exercicios.length * 120 }}>
          <thead><tr><th style={thEsq}>{tr("Jogador")}</th>{exercicios.map((e) => <th key={e} style={{ ...th, whiteSpace: "normal", maxWidth: 140 }}>{e}</th>)}</tr></thead>
          <tbody>
            {jogadores.map((j) => (
              <tr key={j}>
                <td style={{ ...tdEsq, fontWeight: 600 }}><NomeJogador nome={j} /></td>
                {exercicios.map((e) => {
                  const l = mapa.get(`${j}|${e}`);
                  const v = l?.vs_equipa_pct ?? null;
                  const cor = v === null || Math.abs(v) < 10 ? cores.texto : v > 0 ? cores.perigo : cores.info;
                  return (
                    <td key={e} style={td}>
                      {l ? <><span style={{ fontWeight: 600 }}>{fmt(l.dist_min, 0, loc)}</span> <span style={{ fontSize: "0.72rem", color: cor }}>{fmtPct(v, loc)}</span></> : <span style={{ color: cores.textoFraco }}>—</span>}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
