"use client";

/** Centro de Controlo — só apresentação (os dados chegam por props), para se
 * poder pré-visualizar e testar sem API. Hierarquia: estado do plantel em
 * cima; quem precisa de atenção e planeado vs realizado lado a lado; carga
 * externa e exposição da semana por baixo. */
import { useState } from "react";
import { cores, espaco, raio } from "@/lib/theme";
import { Cartao, Etiqueta, SecaoTitulo, Vazio, estiloBotao } from "@/components/ui/base";
import { KpiCargaCard, type KpiCarga } from "@/components/ui/KpiCargaCard";
import { NomeJogador } from "@/components/ui/NomeJogador";
import { useTr } from "@/lib/i18n/cliente";
import type { Tr } from "@/lib/i18n/core";

// ── Tipos (espelham a API) ───────────────────────────────────────────────────
export interface SquadStatus {
  normal: number;
  attention: number;
  highAttention: number;
  total: number;
}

export interface Alerta {
  player_id: string;
  player_name: string;
  status: "normal" | "attention" | "high-attention";
  primary_reason: string;
  reason_text: string;
  metric_value: string;
  sinais?: { chave: string; texto: string; detalhe: { valor?: number; limite?: number; ref?: [number, number]; janela?: number; minimo?: number } }[];
}

export interface JogadorExposicao {
  jogador: string;
  posicao: string;
  ratio: number;
  zona: "baixo" | "ok" | "alto";
  n_treinos?: number;
  acumulado?: number;
  referencia?: number;
  fonte_referencia?: "media_90" | "posicao" | "equipa" | "pico";
  em_falta?: number;
}

export interface MetricaExposicao {
  chave: string;
  label: string;
  ref: [number, number];
  ratio_equipa: number;
  zona_equipa: "baixo" | "ok" | "alto";
  posicoes: { posicao: string; n_jogadores: number; ratio: number; zona: "baixo" | "ok" | "alto" }[];
  jogadores: JogadorExposicao[];
}

export interface ExposicaoSemana {
  tem_dados: boolean;
  motivo: string | null;
  microciclo: number | null;
  microciclos_disponiveis?: number[];
  metricas: MetricaExposicao[];
}

export interface PlaneadoRealizado {
  tem_dados: boolean;
  motivo: string | null;
  data?: string;
  dia_md?: string | null;
  microciclo?: number | null;
  tem_plano?: boolean;
  n_jogadores?: number;
  limites?: { ok: number; atencao: number };
  metricas?: { chave: string; label: string; unidade: string; planeado: number | null; real: number | null; desvio_pct: number | null; estado: "ok" | "atencao" | "fora" | "sem_plano" }[];
  jogadores_fora?: { jogador: string; real: number; desvio_pct: number }[];
}

export interface CentroControloProps {
  squadStatus: SquadStatus | null;
  alertas: Alerta[];
  kpis: KpiCarga[];
  sessaoRecente: string | null;
  exposicao: ExposicaoSemana | null;
  planeado: PlaneadoRealizado | null;
  aCarregarExposicao?: boolean;
  onMicrociclo: (mc: number) => void;
  navegar: (rota: string) => void;
}

const COR_STATUS = { normal: cores.sucesso, attention: cores.atencao, "high-attention": cores.perigo } as const;
const COR_ZONA: Record<string, string> = { baixo: cores.perigo, ok: cores.sucesso, alto: cores.atencao };
const LABEL_ZONA: Record<string, string> = { baixo: "Exposição baixa", ok: "Na referência", alto: "Exposição elevada" };
const COR_PLANO: Record<string, string> = { ok: cores.sucesso, atencao: cores.atencao, fora: cores.perigo, sem_plano: cores.textoFraco };

export function CentroControlo(p: CentroControloProps) {
  const tr = useTr();
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: espaco.xl }}>
      {p.squadStatus && <EstadoPlantel s={p.squadStatus} />}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 360px), 1fr))", gap: espaco.lg, alignItems: "start" }}>
        <PrecisamAtencao alertas={p.alertas} navegar={p.navegar} />
        <PlaneadoVsRealizado dados={p.planeado} navegar={p.navegar} />
      </div>

      {p.kpis.length > 0 && (
        <section>
          <SecaoTitulo
            subtitulo={p.sessaoRecente ? tr("Sessão de {0} face à média dos últimos 28 dias", [new Date(p.sessaoRecente).toLocaleDateString(tr.loc, { day: "numeric", month: "long" })]) : undefined}
            acoes={<button onClick={() => p.navegar("/carga-externa")} style={estiloBotao.ligacao}>{tr("Ver detalhe")}</button>}
          >
            {tr("Carga externa da equipa")}</SecaoTitulo>
          <div className="grelha-kpis">
            {p.kpis.map((k) => <KpiCargaCard key={k.chave} kpi={k} compacto />)}
          </div>
        </section>
      )}

      {p.exposicao && <Exposicao exposicao={p.exposicao} aCarregar={p.aCarregarExposicao} onMicrociclo={p.onMicrociclo} />}
    </div>
  );
}

// ── Estado do plantel: uma faixa, três números ───────────────────────────────
function EstadoPlantel({ s }: { s: SquadStatus }) {
  const tr = useTr();
  const itens = [
    { k: "normal" as const, label: tr("Normal"), n: s.normal },
    { k: "attention" as const, label: tr("Atenção"), n: s.attention },
    { k: "high-attention" as const, label: tr("Atenção alta"), n: s.highAttention },
  ];
  return (
    <Cartao padding={0}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)" }}>
        {itens.map((it, i) => (
          <div key={it.k} style={{ padding: `${espaco.md}px ${espaco.lg}px`, borderLeft: i ? `1px solid ${cores.borda}` : "none" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 7, fontSize: "0.76rem", color: cores.textoSuave }}>
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: COR_STATUS[it.k] }} />
              {tr(it.label)}
            </div>
            <div className="font-display" style={{ fontSize: "1.6rem", fontWeight: 600, color: it.n && it.k !== "normal" ? COR_STATUS[it.k] : cores.textoForte, lineHeight: 1.2, marginTop: 2, fontVariantNumeric: "tabular-nums" }}>
              {it.n}
              <span style={{ fontSize: "0.78rem", fontWeight: 400, color: cores.textoFraco, marginLeft: 6 }}>/ {s.total}</span>
            </div>
          </div>
        ))}
      </div>
    </Cartao>
  );
}

// ── Quem precisa de atenção: agrupado por motivo ─────────────────────────────
// Um grupo por sinal (ex.: «Exposição HSR elevada · 14 jogadores») em vez de
// uma linha por jogador com o mesmo texto repetido.
type Sinal = { chave: string; texto: string; detalhe: { valor?: number; limite?: number; ref?: [number, number]; janela?: number; minimo?: number } };
const ORDEM_SINAIS = ["acwr", "hsr_alto", "sprint_alto", "vmax", "hsr_baixo", "sprint_baixo"];
const N_CHIPS = 12;

function sinaisDe(a: Alerta): Sinal[] {
  if (a.sinais?.length) return a.sinais;
  return [{ chave: a.primary_reason, texto: a.reason_text, detalhe: {} }];
}

function valorCurto(s: Sinal, loc: string): string {
  const v = s.detalhe.valor;
  if (v == null) return "";
  if (s.chave === "vmax") return `${Math.round(v)}%`;
  if (s.chave === "acwr") return v.toLocaleString(loc, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${v.toLocaleString(loc, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}×`;
}

function referencia(s: Sinal, tr: Tr): string {
  const d = s.detalhe, n2 = (x: number) => x.toLocaleString(tr.loc, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (s.chave === "acwr" && d.limite != null) return tr("limite {0}", [n2(d.limite)]);
  if (s.chave === "vmax" && d.minimo != null) return tr("% do recorde em {0} dias · mín. {1}%", [d.janela ?? 7, d.minimo]);
  if (d.ref) return tr("semana ÷ jogo · ref. {0}–{1}×", [n2(d.ref[0]), n2(d.ref[1])]);
  return "";
}

function PrecisamAtencao({ alertas, navegar }: { alertas: Alerta[]; navegar: (r: string) => void }) {
  const tr = useTr();
  const [abertos, setAbertos] = useState<Record<string, boolean>>({});
  const grupos = new Map<string, { sinal: Sinal; itens: { a: Alerta; s: Sinal }[] }>();
  for (const a of alertas) {
    for (const s of sinaisDe(a)) {
      const g = grupos.get(s.chave) ?? { sinal: s, itens: [] };
      g.itens.push({ a, s });
      grupos.set(s.chave, g);
    }
  }
  const lista = [...grupos.values()].sort((x, y) => {
    const ox = ORDEM_SINAIS.indexOf(x.sinal.chave), oy = ORDEM_SINAIS.indexOf(y.sinal.chave);
    return (ox < 0 ? 99 : ox) - (oy < 0 ? 99 : oy);
  });
  const altos = alertas.filter((a) => a.status === "high-attention").length;
  // Marcar quem tem mais do que um sinal só ajuda quando nem todos têm.
  const marcar = altos > 0 && altos < alertas.length;
  return (
    <section>
      <SecaoTitulo subtitulo={alertas.length ? tr("{0} atleta(s) com sinais de ACWR, velocidade ou exposição", [alertas.length]) : undefined}>
        {tr("Precisam de atenção")}</SecaoTitulo>
      {alertas.length === 0 ? (
        <Vazio>{tr("Ninguém precisa de atenção especial neste momento.")}</Vazio>
      ) : (
        <Cartao padding={0}>
          {lista.map((g, i) => {
            const aberto = abertos[g.sinal.chave];
            const itens = [...g.itens].sort((x, y) => (y.s.detalhe.valor ?? 0) - (x.s.detalhe.valor ?? 0));
            const visiveis = aberto ? itens : itens.slice(0, N_CHIPS);
            return (
              <div key={g.sinal.chave} style={{ padding: `${espaco.md}px ${espaco.lg}px`, borderTop: i ? `1px solid ${cores.borda}` : "none" }}>
                <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: espaco.md, flexWrap: "wrap", marginBottom: 8 }}>
                  <span style={{ fontSize: "0.88rem", fontWeight: 600, color: cores.textoForte }}>
                    {tr(g.sinal.texto)}
                    <span style={{ fontWeight: 400, color: cores.textoSuave }}> · {tr("{0} jogador(es)", [g.itens.length])}</span>
                  </span>
                  <span style={{ fontSize: "0.74rem", color: cores.textoFraco }}>{referencia(g.sinal, tr)}</span>
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {visiveis.map(({ a, s }) => (
                    <button key={a.player_id} onClick={() => navegar(`/jogadores?nome=${encodeURIComponent(a.player_name)}`)} className="lm-linha"
                      title={a.status === "high-attention" ? tr("Mais do que um sinal") : undefined}
                      style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "3px 9px", borderRadius: 999, cursor: "pointer",
                        border: `1px solid ${cores.borda}`, background: "transparent", fontSize: "0.78rem", color: cores.texto }}>
                      {marcar && a.status === "high-attention" && <span style={{ width: 6, height: 6, borderRadius: "50%", background: COR_STATUS["high-attention"] }} />}
                      <NomeJogador nome={a.player_name} />
                      <span style={{ fontWeight: 600, color: cores.textoForte, fontVariantNumeric: "tabular-nums" }}>{valorCurto(s, tr.loc)}</span>
                    </button>
                  ))}
                  {itens.length > N_CHIPS && (
                    <button onClick={() => setAbertos({ ...abertos, [g.sinal.chave]: !aberto })} style={{ ...estiloBotao.ligacao, fontSize: "0.78rem" }}>
                      {aberto ? tr("Mostrar menos") : tr("+ {0}", [itens.length - N_CHIPS])}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
          {altos > 0 && (
            <div style={{ borderTop: `1px solid ${cores.borda}`, padding: `8px ${espaco.lg}px`, fontSize: "0.74rem", color: cores.textoSuave }}>
              {marcar && <span style={{ display: "inline-block", width: 7, height: 7, borderRadius: "50%", background: COR_STATUS["high-attention"], marginRight: 6 }} />}
              {marcar ? tr("{0} com mais do que um sinal (atenção alta)", [altos]) : tr("Todos com mais do que um sinal (atenção alta)")}
            </div>
          )}
        </Cartao>
      )}
    </section>
  );
}

// ── Planeado vs realizado: tabela curta ──────────────────────────────────────
function fmt(v: number | null, unidade: string, loc: string): string {
  if (v == null) return "—";
  const n = unidade === "" ? v.toLocaleString(loc, { minimumFractionDigits: 1, maximumFractionDigits: 1 }) : Math.round(v).toLocaleString(loc);
  return unidade ? `${n} ${unidade}` : n;
}

function PlaneadoVsRealizado({ dados, navegar }: { dados: PlaneadoRealizado | null; navegar: (r: string) => void }) {
  const tr = useTr();
  const data = dados?.data ? new Date(`${dados.data}T00:00:00`).toLocaleDateString(tr.loc, { weekday: "long", day: "numeric", month: "short" }) : "";
  const contexto = [data, dados?.dia_md, dados?.microciclo != null ? `microciclo ${dados.microciclo}` : null].filter(Boolean).join(" · ");
  return (
    <section>
      <SecaoTitulo
        subtitulo={dados?.tem_dados ? tr("Último treino: {0}", [contexto]) : undefined}
        acoes={<button onClick={() => navegar("/planeamento")} style={estiloBotao.ligacao}>{dados?.tem_plano ? tr("Planeamento") : tr("Planear")}</button>}
      >
        {tr("Planeado vs realizado")}</SecaoTitulo>
      {!dados?.tem_dados ? (
        <Vazio>{dados?.motivo ?? tr("Ainda não há sessões de treino.")}</Vazio>
      ) : (
        <Cartao padding={0}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {["", "Planeado", "Realizado", "Desvio"].map((h, i) => (
                  <th key={i} style={{ ...th, textAlign: i ? "right" : "left" }}>{tr(h)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(dados.metricas ?? []).map((m) => {
                const cor = COR_PLANO[m.estado];
                return (
                  <tr key={m.chave} style={{ borderTop: `1px solid ${cores.borda}` }}>
                    <td style={{ ...td, color: cores.textoForte, fontWeight: 600 }}>{tr(m.label)}</td>
                    <td style={{ ...td, textAlign: "right", color: cores.textoSuave }}>{fmt(m.planeado, m.unidade, tr.loc)}</td>
                    <td style={{ ...td, textAlign: "right", color: cores.textoForte }}>{fmt(m.real, m.unidade, tr.loc)}</td>
                    <td style={{ ...td, textAlign: "right" }}>
                      {m.desvio_pct != null ? <Etiqueta cor={cor}>{m.desvio_pct > 0 ? "+" : ""}{m.desvio_pct}%</Etiqueta> : <span style={{ color: cores.textoFraco }}>—</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {(!dados.tem_plano || (dados.jogadores_fora?.length ?? 0) > 0) && (
            <div style={{ borderTop: `1px solid ${cores.borda}`, padding: `9px ${espaco.lg}px`, fontSize: "0.76rem", color: cores.textoSuave, lineHeight: 1.5 }}>
              {!dados.tem_plano ? (
                tr("Sem valores planeados para este dia — define-os no Planeamento para ver o desvio.")
              ) : (
                <>
                  {tr("HSR mais afastado do plano:")}{" "}
                  {dados.jogadores_fora!.map((j, i) => (
                    <span key={j.jogador}>
                      {i > 0 && ", "}
                      <NomeJogador nome={j.jogador} /> <span style={{ color: j.desvio_pct > 0 ? cores.atencao : cores.perigo, fontWeight: 600 }}>{j.desvio_pct > 0 ? "+" : ""}{j.desvio_pct}%</span>
                    </span>
                  ))}
                </>
              )}
            </div>
          )}
        </Cartao>
      )}
    </section>
  );
}

// ── Exposição da semana: um cartão, separadores HSR / Sprint ────────────────
const FONTE_LABEL: Record<string, string> = {
  media_90: "média por 90' dos últimos jogos completos",
  posicao: "sem jogos de 60' — mediana da posição",
  equipa: "sem jogos de 60' — mediana da equipa",
  pico: "pico em jogo (jogos sem minutos registados)",
};

function dica(j: JogadorExposicao, label: string, tr: Tr): string | undefined {
  const partes: string[] = [];
  if (j.acumulado != null && j.referencia != null) partes.push(tr("{0}: {1} m acumulados ÷ {2} m de referência", [label, Math.round(j.acumulado), Math.round(j.referencia)]));
  if (j.fonte_referencia) partes.push(tr("Referência: {0}", [tr(FONTE_LABEL[j.fonte_referencia] ?? j.fonte_referencia)]));
  if (j.n_treinos != null) partes.push(tr("{0} treino(s) somados", [j.n_treinos]));
  return partes.length ? partes.join("\n") : undefined;
}

function Exposicao({ exposicao, aCarregar, onMicrociclo }: { exposicao: ExposicaoSemana; aCarregar?: boolean; onMicrociclo: (mc: number) => void }) {
  const tr = useTr();
  const [chave, setChave] = useState<string | null>(null);
  const metricas = exposicao.metricas ?? [];
  const m = metricas.find((x) => x.chave === chave) ?? metricas[0];
  const seletor = (exposicao.microciclos_disponiveis?.length ?? 0) > 0 && (
    <select aria-label={tr("Microciclo")} value={exposicao.microciclo ?? ""} onChange={(e) => onMicrociclo(Number(e.target.value))} disabled={aCarregar} style={selectEstilo}>
      {[...(exposicao.microciclos_disponiveis ?? [])].reverse().map((mc) => <option key={mc} value={mc}>{tr("Microciclo")}{" "}{mc}</option>)}
    </select>
  );
  return (
    <section>
      <SecaoTitulo
        ajuda={tr("Soma dos treinos do microciclo (jogos excluídos) ÷ referência de jogo do jogador (média por 90' dos últimos jogos com ≥ 60'). Passa o rato num jogador para ver o cálculo.")}
        acoes={<>{aCarregar && <span style={{ fontSize: "0.75rem", color: cores.textoSuave }}>{tr("A calcular…")}</span>}{seletor}</>}
      >
        {tr("Exposição da semana vs jogo")}</SecaoTitulo>
      {!exposicao.tem_dados || !m ? (
        <Vazio>{exposicao.motivo ?? tr("Sem dados de exposição.")}</Vazio>
      ) : (
        <Cartao padding={0}>
          {/* Separadores + resumo da equipa */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: espaco.md, flexWrap: "wrap", padding: `${espaco.md}px ${espaco.lg}px`, borderBottom: `1px solid ${cores.borda}` }}>
            <div role="tablist" style={{ display: "flex", gap: 2, padding: 3, borderRadius: 9, background: cores.superficie }}>
              {metricas.map((x) => {
                const ativo = x.chave === m.chave;
                return (
                  <button key={x.chave} role="tab" aria-selected={ativo} onClick={() => setChave(x.chave)}
                    style={{ border: "none", borderRadius: 7, padding: "5px 14px", fontSize: "0.82rem", fontWeight: 600, cursor: "pointer",
                      background: ativo ? cores.bgCartao : "transparent", color: ativo ? cores.textoForte : cores.textoSuave,
                      boxShadow: ativo ? "0 1px 2px rgb(0 0 0 / 0.12)" : "none" }}>
                    {tr(x.label)}
                  </button>
                );
              })}
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: espaco.sm }}>
              <span style={{ fontSize: "0.76rem", color: cores.textoSuave }}>{tr("Equipa")}</span>
              <span className="font-display" style={{ fontSize: "1.3rem", fontWeight: 600, color: COR_ZONA[m.zona_equipa], fontVariantNumeric: "tabular-nums" }}>{m.ratio_equipa.toFixed(2)}×</span>
              <Etiqueta cor={COR_ZONA[m.zona_equipa]}>{tr(LABEL_ZONA[m.zona_equipa])}</Etiqueta>
              <span style={{ fontSize: "0.74rem", color: cores.textoFraco }}>{tr("ref.")}{" "}{m.ref[0].toFixed(2)}–{m.ref[1].toFixed(2)}×</span>
            </div>
          </div>

          {m.posicoes.length > 1 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: `${espaco.sm}px ${espaco.lg}px`, borderBottom: `1px solid ${cores.borda}` }}>
              {m.posicoes.map((pos) => (
                <Etiqueta key={pos.posicao} cor={COR_ZONA[pos.zona]} title={tr("{0} jogador(es)", [pos.n_jogadores])}>{pos.posicao} {pos.ratio.toFixed(2)}×</Etiqueta>
              ))}
            </div>
          )}

          {/* Jogadores em duas colunas, com a zona de referência marcada */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 440px), 1fr))", columnGap: espaco.xxl, rowGap: 6, padding: `${espaco.md}px ${espaco.lg}px ${espaco.lg}px` }}>
            {m.jogadores.map((j) => {
              const cor = COR_ZONA[j.zona];
              const escala = Math.max(m.ref[1] * 1.4, j.ratio);
              const pct = escala > 0 ? Math.min(100, (j.ratio / escala) * 100) : 0;
              const zIni = (m.ref[0] / escala) * 100;
              const zFim = (m.ref[1] / escala) * 100;
              return (
                <div key={j.jogador} title={dica(j, m.label, tr)} style={{ display: "grid", gridTemplateColumns: "minmax(120px, 1.2fr) 1.5fr 78px 44px", alignItems: "center", gap: espaco.sm, fontSize: "0.78rem" }}>
                  <span style={{ color: cores.texto, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    <NomeJogador nome={j.jogador} />{j.posicao && j.posicao !== "—" && <span style={{ color: cores.textoFraco }}> · {j.posicao}</span>}
                  </span>
                  <div style={{ position: "relative", height: 6, background: cores.superficieHover, borderRadius: 3 }}>
                    <div style={{ position: "absolute", top: -2, bottom: -2, left: `${zIni}%`, width: `${zFim - zIni}%`, background: "rgb(34 197 94 / 0.14)", borderRadius: 2 }} />
                    <div style={{ position: "absolute", top: 0, bottom: 0, left: 0, width: `${pct}%`, background: cor, borderRadius: 3 }} />
                  </div>
                  <span style={{ color: cores.textoSuave, textAlign: "right", whiteSpace: "nowrap", fontVariantNumeric: "tabular-nums" }}>{j.em_falta ? tr("faltam {0} m", [Math.round(j.em_falta)]) : ""}</span>
                  <span style={{ fontWeight: 600, color: cor, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{j.ratio.toFixed(2)}×</span>
                </div>
              );
            })}
          </div>
        </Cartao>
      )}
    </section>
  );
}

const th: React.CSSProperties = { padding: `9px ${espaco.lg}px`, fontSize: "0.68rem", fontWeight: 500, color: cores.textoFraco, letterSpacing: "0.03em" };
const td: React.CSSProperties = { padding: `9px ${espaco.lg}px`, fontSize: "0.84rem", fontVariantNumeric: "tabular-nums" };
const selectEstilo: React.CSSProperties = { background: cores.bgCartao, color: cores.texto, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, padding: "5px 8px", fontSize: "0.8rem", cursor: "pointer" };
