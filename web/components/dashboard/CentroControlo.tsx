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
const N_ALERTAS = 8;

export function CentroControlo(p: CentroControloProps) {
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
            subtitulo={p.sessaoRecente ? `Sessão de ${new Date(p.sessaoRecente).toLocaleDateString("pt-PT", { day: "numeric", month: "long" })} face à média dos últimos 28 dias` : undefined}
            acoes={<button onClick={() => p.navegar("/carga-externa")} style={estiloBotao.ligacao}>Ver detalhe</button>}
          >
            Carga externa da equipa
          </SecaoTitulo>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: espaco.md }}>
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
  const itens = [
    { k: "normal" as const, label: "Normal", n: s.normal },
    { k: "attention" as const, label: "Atenção", n: s.attention },
    { k: "high-attention" as const, label: "Atenção alta", n: s.highAttention },
  ];
  return (
    <Cartao padding={0}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)" }}>
        {itens.map((it, i) => (
          <div key={it.k} style={{ padding: `${espaco.md}px ${espaco.lg}px`, borderLeft: i ? `1px solid ${cores.borda}` : "none" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 7, fontSize: "0.76rem", color: cores.textoSuave }}>
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: COR_STATUS[it.k] }} />
              {it.label}
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

// ── Quem precisa de atenção: lista compacta ──────────────────────────────────
function PrecisamAtencao({ alertas, navegar }: { alertas: Alerta[]; navegar: (r: string) => void }) {
  const [todos, setTodos] = useState(false);
  const lista = todos ? alertas : alertas.slice(0, N_ALERTAS);
  return (
    <section>
      <SecaoTitulo subtitulo={alertas.length ? `${alertas.length} atleta(s) com sinais de ACWR, velocidade ou exposição` : undefined}>
        Precisam de atenção
      </SecaoTitulo>
      {alertas.length === 0 ? (
        <Vazio>Ninguém precisa de atenção especial neste momento.</Vazio>
      ) : (
        <Cartao padding={0}>
          {lista.map((a, i) => (
            <button
              key={a.player_id}
              onClick={() => navegar(`/jogadores?nome=${encodeURIComponent(a.player_name)}`)}
              className="lm-linha"
              style={{
                display: "grid", gridTemplateColumns: "10px minmax(0, 1fr) auto", alignItems: "center", gap: espaco.md, width: "100%",
                padding: `10px ${espaco.lg}px`, border: "none", borderTop: i ? `1px solid ${cores.borda}` : "none",
                background: "transparent", cursor: "pointer", textAlign: "left", color: cores.texto,
              }}
            >
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: COR_STATUS[a.status] }} />
              <span style={{ minWidth: 0 }}>
                <span style={{ display: "block", fontSize: "0.86rem", fontWeight: 600, color: cores.textoForte }}><NomeJogador nome={a.player_name} /></span>
                <span style={{ display: "block", fontSize: "0.76rem", color: cores.textoSuave, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {a.reason_text} · {a.metric_value}
                </span>
              </span>
              <span style={{ color: cores.textoFraco, fontSize: "0.9rem" }}>›</span>
            </button>
          ))}
          {alertas.length > N_ALERTAS && (
            <div style={{ borderTop: `1px solid ${cores.borda}`, padding: `8px ${espaco.lg}px` }}>
              <button onClick={() => setTodos(!todos)} style={estiloBotao.ligacao}>{todos ? "Mostrar menos" : `Ver todos (${alertas.length})`}</button>
            </div>
          )}
        </Cartao>
      )}
    </section>
  );
}

// ── Planeado vs realizado: tabela curta ──────────────────────────────────────
function fmt(v: number | null, unidade: string): string {
  if (v == null) return "—";
  const n = unidade === "" ? v.toLocaleString("pt-PT", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) : Math.round(v).toLocaleString("pt-PT");
  return unidade ? `${n} ${unidade}` : n;
}

function PlaneadoVsRealizado({ dados, navegar }: { dados: PlaneadoRealizado | null; navegar: (r: string) => void }) {
  const data = dados?.data ? new Date(`${dados.data}T00:00:00`).toLocaleDateString("pt-PT", { weekday: "long", day: "numeric", month: "short" }) : "";
  const contexto = [data, dados?.dia_md, dados?.microciclo != null ? `microciclo ${dados.microciclo}` : null].filter(Boolean).join(" · ");
  return (
    <section>
      <SecaoTitulo
        subtitulo={dados?.tem_dados ? `Último treino: ${contexto}` : undefined}
        acoes={<button onClick={() => navegar("/planeamento")} style={estiloBotao.ligacao}>{dados?.tem_plano ? "Planeamento" : "Planear"}</button>}
      >
        Planeado vs realizado
      </SecaoTitulo>
      {!dados?.tem_dados ? (
        <Vazio>{dados?.motivo ?? "Ainda não há sessões de treino."}</Vazio>
      ) : (
        <Cartao padding={0}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {["", "Planeado", "Realizado", "Desvio"].map((h, i) => (
                  <th key={i} style={{ ...th, textAlign: i ? "right" : "left" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(dados.metricas ?? []).map((m) => {
                const cor = COR_PLANO[m.estado];
                return (
                  <tr key={m.chave} style={{ borderTop: `1px solid ${cores.borda}` }}>
                    <td style={{ ...td, color: cores.textoForte, fontWeight: 600 }}>{m.label}</td>
                    <td style={{ ...td, textAlign: "right", color: cores.textoSuave }}>{fmt(m.planeado, m.unidade)}</td>
                    <td style={{ ...td, textAlign: "right", color: cores.textoForte }}>{fmt(m.real, m.unidade)}</td>
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
                "Sem valores planeados para este dia — define-os no Planeamento para ver o desvio."
              ) : (
                <>
                  HSR mais afastado do plano:{" "}
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

function dica(j: JogadorExposicao, label: string): string | undefined {
  const partes: string[] = [];
  if (j.acumulado != null && j.referencia != null) partes.push(`${label}: ${Math.round(j.acumulado)} m acumulados ÷ ${Math.round(j.referencia)} m de referência`);
  if (j.fonte_referencia) partes.push(`Referência: ${FONTE_LABEL[j.fonte_referencia] ?? j.fonte_referencia}`);
  if (j.n_treinos != null) partes.push(`${j.n_treinos} treino(s) somados`);
  return partes.length ? partes.join("\n") : undefined;
}

function Exposicao({ exposicao, aCarregar, onMicrociclo }: { exposicao: ExposicaoSemana; aCarregar?: boolean; onMicrociclo: (mc: number) => void }) {
  const [chave, setChave] = useState<string | null>(null);
  const metricas = exposicao.metricas ?? [];
  const m = metricas.find((x) => x.chave === chave) ?? metricas[0];
  const seletor = (exposicao.microciclos_disponiveis?.length ?? 0) > 0 && (
    <select aria-label="Microciclo" value={exposicao.microciclo ?? ""} onChange={(e) => onMicrociclo(Number(e.target.value))} disabled={aCarregar} style={selectEstilo}>
      {[...(exposicao.microciclos_disponiveis ?? [])].reverse().map((mc) => <option key={mc} value={mc}>Microciclo {mc}</option>)}
    </select>
  );
  return (
    <section>
      <SecaoTitulo
        subtitulo="Soma dos treinos do microciclo (jogos excluídos) ÷ referência de jogo do jogador (média por 90' dos últimos jogos com ≥ 60'). Passa o rato num jogador para ver o cálculo."
        acoes={<>{aCarregar && <span style={{ fontSize: "0.75rem", color: cores.textoSuave }}>A calcular…</span>}{seletor}</>}
      >
        Exposição da semana vs jogo
      </SecaoTitulo>
      {!exposicao.tem_dados || !m ? (
        <Vazio>{exposicao.motivo ?? "Sem dados de exposição."}</Vazio>
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
                    {x.label}
                  </button>
                );
              })}
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: espaco.sm }}>
              <span style={{ fontSize: "0.76rem", color: cores.textoSuave }}>Equipa</span>
              <span className="font-display" style={{ fontSize: "1.3rem", fontWeight: 600, color: COR_ZONA[m.zona_equipa], fontVariantNumeric: "tabular-nums" }}>{m.ratio_equipa.toFixed(2)}×</span>
              <Etiqueta cor={COR_ZONA[m.zona_equipa]}>{LABEL_ZONA[m.zona_equipa]}</Etiqueta>
              <span style={{ fontSize: "0.74rem", color: cores.textoFraco }}>ref. {m.ref[0].toFixed(2)}–{m.ref[1].toFixed(2)}×</span>
            </div>
          </div>

          {m.posicoes.length > 1 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: `${espaco.sm}px ${espaco.lg}px`, borderBottom: `1px solid ${cores.borda}` }}>
              {m.posicoes.map((pos) => (
                <Etiqueta key={pos.posicao} cor={COR_ZONA[pos.zona]} title={`${pos.n_jogadores} jogador(es)`}>{pos.posicao} {pos.ratio.toFixed(2)}×</Etiqueta>
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
                <div key={j.jogador} title={dica(j, m.label)} style={{ display: "grid", gridTemplateColumns: "minmax(120px, 1.2fr) 1.5fr 78px 44px", alignItems: "center", gap: espaco.sm, fontSize: "0.78rem" }}>
                  <span style={{ color: cores.texto, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    <NomeJogador nome={j.jogador} />{j.posicao && j.posicao !== "—" && <span style={{ color: cores.textoFraco }}> · {j.posicao}</span>}
                  </span>
                  <div style={{ position: "relative", height: 6, background: cores.superficieHover, borderRadius: 3 }}>
                    <div style={{ position: "absolute", top: -2, bottom: -2, left: `${zIni}%`, width: `${zFim - zIni}%`, background: "rgb(34 197 94 / 0.14)", borderRadius: 2 }} />
                    <div style={{ position: "absolute", top: 0, bottom: 0, left: 0, width: `${pct}%`, background: cor, borderRadius: 3 }} />
                  </div>
                  <span style={{ color: cores.textoSuave, textAlign: "right", whiteSpace: "nowrap", fontVariantNumeric: "tabular-nums" }}>{j.em_falta ? `faltam ${Math.round(j.em_falta)} m` : ""}</span>
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
