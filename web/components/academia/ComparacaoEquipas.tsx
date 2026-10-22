"use client";

import { useEffect, useMemo, useState } from "react";
import { pedidoApi } from "@/lib/api-cliente";
import { cores, espaco, raio } from "@/lib/theme";
import { Cartao, Etiqueta, SecaoTitulo, Vazio, estiloBotao } from "@/components/ui/base";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { Ajuda } from "@/components/ui/Ajuda";
import { PageHeader } from "@/components/layout/PageHeader";
import { useTr } from "@/lib/i18n/cliente";
import type { Metrica } from "./tipos";

type Ref = { n: number; p25?: number; p50?: number; p75?: number; idade?: number; categoria?: string };
type ValorRef = { valor: number; data: string; idade: number | null; cat: string | null;
  p_idade?: number | null; p_mat?: number | null; ref_idade?: Ref; ref_mat?: Ref };
type Estat = { n: number; media: number; dp: number | null; mediana: number; min: number; max: number; valores: { nome: string; valor: number }[] };
interface Equipa {
  team_id: string; escalao: string; n_atletas: number; idade_media: number | null;
  estatisticas: Record<string, Record<string, Estat>>;
  maturacao: Record<string, Record<string, number>>;
}
interface Atleta { atleta_id: string; nome: string; idade: number | null; equipas: string[]; valores: Record<string, Record<string, ValorRef>> }
interface Comparacao {
  epoca: string; epocas: string[]; metricas: Metrica[]; categorias_mat: string[]; min_coorte: number;
  equipas: Equipa[]; atletas: Atleta[];
}

const MOMENTOS = [1, 2, 3, 4];
const COR_EQUIPA: Record<string, string> = { "Sub-15": "#3b82f6", "Sub-16": "#14b8a6", "Sub-17": "#f59e0b", "Sub-19": "#a855f7" };
const COR_MAT: Record<string, string> = {
  "Pré-púbere": "#3b82f6", "Início da puberdade": "#f59e0b", "Meio da puberdade": "#ef4444", "Fim da puberdade": "#22c55e",
};
const GRUPOS: { titulo: string; chaves: string[] }[] = [
  { titulo: "Velocidade", chaves: ["sprint_5m_s", "sprint_10m_s", "sprint_20m_s", "sprint_30m_s"] },
  { titulo: "Resistência", chaves: ["corrida_1km_s"] },
  { titulo: "Saltos", chaves: ["cmj_cm", "dj_altura_cm", "dj_contacto_ms", "rsi"] },
  { titulo: "Antropometria", chaves: ["altura_cm", "peso_kg"] },
];

export function fmtValor(v: number | null | undefined, m: Metrica, loc: string) {
  if (v == null) return "—";
  if (m.unidade === "s" && v >= 60) {
    const t = Math.round(v);
    return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`;
  }
  return v.toLocaleString(loc, { minimumFractionDigits: m.casas, maximumFractionDigits: m.casas });
}
const unid = (m: Metrica) => (m.chave === "corrida_1km_s" ? "m:ss" : m.unidade);
const rotuloMetrica = (m: Metrica, tr: (s: string) => string) => tr(m.label).replace(/^Drop jump — /, "DJ ");

/** Cor do percentil: verde ≥ P75, vermelho ≤ P25. */
export function corPercentil(p: number | null | undefined) {
  if (p == null) return cores.textoFraco;
  return p >= 75 ? cores.sucesso : p <= 25 ? cores.perigo : cores.textoSuave;
}

export function ComparacaoEquipas() {
  const tr = useTr();
  const [epoca, setEpoca] = useState<string | null>(null);
  const [dados, setDados] = useState<Comparacao | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [momento, setMomento] = useState<number | null>(null);
  const [metrica, setMetrica] = useState("sprint_10m_s");

  useEffect(() => {
    setErro(null);
    pedidoApi<Comparacao>(`/api/academia/comparacao${epoca ? `?epoca=${encodeURIComponent(epoca)}` : ""}`)
      .then((d) => {
        setDados(d);
        const comDados = MOMENTOS.filter((m) => d.equipas.some((e) => Object.values(e.estatisticas).some((s) => s[m])));
        setMomento(comDados.length ? comDados[comDados.length - 1] : 1);
      })
      .catch((e) => setErro(e.message));
  }, [epoca]);

  const porChave = useMemo(() => Object.fromEntries((dados?.metricas ?? []).map((m) => [m.chave, m])), [dados]);

  if (erro) return <div style={{ padding: espaco.xxl }}><Vazio>{erro}</Vazio></div>;
  if (!dados || momento == null) return <p style={{ padding: espaco.xxl, color: cores.textoSuave }}>{tr("A carregar…")}</p>;

  const k = String(momento);
  const m = porChave[metrica];
  const temDados = dados.equipas.some((e) => Object.values(e.estatisticas).some((s) => s[k]));

  return (
    <div>
      <PageHeader titulo={tr("Academia · Comparar equipas")} subtitulo={tr("Os escalões lado a lado nos mesmos testes, com o estado maturacional de cada um")} />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px`, maxWidth: 1300 }}>
        <div style={{ display: "flex", gap: espaco.sm, flexWrap: "wrap", alignItems: "center", marginBottom: espaco.lg }}>
          <select value={dados.epoca} onChange={(e) => setEpoca(e.target.value)} style={campo} aria-label={tr("Época")}>
            {dados.epocas.map((ep) => <option key={ep} value={ep}>{ep}</option>)}
          </select>
          <select value={momento} onChange={(e) => setMomento(Number(e.target.value))} style={campo} aria-label={tr("Momento")}>
            {MOMENTOS.map((mm) => <option key={mm} value={mm}>T{mm}</option>)}
          </select>
          <select value={metrica} onChange={(e) => setMetrica(e.target.value)} style={campo} aria-label={tr("Teste")}>
            {GRUPOS.map((g) => (
              <optgroup key={g.titulo} label={tr(g.titulo)}>
                {g.chaves.filter((c) => porChave[c]).map((c) => <option key={c} value={c}>{tr(porChave[c].label)}</option>)}
              </optgroup>
            ))}
          </select>
        </div>

        {dados.equipas.length === 0 ? <Vazio>{tr("Ainda não há equipas de escalão nesta época.")}</Vazio> : (
          <>
            <SecaoTitulo ajuda={tr("Média ± desvio-padrão (n atletas) no momento escolhido. A negrito o escalão com melhor média. Clica num teste para o ver nos gráficos.")}>
              {tr("Resumo por escalão — T{0}", [momento])}</SecaoTitulo>
            <TabelaResumo dados={dados} k={k} porChave={porChave} metrica={metrica} setMetrica={setMetrica} />
            {!temDados && <p style={nota}>{tr("Ainda não há testes registados em T")}{momento}.</p>}

            {m && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(380px, 1fr))", gap: espaco.lg, marginTop: espaco.xl }}>
                <GraficoDistribuicao dados={dados} k={k} m={m} />
                <GraficoProgressao dados={dados} m={m} />
              </div>
            )}

            <div style={{ marginTop: espaco.xxl }}><SecaoTitulo ajuda={tr("Khamis-Roche no momento escolhido (precisa de altura, peso, data de nascimento e altura dos pais). O método só se aplica até aos 17,5 anos — nos Sub-19 quase nunca há estado.")}>{tr("Estado maturacional por escalão")}</SecaoTitulo></div>
            <DistribuicaoMaturacao dados={dados} k={k} />

            {m && <BioBanding dados={dados} k={k} m={m} />}
          </>
        )}
      </div>
    </div>
  );
}

// ── Tabela: média ± dp de cada escalão em cada teste ────────────────────────
function TabelaResumo({ dados, k, porChave, metrica, setMetrica }: {
  dados: Comparacao; k: string; porChave: Record<string, Metrica>; metrica: string; setMetrica: (c: string) => void;
}) {
  const tr = useTr();
  return (
    <Cartao padding={0}>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem", minWidth: 640 }}>
          <thead>
            <tr>
              <th style={th}>{tr("Teste")}</th>
              {dados.equipas.map((e) => (
                <th key={e.team_id} style={{ ...th, textAlign: "right" }}>
                  <span style={{ color: COR_EQUIPA[e.escalao] ?? cores.textoForte }}>{tr(e.escalao)}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr style={{ borderTop: `1px solid ${cores.borda}` }}>
              <td style={{ ...td, color: cores.textoSuave }}>{tr("Atletas · idade média")}</td>
              {dados.equipas.map((e) => (
                <td key={e.team_id} style={{ ...td, textAlign: "right", color: cores.textoSuave }}>
                  {e.n_atletas} · {e.idade_media != null ? tr("{0} anos", [e.idade_media.toLocaleString(tr.loc)]) : "—"}
                </td>
              ))}
            </tr>
            {GRUPOS.map((g) => [
              <tr key={g.titulo}>
                <td colSpan={dados.equipas.length + 1} style={{ ...td, fontSize: "0.68rem", fontWeight: 700, color: cores.acento, letterSpacing: "0.06em", textTransform: "uppercase", paddingTop: 12 }}>{tr(g.titulo)}</td>
              </tr>,
              ...g.chaves.filter((c) => porChave[c]).map((c) => {
                const m = porChave[c];
                const medias = dados.equipas.map((e) => e.estatisticas[c]?.[k]?.media).filter((v): v is number => v != null);
                const melhor = m.maior_melhor == null || medias.length < 2 ? null : m.maior_melhor ? Math.max(...medias) : Math.min(...medias);
                const ativo = c === metrica;
                return (
                  <tr key={c} onClick={() => setMetrica(c)} style={{ borderTop: `1px solid ${cores.borda}`, cursor: "pointer", background: ativo ? cores.superficie : undefined }}>
                    <td style={{ ...td, color: cores.textoForte, fontWeight: ativo ? 700 : 400 }}>
                      {tr(m.label)}{unid(m) ? <span style={{ color: cores.textoFraco }}> ({unid(m)})</span> : null}
                    </td>
                    {dados.equipas.map((e) => {
                      const s = e.estatisticas[c]?.[k];
                      return (
                        <td key={e.team_id} style={{ ...td, textAlign: "right", fontVariantNumeric: "tabular-nums", fontWeight: s && s.media === melhor ? 700 : 400 }}>
                          {s ? <>
                            {fmtValor(s.media, m, tr.loc)}
                            {s.dp != null && <span style={{ color: cores.textoFraco }}> ± {fmtValor(s.dp, { ...m, unidade: m.unidade === "s" && s.dp >= 60 ? "s" : "" }, tr.loc)}</span>}
                            <span style={{ color: cores.textoFraco, fontSize: "0.7rem" }}> ({s.n})</span>
                          </> : <span style={{ color: cores.textoFraco }}>—</span>}
                        </td>
                      );
                    })}
                  </tr>
                );
              }),
            ])}
          </tbody>
        </table>
      </div>
    </Cartao>
  );
}

// ── Gráficos ────────────────────────────────────────────────────────────────
function GraficoDistribuicao({ dados, k, m }: { dados: Comparacao; k: string; m: Metrica }) {
  const tr = useTr();
  const series = dados.equipas.filter((e) => e.estatisticas[m.chave]?.[k]).map((e) => {
    const s = e.estatisticas[m.chave][k];
    return {
      type: "box", name: tr(e.escalao), y: s.valores.map((v) => v.valor), text: s.valores.map((v) => v.nome),
      boxpoints: "all", jitter: 0.4, pointpos: 0, marker: { color: COR_EQUIPA[e.escalao] ?? "#64748b", size: 6 },
      line: { color: COR_EQUIPA[e.escalao] ?? "#64748b" }, fillcolor: "rgba(0,0,0,0)",
      hovertemplate: `%{text}<br>%{y} ${m.unidade}<extra>${tr(e.escalao)}</extra>`,
    };
  });
  return (
    <Cartao>
      <div style={tituloGrafico}>{tr("{0} — distribuição por escalão (T{1})", [tr(m.label), k])}
        <Ajuda>{m.maior_melhor === false ? tr("Eixo invertido: mais acima = mais rápido. ") : ""}{tr("Cada ponto é um atleta; a caixa vai do P25 ao P75 com a mediana ao meio.")}</Ajuda></div>
      {series.length === 0 ? <Vazio>{tr("Sem dados neste momento.")}</Vazio> : (
        <PlotlyChart data={series as never} altura={320} titulo={tr(m.label)} layout={{
          showlegend: false, margin: { l: 50, r: 10, t: 10, b: 40 },
          yaxis: { title: { text: unid(m) }, autorange: m.maior_melhor === false ? "reversed" : true },
        } as never} />
      )}
    </Cartao>
  );
}

function GraficoProgressao({ dados, m }: { dados: Comparacao; m: Metrica }) {
  const tr = useTr();
  const series = dados.equipas.map((e) => {
    const pts = MOMENTOS.map((mm) => e.estatisticas[m.chave]?.[String(mm)]);
    return {
      type: "scatter", mode: "lines+markers", name: tr(e.escalao),
      x: MOMENTOS.map((mm) => `T${mm}`), y: pts.map((s) => s?.media ?? null),
      error_y: { type: "data", array: pts.map((s) => s?.dp ?? 0), visible: true, thickness: 1, width: 3 },
      line: { color: COR_EQUIPA[e.escalao] ?? "#64748b", width: 2 }, marker: { size: 7 }, connectgaps: true,
      hovertemplate: `%{x}: %{y} ${m.unidade}<extra>${tr(e.escalao)}</extra>`,
    };
  }).filter((s) => s.y.some((v) => v != null));
  return (
    <Cartao>
      <div style={tituloGrafico}>{tr("{0} — média por momento (T1–T4)", [tr(m.label)])}
        <Ajuda>{tr("Média ± desvio-padrão de cada escalão em cada momento da época.")}</Ajuda></div>
      {series.length === 0 ? <Vazio>{tr("Sem dados nesta época.")}</Vazio> : (
        <PlotlyChart data={series as never} altura={320} titulo={tr(m.label)} layout={{
          margin: { l: 50, r: 10, t: 10, b: 40 }, legend: { orientation: "h", y: -0.18 },
          yaxis: { title: { text: unid(m) }, autorange: m.maior_melhor === false ? "reversed" : true },
        } as never} />
      )}
    </Cartao>
  );
}

function DistribuicaoMaturacao({ dados, k }: { dados: Comparacao; k: string }) {
  const tr = useTr();
  return (
    <Cartao>
      <div style={{ display: "grid", gap: espaco.sm }}>
        {dados.equipas.map((e) => {
          const cont = e.maturacao[k] ?? {};
          const total = Object.values(cont).reduce((a, b) => a + b, 0);
          return (
            <div key={e.team_id} style={{ display: "grid", gridTemplateColumns: "70px 1fr 90px", gap: espaco.sm, alignItems: "center" }}>
              <span style={{ fontWeight: 700, color: COR_EQUIPA[e.escalao] ?? cores.textoForte, fontSize: "0.84rem" }}>{tr(e.escalao)}</span>
              <div style={{ display: "flex", height: 22, borderRadius: raio.sm, overflow: "hidden", background: cores.superficie }}>
                {total > 0 && dados.categorias_mat.map((c) => cont[c] ? (
                  <div key={c} title={`${tr(c)}: ${cont[c]}`} style={{ width: `${(cont[c] / total) * 100}%`, background: COR_MAT[c], color: "#fff", fontSize: "0.7rem", fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    {cont[c]}
                  </div>
                ) : null)}
              </div>
              <span style={{ fontSize: "0.74rem", color: cores.textoSuave, textAlign: "right" }}>
                {total ? tr("{0} de {1} atletas", [total, e.n_atletas]) : tr("sem dados")}
              </span>
            </div>
          );
        })}
      </div>
      <div style={{ display: "flex", gap: espaco.md, flexWrap: "wrap", marginTop: espaco.md }}>
        {dados.categorias_mat.map((c) => <Etiqueta key={c} cor={COR_MAT[c]}>{tr(c)}</Etiqueta>)}
      </div>
    </Cartao>
  );
}

// ── Bio-banding: cada atleta face aos colegas no mesmo estado maturacional ──
const N_BIO = 10;

function BioBanding({ dados, k, m }: { dados: Comparacao; k: string; m: Metrica }) {
  const tr = useTr();
  const [abertos, setAbertos] = useState<Record<string, boolean>>({});
  const antropometria = m.maior_melhor == null;
  const grupos = dados.categorias_mat.map((cat) => {
    const linhas = dados.atletas
      .map((a) => ({ a, v: a.valores[m.chave]?.[k] }))
      .filter((x): x is { a: Atleta; v: ValorRef } => !!x.v && x.v.cat === cat)
      .sort((x, y) => (m.maior_melhor === false ? x.v.valor - y.v.valor : y.v.valor - x.v.valor));
    return { cat, linhas };
  }).filter((g) => g.linhas.length);
  const semEstado = dados.atletas.filter((a) => a.valores[m.chave]?.[k] && !a.valores[m.chave][k].cat).length;

  return (
    <>
      <div style={{ marginTop: espaco.xxl }}><SecaoTitulo
        ajuda={tr("Cada atleta comparado com os colegas da academia no mesmo estado maturacional, seja qual for o escalão. Assim um jogador mais adiantado não parece melhor só por estar mais maduro, e um mais atrasado não fica escondido. P mat. = percentil dentro do estado; P idade = percentil face aos da mesma idade.")}
      >{tr("Por estado maturacional (bio-banding) — {0}, T{1}", [tr(m.label), k])}</SecaoTitulo></div>
      {antropometria ? <Vazio>{tr("Escolhe um teste de desempenho (velocidade, resistência ou saltos) para ver o bio-banding.")}</Vazio>
        : grupos.length === 0 ? <Vazio>{tr("Ainda não há atletas com estado maturacional e este teste no mesmo momento.")}</Vazio> : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(380px, 1fr))", gap: espaco.lg }}>
            {grupos.map(({ cat, linhas }) => {
              const r = linhas.find((l) => l.v.ref_mat)?.v.ref_mat;
              const tudo = abertos[cat];
              const visiveis = tudo ? linhas : linhas.slice(0, N_BIO);
              return (
                <Cartao key={cat} padding={0}>
                  <div style={{ padding: `${espaco.sm}px ${espaco.md}px`, borderBottom: `1px solid ${cores.borda}`, display: "flex", justifyContent: "space-between", alignItems: "center", gap: espaco.sm }}>
                    <Etiqueta cor={COR_MAT[cat]}>{tr(cat)}</Etiqueta>
                    <span style={{ fontSize: "0.72rem", color: cores.textoSuave }}>
                      {r?.p50 != null ? tr("academia: mediana {0} · P25–P75 {1}–{2} (n = {3})", [fmtValor(r.p50, m, tr.loc), fmtValor(r.p25, m, tr.loc), fmtValor(r.p75, m, tr.loc), r.n])
                        : tr("{0} atleta(s) — precisa de {1} para percentis", [r?.n ?? linhas.length, dados.min_coorte])}
                    </span>
                  </div>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
                    <thead>
                      <tr>
                        <th style={th}>{tr("Atleta")}</th>
                        <th style={th}>{tr("Escalão")}</th>
                        <th style={{ ...th, textAlign: "right" }}>{tr("Idade")}</th>
                        <th style={{ ...th, textAlign: "right" }}>{rotuloMetrica(m, tr)}{unid(m) ? ` (${unid(m)})` : ""}</th>
                        <th style={{ ...th, textAlign: "right" }}>{tr("P mat.")}</th>
                        <th style={{ ...th, textAlign: "right" }}>{tr("P idade")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {visiveis.map(({ a, v }) => (
                        <tr key={a.atleta_id} style={{ borderTop: `1px solid ${cores.borda}` }}>
                          <td style={{ ...td, color: cores.textoForte, fontWeight: 600 }}>{a.nome}</td>
                          <td style={{ ...td, color: cores.textoSuave }}>{a.equipas.map((e) => tr(e)).join(", ")}</td>
                          <td style={{ ...td, textAlign: "right", color: cores.textoSuave }}>{v.idade != null ? v.idade.toLocaleString(tr.loc, { maximumFractionDigits: 1 }) : "—"}</td>
                          <td style={{ ...td, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{fmtValor(v.valor, m, tr.loc)}</td>
                          <td style={{ ...td, textAlign: "right", fontWeight: 700, color: corPercentil(v.p_mat) }}>{v.p_mat != null ? `P${v.p_mat}` : "—"}</td>
                          <td style={{ ...td, textAlign: "right", color: corPercentil(v.p_idade) }}>{v.p_idade != null ? `P${v.p_idade}` : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {linhas.length > N_BIO && (
                    <div style={{ borderTop: `1px solid ${cores.borda}`, padding: `6px ${espaco.md}px` }}>
                      <button onClick={() => setAbertos({ ...abertos, [cat]: !tudo })} style={{ ...estiloBotao.ligacao, fontSize: "0.78rem" }}>
                        {tudo ? tr("Mostrar menos") : tr("Ver todos ({0})", [linhas.length])}</button>
                    </div>
                  )}
                </Cartao>
              );
            })}
          </div>
        )}
      {semEstado > 0 && !antropometria && (
        <p style={nota}>{tr("{0} atleta(s) com este teste mas sem estado maturacional nesse momento (falta altura, peso, data de nascimento ou altura dos pais, ou têm mais de 17,5 anos).", [semEstado])}</p>
      )}
    </>
  );
}

const campo: React.CSSProperties = { background: cores.bgCartao, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: cores.textoForte, fontSize: "0.82rem", padding: "5px 8px", height: 32 };
const th: React.CSSProperties = { padding: `8px ${espaco.sm}px`, fontSize: "0.66rem", fontWeight: 600, color: cores.textoSuave, letterSpacing: "0.02em", textAlign: "left", whiteSpace: "nowrap" };
const td: React.CSSProperties = { padding: `6px ${espaco.sm}px`, color: cores.texto };
const nota: React.CSSProperties = { fontSize: "0.72rem", color: cores.textoSuave, lineHeight: 1.5, marginTop: espaco.sm };
const tituloGrafico: React.CSSProperties = { fontSize: "0.86rem", fontWeight: 700, color: cores.textoForte, marginBottom: espaco.sm, display: "flex", alignItems: "center", gap: 7 };
