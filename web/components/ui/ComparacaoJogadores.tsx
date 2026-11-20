"use client";

/** Comparar jogadores (até 3). Por omissão cada jogador é comparado CONSIGO
 * MESMO (últimas 4 semanas face à época dele) — o que interessa na
 * monitorização é a mudança de cada um, não um ranking entre colegas. A vista
 * «face ao plantel» (percentis, quem ganha) continua disponível. Contexto explícito:
 *  · o quê: jogos (só com ≥ 30 min), treinos, ou tudo (antes misturava os dois
 *    e a média não queria dizer nada);
 *  · quando: a época ou as últimas 4 semanas;
 *  · como: médias por sessão ou por minuto (justo para quem joga menos).
 * Mostra um cartão por métrica com quem ganha, um radar de percentis face ao
 * plantel todo e a tabela completa. */
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Escolha, Radar } from "@/components/graficos/Graficos";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { pedidoApi } from "@/lib/api-cliente";
import { cores, desvio, espaco, raio, letra } from "@/lib/theme";
import { useTr } from "@/lib/i18n/cliente";

export interface MetricaDef { chave: string; label: string; unidade: string; cor: string; casas: number; peak?: boolean }
export interface JogadorResumo { jogador: string; posicao: string; n_sessoes: number; valores: Record<string, number | null> }
export interface ComparacaoResposta {
  tem_dados: boolean; metricas: MetricaDef[]; jogadores: JogadorResumo[]; benchmark: Record<string, number | null>;
  contexto?: string; por_minuto?: boolean;
}

type Contexto = "jogos" | "treinos" | "todos";
type Face = "proprio" | "plantel";
/** ±10 % da época dele = sem mudança relevante (cinzento). */
const ZONA_IGUAL = 10;
const MAX = 3;
const PALETA = ["#2563eb", "#e11d48", "#16a34a"];
/** Métricas em que mais é pior (para o percentil e para «quem ganha»). */
const MENOS_E_MELHOR = new Set(["hooper_index"]);

export function ComparacaoJogadores({ teamId, inicial }: { teamId: string; inicial: ComparacaoResposta }) {
  const tr = useTr();
  const loc = tr.loc;
  const { oculto } = usePrivacidade();
  const [face, setFace] = useState<Face>("proprio");
  const [recente, setRecente] = useState<ComparacaoResposta | null>(null);
  const [contexto, setContexto] = useState<Contexto>("jogos");
  const [periodo, setPeriodo] = useState<"epoca" | "4">("epoca");
  const [porMin, setPorMin] = useState(false);
  const [dados, setDados] = useState<ComparacaoResposta>(inicial);
  const [aCarregar, setACarregar] = useState(false);
  const [sel, setSel] = useState<string[]>(() => inicial.jogadores.slice(0, 2).map((j) => j.jogador));
  // Os filtros globais do topo (microciclo, dia MD) continuam a aplicar-se.
  const params = useSearchParams();
  const microciclo = params.get("microciclo"), diaMd = params.get("dia_md");

  useEffect(() => {
    let vivo = true;
    setACarregar(true);
    const url = (ult: boolean) => `/api/teams/${teamId}/comparacao/jogadores?${new URLSearchParams({
      contexto, por_minuto: String(porMin), ...(ult ? { ultimos: "4" } : {}),
      ...(microciclo ? { microciclo } : {}), ...(diaMd ? { dia_md: diaMd } : {}) })}`;
    const vazio: ComparacaoResposta = { tem_dados: false, metricas: [], jogadores: [], benchmark: {} };
    // Face ao próprio: época (referência dele) + últimas 4 semanas; face ao plantel: só o período escolhido.
    const pedidos = face === "proprio" ? [url(false), url(true)] : [url(periodo === "4")];
    Promise.all(pedidos.map((u) => pedidoApi<ComparacaoResposta>(u)))
      .then(([a, b]) => { if (vivo) { setDados(a); setRecente(b ?? null); } })
      .catch(() => { if (vivo) { setDados(vazio); setRecente(null); } })
      .finally(() => { if (vivo) setACarregar(false); });
    return () => { vivo = false; };
  }, [teamId, face, contexto, periodo, porMin, microciclo, diaMd]);

  const escolhidos = sel.map((n) => dados.jogadores.find((j) => j.jogador === n)).filter((j): j is JogadorResumo => !!j);
  const metricas = dados.metricas;

  // Percentil de cada jogador escolhido face a todo o plantel (no mesmo contexto).
  const percentis = useMemo(() => {
    const out: Record<string, Record<string, number | null>> = {};
    for (const j of escolhidos) {
      out[j.jogador] = {};
      for (const m of metricas) {
        const v = j.valores[m.chave];
        const todos = dados.jogadores.map((x) => x.valores[m.chave]).filter((x): x is number => x != null);
        if (v == null || todos.length < 3) { out[j.jogador][m.chave] = null; continue; }
        const abaixo = todos.filter((x) => (MENOS_E_MELHOR.has(m.chave) ? x > v : x < v)).length;
        const iguais = todos.filter((x) => x === v).length;
        out[j.jogador][m.chave] = Math.round(((abaixo + iguais / 2) / todos.length) * 100);
      }
    }
    return out;
  }, [escolhidos, metricas, dados.jogadores]);

  function alternar(nome: string) {
    setSel((a) => (a.includes(nome) ? a.filter((n) => n !== nome) : a.length >= MAX ? [...a.slice(1), nome] : [...a, nome]));
  }
  const fmt = (v: number | null | undefined, casas: number) => (v == null ? "—" : v.toLocaleString(loc, { maximumFractionDigits: casas, minimumFractionDigits: casas > 1 ? casas : 0 }));
  const cor = (nome: string) => PALETA[sel.indexOf(nome) % PALETA.length];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: espaco.lg }}>
      {/* Contexto */}
      <div style={{ display: "flex", gap: espaco.md, flexWrap: "wrap", alignItems: "center" }}>
        <Escolha rotulo={tr("Comparar")} valor={face} onChange={setFace}
          opcoes={[{ valor: "proprio", texto: tr("Cada um consigo mesmo") }, { valor: "plantel", texto: tr("Face ao plantel") }]} />
        <Escolha rotulo={tr("Sessões")} valor={contexto} onChange={setContexto}
          opcoes={[{ valor: "jogos", texto: tr("Jogos (≥ 30 min)") }, { valor: "treinos", texto: tr("Treinos") }, { valor: "todos", texto: tr("Tudo") }]} />
        {face === "plantel" && (
          <Escolha rotulo={tr("Período")} valor={periodo} onChange={setPeriodo}
            opcoes={[{ valor: "epoca", texto: tr("Época") }, { valor: "4", texto: tr("Últimas 4 semanas") }]} />
        )}
        <Escolha rotulo={tr("Unidade")} valor={porMin ? "min" : "sessao"} onChange={(v) => setPorMin(v === "min")}
          opcoes={[{ valor: "sessao", texto: tr("Média por sessão") }, { valor: "min", texto: tr("Por minuto") }]} />
        {aCarregar && <span style={{ fontSize: letra.pequeno, color: cores.textoSuave }}>{tr("A calcular…")}</span>}
      </div>

      {/* Jogadores */}
      <div style={cartao}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: espaco.sm }}>
          <span style={{ fontSize: letra.pequeno, color: cores.textoSuave }}>{tr("Escolhe até {0} jogadores · {1} de {0}", [MAX, escolhidos.length])}</span>
          {sel.length > 0 && <button onClick={() => setSel([])} style={{ background: "none", border: "none", color: cores.acento, fontSize: letra.pequeno, cursor: "pointer" }}>{tr("Limpar")}</button>}
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {dados.jogadores.map((j) => {
            const ativo = sel.includes(j.jogador);
            return (
              <button key={j.jogador} onClick={() => alternar(j.jogador)} aria-pressed={ativo}
                style={{ display: "inline-flex", alignItems: "center", gap: 6, borderRadius: 999, padding: "6px 12px", fontSize: letra.pequeno, fontWeight: 600, cursor: "pointer",
                  background: ativo ? `color-mix(in srgb, ${cor(j.jogador)} 14%, transparent)` : cores.bgCartao,
                  border: `1.5px solid ${ativo ? cor(j.jogador) : cores.borda}`, color: ativo ? cores.textoForte : cores.textoSuave }}>
                {ativo && <span style={{ width: 8, height: 8, borderRadius: "50%", background: cor(j.jogador) }} />}
                {nomeOuOculto(j.jogador, oculto)} <span style={{ color: cores.textoFraco, fontWeight: 400 }}>{j.posicao}</span>
              </button>
            );
          })}
        </div>
      </div>

      {!dados.tem_dados ? (
        <p style={{ color: cores.textoSuave, fontSize: letra.texto }}>{tr("Sem sessões neste contexto. Experimenta outro período ou «Tudo».")}</p>
      ) : escolhidos.length === 0 ? (
        <p style={{ color: cores.textoSuave, fontSize: letra.texto }}>{tr("Escolhe pelo menos um jogador.")}</p>
      ) : face === "proprio" ? (
        <FaceAoProprio escolhidos={escolhidos} recente={recente} metricas={metricas} cor={cor} fmt={fmt} />
      ) : (
        <>
          {/* Uma métrica por cartão: quem ganha + barras */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(230px, 1fr))", gap: espaco.md }}>
            {metricas.map((m) => {
              const vals = escolhidos.map((j) => ({ j, v: j.valores[m.chave] }));
              const validos = vals.filter((x) => x.v != null) as { j: JogadorResumo; v: number }[];
              const melhor = validos.length > 1 ? validos.reduce((a, b) => (MENOS_E_MELHOR.has(m.chave) ? (b.v < a.v ? b : a) : (b.v > a.v ? b : a))) : null;
              const bench = dados.benchmark[m.chave];
              const topo = Math.max(1, ...validos.map((x) => x.v), bench ?? 0) * 1.05;
              return (
                <div key={m.chave} style={cartao}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 6 }}>
                    <span style={{ fontSize: letra.pequeno, fontWeight: 600, color: cores.textoSuave }}>{tr(m.label)} {m.unidade && <span style={{ fontWeight: 400 }}>({m.unidade})</span>}</span>
                    {melhor && <span title={tr("Melhor dos escolhidos")} style={{ fontSize: letra.pequeno, fontWeight: 700, color: cor(melhor.j.jogador) }}>★ {nomeOuOculto(melhor.j.jogador, oculto).split(" ").slice(-1)[0]}</span>}
                  </div>
                  <div className="font-display" style={{ fontSize: letra.numero, fontWeight: 700, color: melhor ? cor(melhor.j.jogador) : cores.textoForte, margin: "2px 0 8px" }}>
                    {fmt(melhor?.v ?? validos[0]?.v, m.casas)}
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {vals.map(({ j, v }) => (
                      <div key={j.jogador} style={{ display: "grid", gridTemplateColumns: "1fr 54px", alignItems: "center", gap: 6 }}
                        title={`${nomeOuOculto(j.jogador, oculto)}: ${fmt(v, m.casas)}${percentis[j.jogador]?.[m.chave] != null ? ` · P${percentis[j.jogador][m.chave]} ${tr("no plantel")}` : ""}`}>
                        <div style={{ position: "relative", height: 8, background: cores.superficie, borderRadius: 4 }}>
                          <div style={{ width: `${((v ?? 0) / topo) * 100}%`, height: "100%", background: cor(j.jogador), borderRadius: 4, transition: "width 0.35s ease" }} />
                          {bench != null && <div title={tr("Média do plantel")} style={{ position: "absolute", top: -3, bottom: -3, left: `${(bench / topo) * 100}%`, width: 2, background: cores.textoForte, opacity: 0.5 }} />}
                        </div>
                        <span style={{ fontSize: letra.pequeno, textAlign: "right", fontVariantNumeric: "tabular-nums", color: cores.texto }}>{fmt(v, m.casas)}</span>
                      </div>
                    ))}
                  </div>
                  <div style={{ fontSize: letra.legenda, color: cores.textoFraco, marginTop: 6 }}>{tr("traço = média do plantel")} ({fmt(bench, m.casas)})</div>
                </div>
              );
            })}
          </div>

          {/* Radar + resumo */}
          <div style={{ ...cartao, display: "grid", gridTemplateColumns: "minmax(280px, 1.2fr) minmax(240px, 1fr)", gap: espaco.lg, alignItems: "center" }} className="comparacao-radar">
            <div>
              <div className="font-display" style={{ fontSize: letra.realce, fontWeight: 600, color: cores.textoForte }}>{tr("Perfil · percentil no plantel")}</div>
              <div style={{ fontSize: letra.pequeno, color: cores.textoSuave, marginBottom: espaco.sm }}>{tr("0 = o mais baixo do plantel, 100 = o mais alto, no mesmo contexto (jogos/treinos, período, unidade).")}</div>
              <Radar eixos={metricas.map((m) => tr(m.label))}
                series={escolhidos.map((j) => ({ nome: nomeOuOculto(j.jogador, oculto), cor: cor(j.jogador), valores: metricas.map((m) => percentis[j.jogador]?.[m.chave] ?? null) }))} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: espaco.sm }}>
              {escolhidos.map((j) => {
                const ps = metricas.map((m) => ({ m, p: percentis[j.jogador]?.[m.chave] })).filter((x): x is { m: MetricaDef; p: number } => x.p != null);
                const media = ps.length ? Math.round(ps.reduce((a, b) => a + b.p, 0) / ps.length) : null;
                const forte = ps.length ? ps.reduce((a, b) => (b.p > a.p ? b : a)) : null;
                const fraco = ps.length ? ps.reduce((a, b) => (b.p < a.p ? b : a)) : null;
                return (
                  <div key={j.jogador} style={{ display: "flex", alignItems: "center", gap: espaco.md, padding: espaco.md, borderRadius: raio.md, border: `1.5px solid ${cor(j.jogador)}` }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 700, color: cores.textoForte, fontSize: letra.texto }}>{nomeOuOculto(j.jogador, oculto)} <span style={{ color: cores.textoFraco, fontWeight: 400, fontSize: letra.pequeno }}>{j.posicao} · {j.n_sessoes} {tr("sessões")}</span></div>
                      <div style={{ fontSize: letra.pequeno, color: cores.textoSuave }}>
                        {forte && <>{tr("Melhor")}: {tr(forte.m.label)} (P{forte.p})</>}{fraco && <> · {tr("Mais baixo")}: {tr(fraco.m.label)} (P{fraco.p})</>}
                      </div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div className="font-display" style={{ fontSize: letra.titulo, fontWeight: 700, color: cor(j.jogador), lineHeight: 1 }}>{media ?? "—"}</div>
                      <div style={{ fontSize: letra.legenda, color: cores.textoFraco }}>{tr("percentil médio")}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <p style={{ color: cores.textoSuave, fontSize: letra.pequeno, margin: 0 }}>
            {tr("Descritivo, não é uma nota: mais distância num jogo pode ser a função na equipa. Velocidade máxima = a mais alta no período. No Hooper, menos é melhor.")}
          </p>
        </>
      )}
    </div>
  );
}

/** Cada jogador face a ele próprio: últimas 4 semanas vs a época dele, no
 * mesmo contexto (jogos/treinos, unidade). Sem «quem ganha». */
function FaceAoProprio({ escolhidos, recente, metricas, cor, fmt }: {
  escolhidos: JogadorResumo[]; recente: ComparacaoResposta | null; metricas: MetricaDef[];
  cor: (n: string) => string; fmt: (v: number | null | undefined, casas: number) => string;
}) {
  const tr = useTr();
  const { oculto } = usePrivacidade();
  const rec = (nome: string) => recente?.jogadores.find((j) => j.jogador === nome);
  // % da época dele (100 = igual ao normal da época).
  const pct = (j: JogadorResumo, chave: string): number | null => {
    const e = j.valores[chave], r = rec(j.jogador)?.valores[chave];
    return e != null && r != null && e > 0 ? Math.round((r / e) * 100) : null;
  };
  const corVar = (d: number | null) => (d == null || Math.abs(d) <= ZONA_IGUAL ? cores.textoSuave : d > 0 ? desvio.acima : desvio.abaixo);
  return (
    <>
      <p style={{ color: cores.textoSuave, fontSize: letra.texto, margin: 0 }}>
        {tr("Últimas 4 semanas de cada jogador face à época DELE (no mesmo contexto). Azul = acima do normal dele, violeta = abaixo; ±{0} % conta como igual.", [ZONA_IGUAL])}
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(230px, 1fr))", gap: espaco.md }}>
        {metricas.map((m) => (
          <div key={m.chave} style={cartao}>
            <span style={{ fontSize: letra.pequeno, fontWeight: 600, color: cores.textoSuave }}>{tr(m.label)} {m.unidade && <span style={{ fontWeight: 400 }}>({m.unidade})</span>}</span>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 8 }}>
              {escolhidos.map((j) => {
                const p = pct(j, m.chave);
                const d = p == null ? null : p - 100;
                const larg = d == null ? 0 : (Math.min(Math.abs(d), 50) / 50) * 50;
                return (
                  <div key={j.jogador} title={`${nomeOuOculto(j.jogador, oculto)}: ${fmt(rec(j.jogador)?.valores[m.chave], m.casas)} ${tr("vs época")} ${fmt(j.valores[m.chave], m.casas)}`}
                    style={{ display: "grid", gridTemplateColumns: "10px 1fr 52px", alignItems: "center", gap: 6 }}>
                    <span style={{ width: 8, height: 8, borderRadius: "50%", background: cor(j.jogador) }} />
                    <div style={{ position: "relative", height: 8, background: cores.superficie, borderRadius: 4 }}>
                      <div style={{ position: "absolute", left: "50%", top: -3, bottom: -3, width: 1, background: cores.textoFraco }} />
                      {d != null && <div style={{ position: "absolute", top: 0, bottom: 0, borderRadius: 4, background: corVar(d),
                        left: d >= 0 ? "50%" : `${50 - larg}%`, width: `${larg}%`, transition: "all 0.35s ease" }} />}
                    </div>
                    <span style={{ fontSize: letra.pequeno, textAlign: "right", fontWeight: 600, fontVariantNumeric: "tabular-nums", color: corVar(d) }}>
                      {d == null ? "—" : `${d > 0 ? "+" : ""}${d}%`}
                    </span>
                  </div>
                );
              })}
            </div>
            <div style={{ fontSize: letra.legenda, color: cores.textoFraco, marginTop: 6 }}>{tr("traço = a época de cada um")}</div>
          </div>
        ))}
      </div>

      <div style={{ ...cartao, display: "grid", gridTemplateColumns: "minmax(280px, 1.2fr) minmax(240px, 1fr)", gap: espaco.lg, alignItems: "center" }} className="comparacao-radar">
        <div>
          <div className="font-display" style={{ fontSize: letra.realce, fontWeight: 600, color: cores.textoForte }}>{tr("Perfil · últimas 4 semanas face à época dele")}</div>
          <div style={{ fontSize: letra.pequeno, color: cores.textoSuave, marginBottom: espaco.sm }}>{tr("O anel do meio = a época de cada jogador; para fora = mais do que o normal dele.")}</div>
          <Radar eixos={metricas.map((m) => tr(m.label))} marcaMeio={tr("época")}
            formatar={(v) => tr("{0}% da época dele", [Math.round(v * 2)])}
            series={escolhidos.map((j) => ({ nome: nomeOuOculto(j.jogador, oculto), cor: cor(j.jogador),
              valores: metricas.map((m) => { const p = pct(j, m.chave); return p == null ? null : Math.min(100, p / 2); }) }))} />
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: espaco.sm }}>
          {escolhidos.map((j) => {
            const ds = metricas.map((m) => ({ m, d: pct(j, m.chave) })).filter((x): x is { m: MetricaDef; d: number } => x.d != null).map((x) => ({ m: x.m, d: x.d - 100 }));
            const sobe = ds.length ? ds.reduce((a, b) => (b.d > a.d ? b : a)) : null;
            const desce = ds.length ? ds.reduce((a, b) => (b.d < a.d ? b : a)) : null;
            const n = rec(j.jogador)?.n_sessoes ?? 0;
            return (
              <div key={j.jogador} style={{ padding: espaco.md, borderRadius: raio.md, border: `1.5px solid ${cor(j.jogador)}` }}>
                <div style={{ fontWeight: 700, color: cores.textoForte, fontSize: letra.texto }}>{nomeOuOculto(j.jogador, oculto)} <span style={{ color: cores.textoFraco, fontWeight: 400, fontSize: letra.pequeno }}>{j.posicao} · {n} {tr("sessões nas últimas 4 semanas")}</span></div>
                <div style={{ fontSize: letra.pequeno, color: cores.textoSuave, marginTop: 2 }}>
                  {n === 0 ? tr("Sem sessões nas últimas 4 semanas neste contexto.") : <>
                    {sobe && sobe.d > ZONA_IGUAL && <span style={{ color: desvio.acima }}>{tr("Mais subiu")}: {tr(sobe.m.label)} (+{sobe.d}%)</span>}
                    {sobe && sobe.d > ZONA_IGUAL && desce && desce.d < -ZONA_IGUAL && " · "}
                    {desce && desce.d < -ZONA_IGUAL && <span style={{ color: desvio.abaixo }}>{tr("Mais desceu")}: {tr(desce.m.label)} ({desce.d}%)</span>}
                    {!(sobe && sobe.d > ZONA_IGUAL) && !(desce && desce.d < -ZONA_IGUAL) && tr("Tudo dentro de ±{0} % da época dele.", [ZONA_IGUAL])}
                  </>}
                </div>
              </div>
            );
          })}
        </div>
      </div>
      <p style={{ color: cores.textoSuave, fontSize: letra.pequeno, margin: 0 }}>
        {tr("Descritivo: uma mudança é motivo para perceber porquê (função, minutos, regresso), não uma nota. No Hooper, subir é pior.")}
      </p>
    </>
  );
}

const cartao: React.CSSProperties = { background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md, minWidth: 0 };
