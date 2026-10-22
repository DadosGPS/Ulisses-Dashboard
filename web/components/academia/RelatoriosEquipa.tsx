"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { pedidoApi } from "@/lib/api-cliente";
import { cores, espaco, raio } from "@/lib/theme";
import { Cartao, Etiqueta, Vazio, estiloBotao } from "@/components/ui/base";
import type { Metrica } from "./tipos";
import { NavEquipa } from "./NavEquipa";
import { PageHeader } from "@/components/layout/PageHeader";
import { useTr } from "@/lib/i18n/cliente";
import { corPercentil } from "./ComparacaoEquipas";

type Pctl = "nenhum" | "idade" | "mat";

type Ref = { n: number; p25?: number; p50?: number; p75?: number; idade?: number; categoria?: string };
type Valor = { valor: number; data: string; idade?: number | null; cat?: string | null; p_idade?: number | null; p_mat?: number | null; ref_idade?: Ref; ref_mat?: Ref };
type Mat = { estatura_prevista_cm: number; pct_estatura_adulta: number; crescimento_restante_cm: number; categoria: string; idade: number };
interface AtletaRel {
  atleta_id: string;
  nome: string;
  posicao: string | null;
  data_nascimento: string | null;
  idade: number | null;
  valores: Record<string, Record<string, Valor>>;
  maturacao: Record<string, Mat>;
  jogos?: { convocado: number; utilizado: number; titular: number; minutos: number; golos: number; assistencias: number;
    por_contexto: Record<string, number> } | null;
}
interface Relatorio {
  team_id: string;
  rotulo: string;
  epoca: string | null;
  metricas: Metrica[];
  momentos: Record<string, { de: string; ate: string }>;
  atletas: AtletaRel[];
  medias: Record<string, Record<string, number>>;
  min_coorte?: number;
}

const MOMENTOS = [1, 2, 3, 4];
const COR_MAT: Record<string, string> = {
  "Pré-púbere": "#3b82f6", "Início da puberdade": "#f59e0b", "Meio da puberdade": "#ef4444", "Fim da puberdade": "#22c55e",
};
const GRUPOS: { titulo: string; chaves: string[] }[] = [
  { titulo: "Velocidade", chaves: ["sprint_5m_s", "sprint_10m_s", "sprint_20m_s", "sprint_30m_s"] },
  { titulo: "Resistência", chaves: ["corrida_1km_s"] },
  { titulo: "Saltos", chaves: ["cmj_cm", "dj_altura_cm", "dj_contacto_ms", "rsi"] },
  { titulo: "Antropometria", chaves: ["altura_cm", "peso_kg"] },
];

function fmt(v: number | null | undefined, m: Metrica, loc: string) {
  if (v == null) return "—";
  if (m.unidade === "s" && v >= 60) {
    const t = Math.round(v);
    return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`;
  }
  return v.toLocaleString(loc, { minimumFractionDigits: m.casas, maximumFractionDigits: m.casas });
}
const dataPt = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;
const unid = (m: Metrica) => (m.chave === "corrida_1km_s" ? "m:ss" : m.unidade);

/** Melhoria (em %) de a → b: positivo = melhor, tenha a métrica "maior é melhor" ou não. */
function melhoriaPct(a: number, b: number, m: Metrica) {
  if (m.maior_melhor == null || !a) return null;
  return ((m.maior_melhor ? b - a : a - b) / a) * 100;
}

function imprimir() {
  const raiz = document.documentElement;
  const tema = raiz.getAttribute("data-theme");
  raiz.setAttribute("data-theme", "light");
  setTimeout(() => {
    window.print();
    if (tema) raiz.setAttribute("data-theme", tema);
    else raiz.removeAttribute("data-theme");
  }, 50);
}

export function RelatoriosEquipa({ teamId }: { teamId: string }) {
  const tr = useTr();
  const [dados, setDados] = useState<Relatorio | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [tipo, setTipo] = useState<"teste" | "individual">("teste");
  const [momento, setMomento] = useState(1);
  const [atleta, setAtleta] = useState("todos");
  const [pctl, setPctl] = useState<Pctl>("idade");

  useEffect(() => {
    pedidoApi<Relatorio>(`/api/academia/equipas/${teamId}/relatorio`)
      .then((d) => {
        setDados(d);
        const ms = Object.keys(d.momentos).map(Number);
        if (ms.length) setMomento(Math.max(...ms));
      })
      .catch((e) => setErro(e.message));
  }, [teamId]);

  if (erro) return <div style={{ padding: espaco.xxl }}><Vazio>{erro}</Vazio></div>;
  if (!dados) return <p style={{ padding: espaco.xxl, color: cores.textoSuave }}>{tr("A carregar…")}</p>;

  const porChave = Object.fromEntries(dados.metricas.map((m) => [m.chave, m]));
  const individuais = atleta === "todos" ? dados.atletas : dados.atletas.filter((a) => a.atleta_id === atleta);

  return (
    <div>
    <div data-no-print>
      <PageHeader titulo={tr("Academia · {0}", [dados.rotulo])} subtitulo={tr("Relatórios de avaliação da época (T1–T4)")} />
      <NavEquipa teamId={teamId} />
    </div>
    <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px`, maxWidth: 1300 }}>
      <div data-no-print style={{ display: "flex", gap: espaco.sm, flexWrap: "wrap", alignItems: "center", marginBottom: espaco.lg }}>
        <div role="tablist" style={{ display: "flex", gap: 4 }}>
          <button role="tab" aria-selected={tipo === "teste"} onClick={() => setTipo("teste")} style={tipo === "teste" ? estiloBotao.primario : estiloBotao.secundario}>{tr("Relatório do teste")}</button>
          <button role="tab" aria-selected={tipo === "individual"} onClick={() => setTipo("individual")} style={tipo === "individual" ? estiloBotao.primario : estiloBotao.secundario}>{tr("Relatório individual (época)")}</button>
        </div>
        {tipo === "teste" ? (
          <select value={momento} onChange={(e) => setMomento(Number(e.target.value))} style={campo} aria-label={tr("Momento")}>
            {MOMENTOS.map((m) => <option key={m} value={m}>T{m}{dados.momentos[m] ? ` · ${dataPt(dados.momentos[m].de)}${dados.momentos[m].ate !== dados.momentos[m].de ? ` – ${dataPt(dados.momentos[m].ate)}` : ""}` : tr(" · sem testes")}</option>)}
          </select>
        ) : null}
        {tipo === "teste" && (
          <select value={pctl} onChange={(e) => setPctl(e.target.value as Pctl)} style={campo} aria-label={tr("Percentis")}>
            <option value="nenhum">{tr("Sem percentis")}</option>
            <option value="idade">{tr("Percentil por idade")}</option>
            <option value="mat">{tr("Percentil por estado maturacional")}</option>
          </select>
        )}
        {tipo === "individual" && (
          <select value={atleta} onChange={(e) => setAtleta(e.target.value)} style={campo} aria-label={tr("Atleta")}>
            <option value="todos">{tr("Todos os atletas (um por página)")}</option>
            {dados.atletas.map((a) => <option key={a.atleta_id} value={a.atleta_id}>{a.nome}</option>)}
          </select>
        )}
        <button style={{ ...estiloBotao.primario, marginLeft: "auto" }} onClick={imprimir}>{tr("Imprimir / guardar PDF")}</button>
      </div>

      {dados.atletas.length === 0 ? <Vazio>{tr("Esta equipa ainda não tem jogadores.")}</Vazio>
        : tipo === "teste"
          ? <RelatorioTeste dados={dados} momento={momento} porChave={porChave} pctl={pctl} />
          : individuais.map((a) => <RelatorioIndividual key={a.atleta_id} dados={dados} a={a} porChave={porChave} />)}
    </div>
    </div>
  );
}

// ── Relatório do teste: todos os atletas num momento ─────────────────────────
function RelatorioTeste({ dados, momento, porChave, pctl }: { dados: Relatorio; momento: number; porChave: Record<string, Metrica>; pctl: Pctl }) {
  const tr = useTr();
  const k = String(momento);
  const ant = String(momento - 1);
  const chaves = GRUPOS.flatMap((g) => g.chaves).filter((c) => porChave[c]);
  const avaliados = dados.atletas.filter((a) => chaves.some((c) => a.valores[c]?.[k]));
  const periodo = dados.momentos[k];

  // Terços por coluna (verde = melhor terço, vermelho = pior), só em métricas de desempenho.
  const tercos = useMemo(() => {
    const out: Record<string, { bom: number; mau: number; melhor: number } | null> = {};
    for (const c of chaves) {
      const m = porChave[c];
      const vs = dados.atletas.map((a) => a.valores[c]?.[k]?.valor).filter((v): v is number => v != null).sort((x, y) => x - y);
      if (m.maior_melhor == null || vs.length < 3) { out[c] = null; continue; }
      const q1 = vs[Math.floor(vs.length / 3)], q2 = vs[Math.floor((2 * vs.length) / 3)];
      out[c] = m.maior_melhor ? { bom: q2, mau: q1, melhor: vs[vs.length - 1] } : { bom: q1, mau: q2, melhor: vs[0] };
    }
    return out;
  }, [dados, k, chaves, porChave]);

  function corCelula(c: string, v: number) {
    const t = tercos[c];
    const m = porChave[c];
    if (!t) return undefined;
    const bom = m.maior_melhor ? v >= t.bom : v <= t.bom;
    const mau = m.maior_melhor ? v <= t.mau : v >= t.mau;
    return bom ? "rgba(34,197,94,0.14)" : mau ? "rgba(239,68,68,0.12)" : undefined;
  }

  return (
    <section className="pagina paisagem">
      <CabecalhoRelatorio
        titulo={tr("Relatório de avaliação · T{0}", [momento])}
        sub={tr("{0}{1} · {2} de {3} atletas avaliados", [dados.rotulo, periodo ? ` · ${dataPt(periodo.de)}${periodo.ate !== periodo.de ? ` – ${dataPt(periodo.ate)}` : ""}` : "", avaliados.length, dados.atletas.length])}
      />
      {avaliados.length === 0 ? <Vazio>{tr("Ainda não há testes registados em T")}{momento}.</Vazio> : (
        <Cartao padding={0}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 980, fontSize: "0.8rem" }}>
              <thead>
                <tr>
                  <th style={th} rowSpan={2}>{tr("Atleta")}</th>
                  <th style={{ ...th, textAlign: "right" }} rowSpan={2}>{tr("Idade")}</th>
                  {GRUPOS.map((g) => {
                    const n = g.chaves.filter((c) => porChave[c]).length + (g.titulo === "Antropometria" ? 2 : 0);
                    return <th key={g.titulo} colSpan={n} style={{ ...th, textAlign: "center", borderBottom: `1px solid ${cores.borda}` }}>{tr(g.titulo)}{g.titulo === "Antropometria" ? tr(" e maturação") : ""}</th>;
                  })}
                </tr>
                <tr>
                  {chaves.map((c) => <th key={c} style={{ ...th, textAlign: "right" }}>{tr(porChave[c].label).replace(/^Drop jump — /, "DJ ")}{unid(porChave[c]) ? ` (${unid(porChave[c])})` : ""}</th>)}
                  <th style={{ ...th, textAlign: "right" }}>{tr("%PAH")}</th>
                  <th style={th}>{tr("Estado")}</th>
                </tr>
              </thead>
              <tbody>
                {dados.atletas.map((a) => {
                  const mat = a.maturacao[k];
                  return (
                    <tr key={a.atleta_id} style={{ borderTop: `1px solid ${cores.borda}` }}>
                      <td style={{ ...td, fontWeight: 600, color: cores.textoForte, whiteSpace: "nowrap" }}>{a.nome}</td>
                      <td style={{ ...td, textAlign: "right", color: cores.textoSuave }}>{a.idade != null ? a.idade.toLocaleString(tr.loc, { maximumFractionDigits: 1 }) : "—"}</td>
                      {chaves.map((c) => {
                        const reg = a.valores[c]?.[k];
                        const v = reg?.valor;
                        const pv = pctl === "idade" ? reg?.p_idade : pctl === "mat" ? reg?.p_mat : undefined;
                        const r = pctl === "idade" ? reg?.ref_idade : pctl === "mat" ? reg?.ref_mat : undefined;
                        const p = a.valores[c]?.[ant]?.valor;
                        const m = porChave[c];
                        const mel = v != null && p != null ? melhoriaPct(p, v, m) : null;
                        return (
                          <td key={c} title={r?.p50 != null ? tr("Academia ({0}): mediana {1} · P25–P75 {2}–{3} (n = {4})", [pctl === "idade" ? tr("{0} anos", [r.idade ?? "?"]) : tr(r.categoria ?? ""), fmt(r.p50, m, tr.loc), fmt(r.p25, m, tr.loc), fmt(r.p75, m, tr.loc), r.n]) : undefined}
                            style={{ ...td, textAlign: "right", fontVariantNumeric: "tabular-nums", background: v != null ? corCelula(c, v) : undefined, fontWeight: v != null && tercos[c]?.melhor === v ? 700 : 400 }}>
                            {fmt(v, m, tr.loc)}
                            {mel != null && Math.abs(mel) >= 0.5 && <span style={{ fontSize: "0.66rem", color: mel > 0 ? cores.sucesso : cores.perigo }}> {mel > 0 ? "▲" : "▼"}</span>}
                            {pctl !== "nenhum" && v != null && (
                              <div style={{ fontSize: "0.64rem", fontWeight: 600, color: corPercentil(pv) }}>{pv != null ? `P${pv}` : "·"}</div>
                            )}
                          </td>
                        );
                      })}
                      <td style={{ ...td, textAlign: "right" }}>{mat ? `${mat.pct_estatura_adulta.toLocaleString(tr.loc)} %` : "—"}</td>
                      <td style={td}>{mat ? <Etiqueta cor={COR_MAT[mat.categoria] ?? cores.textoSuave}>{tr(mat.categoria)}</Etiqueta> : "—"}</td>
                    </tr>
                  );
                })}
                <tr style={{ borderTop: `2px solid ${cores.bordaForte}`, background: cores.superficie }}>
                  <td style={{ ...td, fontWeight: 700 }} colSpan={2}>{tr("Média da equipa")}</td>
                  {chaves.map((c) => <td key={c} style={{ ...td, textAlign: "right", fontWeight: 700 }}>{fmt(dados.medias[c]?.[k], porChave[c], tr.loc)}</td>)}
                  <td colSpan={2} style={td} />
                </tr>
                <tr style={{ background: cores.superficie }}>
                  <td style={{ ...td, fontWeight: 700 }} colSpan={2}>{tr("Melhor")}</td>
                  {chaves.map((c) => <td key={c} style={{ ...td, textAlign: "right" }}>{fmt(tercos[c]?.melhor, porChave[c], tr.loc)}</td>)}
                  <td colSpan={2} style={td} />
                </tr>
              </tbody>
            </table>
          </div>
        </Cartao>
      )}
      <p style={nota}>
        {tr("Verde = terço melhor da equipa neste teste; vermelho = terço pior; a negrito o melhor valor. ▲/▼ = melhorou/piorou face a T")}{momento - 1 || "—"}{tr(". %PAH = % da estatura adulta prevista (Khamis-Roche); estado segundo Cumming et al. (2017).")}
        {pctl !== "nenhum" && <>{" "}{pctl === "idade"
          ? tr("P = percentil face a todos os atletas da academia com a mesma idade (anos inteiros), em todas as épocas; alto = melhor (na antropometria, alto = maior).")
          : tr("P = percentil face aos atletas da academia no mesmo estado maturacional, seja qual for a idade; alto = melhor.")}
          {" "}{tr("Sem percentil (·) quando o grupo tem menos de {0} atletas. Passa o rato num valor para ver a referência.", [dados.min_coorte ?? 5])}</>}</p>
    </section>
  );
}

// ── Relatório individual: progressão T1 → T4 ─────────────────────────────────
function RelatorioIndividual({ dados, a, porChave }: { dados: Relatorio; a: AtletaRel; porChave: Record<string, Metrica> }) {
  const tr = useTr();
  const linhas = GRUPOS.flatMap((g) => g.chaves.filter((c) => porChave[c]).map((c) => ({ grupo: g.titulo, c, m: porChave[c] })));
  const comDados = linhas.filter((l) => Object.keys(a.valores[l.c] ?? {}).length);
  const evolucoes = comDados.map((l) => {
    const ms = Object.keys(a.valores[l.c]).map(Number).sort();
    const prim = a.valores[l.c][String(ms[0])].valor, ult = a.valores[l.c][String(ms[ms.length - 1])].valor;
    return { ...l, prim, ult, mPrim: ms[0], mUlt: ms[ms.length - 1], mel: ms.length > 1 ? melhoriaPct(prim, ult, l.m) : null };
  });
  const comparaveis = evolucoes.filter((e) => e.mel != null);
  const melhorou = comparaveis.filter((e) => (e.mel ?? 0) > 0.5);
  const maior = [...comparaveis].sort((x, y) => (y.mel ?? 0) - (x.mel ?? 0))[0];
  const matMs = Object.keys(a.maturacao).map(Number).sort();
  const matUlt = matMs.length ? a.maturacao[String(matMs[matMs.length - 1])] : null;

  return (
    <section className="pagina" style={{ marginBottom: espaco.xxl }}>
      <CabecalhoRelatorio
        titulo={`${a.nome}`}
        sub={[tr("Relatório individual · {0}", [dados.rotulo]), a.data_nascimento ? tr("nascido a {0}", [dataPt(a.data_nascimento)]) : null,
          a.idade != null ? tr("{0} anos", [Math.floor(a.idade)]) : null, a.posicao].filter(Boolean).join(" · ")}
      />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: espaco.md, marginBottom: espaco.lg }}>
        <Resumo titulo={tr("Progressão")} valor={comparaveis.length ? tr("{0} de {1}", [melhorou.length, comparaveis.length]) : "—"} sub={tr("testes em que melhorou")} />
        <Resumo titulo={tr("Maior progressão")} valor={maior && (maior.mel ?? 0) > 0.5 ? `${tr(maior.m.label).replace(/^Drop jump — /, "DJ ")}` : "—"}
          sub={maior && (maior.mel ?? 0) > 0.5 ? `+${maior.mel!.toLocaleString(tr.loc, { maximumFractionDigits: 1 })} % (T${maior.mPrim} → T${maior.mUlt})` : tr("precisa de 2 momentos")} />
        <Resumo titulo={tr("Maturação")} valor={matUlt ? tr("{0} %PAH", [matUlt.pct_estatura_adulta.toLocaleString(tr.loc)]) : "—"}
          sub={matUlt ? tr("{0} · PAH {1} cm", [tr(matUlt.categoria), matUlt.estatura_prevista_cm.toLocaleString(tr.loc)]) : tr("falta altura, peso ou pais")} cor={matUlt ? COR_MAT[matUlt.categoria] : undefined} />
      </div>

      {a.jogos && (
        <div style={{ border: `1px solid ${cores.borda}`, borderRadius: raio.sm, padding: `${espaco.sm}px ${espaco.md}px`, marginBottom: espaco.lg }}>
          <div style={{ fontSize: "0.68rem", fontWeight: 700, color: cores.acento, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 6 }}>{tr("Jogos da época")}</div>
          <div style={{ display: "flex", gap: espaco.xl, flexWrap: "wrap", fontSize: "0.84rem", color: cores.texto }}>
            <span><strong style={{ color: cores.textoForte }}>{a.jogos.minutos.toLocaleString(tr.loc)}</strong> {tr("minutos")}</span>
            <span><strong style={{ color: cores.textoForte }}>{a.jogos.utilizado}</strong> {tr("jogos (")}{a.jogos.titular} {tr("titular) ·")}{" "}{a.jogos.convocado} {tr("convocatórias")}</span>
            <span><strong style={{ color: cores.textoForte }}>{a.jogos.golos}</strong> {tr("golos ·")}{" "}<strong style={{ color: cores.textoForte }}>{a.jogos.assistencias}</strong> {tr("assistências")}</span>
            <span style={{ color: cores.textoSuave }}>
              {Object.entries(a.jogos.por_contexto).filter(([, m]) => m > 0).map(([c, m]) => `${tr(c)} ${m}′`).join(" · ") || tr("sem minutos")}
            </span>
          </div>
        </div>
      )}

      <Cartao padding={0}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem", tableLayout: "fixed" }}>
          <colgroup>
            <col style={{ width: "22%" }} />
            {MOMENTOS.map((m) => <col key={m} style={{ width: "9%" }} />)}
            <col style={{ width: "10%" }} /><col style={{ width: "10%" }} /><col style={{ width: "7%" }} /><col style={{ width: "7%" }} /><col style={{ width: "8%" }} />
          </colgroup>
          <thead>
            <tr>
              <th style={th}>{tr("Teste")}</th>
              {MOMENTOS.map((m) => <th key={m} style={{ ...th, textAlign: "right" }}>T{m}</th>)}
              <th style={{ ...th, textAlign: "right" }}>{tr("Evolução")}</th>
              <th style={{ ...th, textAlign: "right" }}>{tr("vs média equipa")}</th>
              <th style={{ ...th, textAlign: "right" }} title={tr("Percentil do último valor face aos atletas da academia com a mesma idade")}>{tr("P idade")}</th>
              <th style={{ ...th, textAlign: "right" }} title={tr("Percentil do último valor face aos atletas da academia no mesmo estado maturacional")}>{tr("P mat.")}</th>
              <th style={{ ...th, textAlign: "center" }}>{tr("Tendência")}</th>
            </tr>
          </thead>
          <tbody>
            {GRUPOS.map((g) => {
              const doGrupo = linhas.filter((l) => l.grupo === g.titulo);
              return [
                <tr key={g.titulo}><td colSpan={10} style={{ ...td, fontSize: "0.68rem", fontWeight: 700, color: cores.acento, letterSpacing: "0.06em", textTransform: "uppercase", paddingTop: 12 }}>{tr(g.titulo)}</td></tr>,
                ...doGrupo.map(({ c, m }) => {
                  const vals = a.valores[c] ?? {};
                  const ev = evolucoes.find((e) => e.c === c);
                  const ultM = ev ? String(ev.mUlt) : null;
                  const media = ultM ? dados.medias[c]?.[ultM] : null;
                  const vsMedia = ev && media ? melhoriaPct(media, ev.ult, m) : null;
                  const regUlt = ultM ? vals[ultM] : undefined;
                  const dicaRef = (r: Ref | undefined, rot: string) => r?.p50 != null
                    ? tr("Academia ({0}): mediana {1} · P25–P75 {2}–{3} (n = {4})", [rot, fmt(r.p50, m, tr.loc), fmt(r.p25, m, tr.loc), fmt(r.p75, m, tr.loc), r.n])
                    : r ? tr("Só {0} atleta(s) neste grupo — precisa de {1}", [r.n, dados.min_coorte ?? 5]) : undefined;
                  return (
                    <tr key={c} style={{ borderTop: `1px solid ${cores.borda}` }}>
                      <td style={{ ...td, color: cores.textoForte }}>{tr(m.label)}{unid(m) ? <span style={{ color: cores.textoFraco }}> ({unid(m)})</span> : null}</td>
                      {MOMENTOS.map((mm) => <td key={mm} style={{ ...td, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{fmt(vals[String(mm)]?.valor, m, tr.loc)}</td>)}
                      <td style={{ ...td, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                        {ev && ev.mPrim !== ev.mUlt ? (
                          m.maior_melhor == null
                            ? `${ev.ult - ev.prim > 0 ? "+" : ""}${(ev.ult - ev.prim).toLocaleString(tr.loc, { maximumFractionDigits: m.casas })} ${m.unidade}`
                            : <span style={{ color: (ev.mel ?? 0) > 0.5 ? cores.sucesso : (ev.mel ?? 0) < -0.5 ? cores.perigo : cores.textoSuave, fontWeight: 600 }}>
                              {(ev.mel ?? 0) > 0 ? "+" : ""}{(ev.mel ?? 0).toLocaleString(tr.loc, { maximumFractionDigits: 1 })} %
                            </span>
                        ) : "—"}
                      </td>
                      <td style={{ ...td, textAlign: "right", color: vsMedia == null ? cores.textoFraco : vsMedia >= 0 ? cores.sucesso : cores.perigo }}>
                        {vsMedia == null ? "—" : `${vsMedia >= 0 ? "+" : ""}${vsMedia.toLocaleString(tr.loc, { maximumFractionDigits: 1 })} %`}
                      </td>
                      <td title={dicaRef(regUlt?.ref_idade, tr("{0} anos", [regUlt?.ref_idade?.idade ?? "?"]))} style={{ ...td, textAlign: "right", fontWeight: 600, color: corPercentil(regUlt?.p_idade) }}>{regUlt?.p_idade != null ? `P${regUlt.p_idade}` : "—"}</td>
                      <td title={dicaRef(regUlt?.ref_mat, tr(regUlt?.ref_mat?.categoria ?? ""))} style={{ ...td, textAlign: "right", fontWeight: 600, color: corPercentil(regUlt?.p_mat) }}>{regUlt?.p_mat != null ? `P${regUlt.p_mat}` : "—"}</td>
                      <td style={{ ...td, textAlign: "center" }}><Sparkline vals={MOMENTOS.map((mm) => vals[String(mm)]?.valor ?? null)} inverter={m.maior_melhor === false} neutro={m.maior_melhor == null} /></td>
                    </tr>
                  );
                }),
              ];
            })}
            <tr><td colSpan={10} style={{ ...td, fontSize: "0.68rem", fontWeight: 700, color: cores.acento, letterSpacing: "0.06em", textTransform: "uppercase", paddingTop: 12 }}>{tr("Maturação (Khamis-Roche)")}</td></tr>
            {([["%PAH", (x: Mat) => `${x.pct_estatura_adulta.toLocaleString(tr.loc)} %`], ["PAH (cm)", (x: Mat) => x.estatura_prevista_cm.toLocaleString(tr.loc)], ["Estado", (x: Mat) => tr(x.categoria)]] as [string, (x: Mat) => string][]).map(([r, f]) => (
              <tr key={r} style={{ borderTop: `1px solid ${cores.borda}` }}>
                <td style={{ ...td, color: cores.textoForte }}>{tr(r)}</td>
                {MOMENTOS.map((mm) => <td key={mm} style={{ ...td, textAlign: "right", fontSize: r === "Estado" ? "0.72rem" : undefined }}>{a.maturacao[String(mm)] ? f(a.maturacao[String(mm)]) : "—"}</td>)}
                <td colSpan={5} style={td} />
              </tr>
            ))}
          </tbody>
        </table>
      </Cartao>
      <p style={nota}>
        {tr("Evolução = do primeiro ao último momento com registo; positivo (verde) = melhorou, já com o sentido de cada teste (nos tempos, descer é melhorar). “vs média equipa” compara o último valor com a média da equipa nesse momento. Na tendência, subir = melhor.")}
        {" "}{tr("P idade / P mat. = percentil do último valor face aos atletas da academia com a mesma idade / no mesmo estado maturacional (todas as épocas); verde ≥ P75, vermelho ≤ P25. Passa o rato para ver a referência.")}</p>
    </section>
  );
}

function CabecalhoRelatorio({ titulo, sub }: { titulo: string; sub: string }) {
  const tr = useTr();
  return (
    <div style={{ marginBottom: espaco.lg, borderBottom: `2px solid ${cores.acento}`, paddingBottom: espaco.sm }}>
      <div style={{ fontSize: "0.68rem", fontWeight: 700, color: cores.acento, letterSpacing: "0.08em", textTransform: "uppercase" }}>{tr("Academia · Avaliação física")}</div>
      <h2 className="font-display" style={{ margin: "2px 0 0", fontSize: "1.3rem", color: cores.textoForte }}>{titulo}</h2>
      <div style={{ fontSize: "0.82rem", color: cores.textoSuave }}>{sub}</div>
    </div>
  );
}

function Resumo({ titulo, valor, sub, cor }: { titulo: string; valor: string; sub: string; cor?: string }) {
  return (
    <div style={{ border: `1px solid ${cores.borda}`, borderLeft: `3px solid ${cor ?? cores.acento}`, borderRadius: raio.sm, padding: `${espaco.sm}px ${espaco.md}px` }}>
      <div style={{ fontSize: "0.68rem", color: cores.textoFraco, textTransform: "uppercase", letterSpacing: "0.05em" }}>{titulo}</div>
      <div style={{ fontSize: "1.05rem", fontWeight: 700, color: cores.textoForte }}>{valor}</div>
      <div style={{ fontSize: "0.74rem", color: cores.textoSuave }}>{sub}</div>
    </div>
  );
}

/** Mini-gráfico T1→T4; nos tempos o eixo inverte-se para "subir = melhor". */
function Sparkline({ vals, inverter, neutro }: { vals: (number | null)[]; inverter: boolean; neutro?: boolean }) {
  const tr = useTr();
  const pts = vals.map((v, i) => (v == null ? null : { i, v: inverter ? -v : v })).filter(Boolean) as { i: number; v: number }[];
  if (pts.length < 2) return <span style={{ color: cores.textoFraco }}>—</span>;
  const lo = Math.min(...pts.map((p) => p.v)), hi = Math.max(...pts.map((p) => p.v));
  const W = 72, H = 22, x = (i: number) => 4 + (i / 3) * (W - 8), y = (v: number) => (hi === lo ? H / 2 : H - 3 - ((v - lo) / (hi - lo)) * (H - 6));
  const sobe = pts[pts.length - 1].v >= pts[0].v;
  const cor = neutro ? "#94a3b8" : sobe ? "#22c55e" : "#ef4444";
  return (
    <svg width={W} height={H} role="img" aria-label={sobe ? tr("a melhorar") : tr("a piorar")}>
      <polyline points={pts.map((p) => `${x(p.i)},${y(p.v)}`).join(" ")} fill="none" stroke={cor} strokeWidth={1.8} />
      {pts.map((p) => <circle key={p.i} cx={x(p.i)} cy={y(p.v)} r={2.2} fill={cor} />)}
    </svg>
  );
}

const campo: React.CSSProperties = { background: cores.bgCartao, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: cores.textoForte, fontSize: "0.82rem", padding: "5px 8px", height: 32 };
const th: React.CSSProperties = { padding: `8px ${espaco.sm}px`, fontSize: "0.66rem", fontWeight: 600, color: cores.textoSuave, letterSpacing: "0.02em", textAlign: "left", whiteSpace: "nowrap" };
const td: React.CSSProperties = { padding: `6px ${espaco.sm}px`, color: cores.texto };
const nota: React.CSSProperties = { fontSize: "0.72rem", color: cores.textoSuave, lineHeight: 1.5, marginTop: espaco.sm };
