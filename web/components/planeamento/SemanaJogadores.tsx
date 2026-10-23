"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Cartao, SecaoTitulo, EstadoVazio } from "@/components/ui/base";
import { Carregando } from "@/components/ui/Esqueleto";
import { pedidoApi } from "@/lib/api-cliente";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { cores, espaco, raio } from "@/lib/theme";
import { useTr } from "@/lib/i18n/cliente";

type Valor = { alvo: number | null; feito: number | null; pct: number | null; falta: number | null; por_sessao: number | null; estado: "atras" | "ok" | "frente" | null };
type Metrica = { chave: string; label: string; unidade: string; fator?: number };
interface Resposta {
  hoje: string;
  microciclos: number[];
  objetivo: null | {
    microciclo: number; nome: string | null; inicio: string; fim: string; tem_fatores: boolean;
    metricas: Metrica[]; sessoes_feitas: string[]; sessoes_restantes: string[]; esperado_pct: number | null;
    jogadores: { jogador: string; posicao: string; sessoes: number; valores: Record<string, Valor> }[];
  };
  compensacao: null | {
    data: string; duracao_min: number; dias_desde: number; minimo_pct: number; metricas: Metrica[];
    jogadores: { jogador: string; posicao: string; minutos: number; pct_minutos: number; falta: Record<string, number>; compensado_pct: Record<string, number | null> }[];
  };
}

const COR_ESTADO = { atras: cores.atencao, ok: cores.sucesso, frente: cores.info };

/** Semana por jogador: objetivo semanal (feito, falta, por sessão) e
 * compensação pós-jogo para quem jogou pouco. */
export function SemanaJogadores({ teamId }: { teamId: string }) {
  const tr = useTr();
  const { oculto } = usePrivacidade();
  const [mc, setMc] = useState<number | null>(null);
  const [d, setD] = useState<Resposta | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [ordem, setOrdem] = useState<string>("nome");

  useEffect(() => {
    pedidoApi<Resposta>(`/api/teams/${teamId}/semana-jogadores${mc != null ? `?microciclo=${mc}` : ""}`)
      .then((r) => { setD(r); setErro(null); })
      .catch((e) => setErro(e instanceof Error ? e.message : "Erro"));
  }, [teamId, mc]);

  if (erro) return <EstadoVazio mensagem={erro} />;
  if (!d) return <Carregando cartoes={0} linhas={8} padding={false} />;
  const o = d.objetivo, c = d.compensacao;
  const n = (v: number | null | undefined) => (v == null ? "—" : Math.round(v).toLocaleString(tr.loc));
  const dataCurta = (iso: string) => new Date(`${iso}T12:00:00`).toLocaleDateString(tr.loc, { weekday: "short", day: "numeric", month: "short" });

  const jogadores = o ? [...o.jogadores].sort((a, b) => {
    if (ordem === "nome") return a.jogador.localeCompare(b.jogador);
    return (a.valores[ordem]?.pct ?? 999) - (b.valores[ordem]?.pct ?? 999);
  }) : [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: espaco.xxl }}>
      {/* ── Compensação pós-jogo ── */}
      <section>
        <SecaoTitulo
          subtitulo={c ? tr("Jogo de {0} ({1} min). Jogadores com menos de {2}% dos minutos e o que lhes faltou face a um jogo completo (a referência de jogo de cada um, por 90').", [dataCurta(c.data), c.duracao_min, c.minimo_pct]) : undefined}
          ajuda={<>{tr("Falta = referência de jogo do jogador (média por 90' dos últimos jogos completos, ajustada à duração deste jogo) − o que fez no jogo. «Já compensado» soma o que fez em treino depois do jogo. É uma referência para o treino compensatório, não uma prescrição.")}</>}>
          {tr("Compensação pós-jogo")}</SecaoTitulo>
        {!c ? <EstadoVazio mensagem={tr("Ainda não há jogos registados no GPS.")} /> : c.jogadores.length === 0 ? (
          <Cartao><span style={{ fontSize: "0.85rem", color: cores.texto }}>{tr("Todos os jogadores disponíveis jogaram pelo menos {0}% dos minutos — ninguém precisa de compensação.", [c.minimo_pct])}</span></Cartao>
        ) : (
          <Cartao padding={0}>
            <div style={{ overflowX: "auto" }}>
              <table style={tabela}>
                <thead><tr>
                  <th style={{ ...th, textAlign: "left" }}>{tr("Jogador")}</th>
                  <th style={th}>{tr("Minutos")}</th>
                  {c.metricas.map((m) => <th key={m.chave} style={th}>{tr("{0} em falta", [tr(m.label)])} <span style={{ fontWeight: 400 }}>{m.unidade}</span></th>)}
                </tr></thead>
                <tbody>
                  {c.jogadores.map((j) => (
                    <tr key={j.jogador} style={{ borderTop: `1px solid ${cores.borda}` }}>
                      <td style={{ ...td, textAlign: "left", fontWeight: 600, color: cores.textoForte, whiteSpace: "nowrap" }}>
                        <Link href={`/jogadores?jogador=${encodeURIComponent(j.jogador)}`} style={{ color: "inherit", textDecoration: "none" }}>{nomeOuOculto(j.jogador, oculto)}</Link>
                        {j.posicao !== "—" && <span style={{ color: cores.textoFraco, fontWeight: 400, fontSize: "0.74rem" }}> · {j.posicao}</span>}
                      </td>
                      <td style={td}>{j.minutos ? `${n(j.minutos)}'` : <span style={{ color: cores.atencao }}>{tr("não jogou")}</span>}</td>
                      {c.metricas.map((m) => {
                        const f = j.falta[m.chave], comp = j.compensado_pct[m.chave];
                        return (
                          <td key={m.chave} style={td}>
                            <div style={{ fontWeight: 650, color: cores.textoForte }}>{n(f)}</div>
                            {comp != null && comp > 0 && <div style={{ fontSize: "0.68rem", color: comp >= 80 ? cores.sucesso : cores.textoSuave }}>{tr("{0}% já compensado", [comp])}</div>}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Cartao>
        )}
      </section>

      {/* ── Objetivo semanal ── */}
      <section>
        <SecaoTitulo
          subtitulo={o ? tr("MC {0} · {1} – {2} · {3} sessão(ões) feita(s), {4} por fazer · esperado até agora ≈ {5}% do objetivo", [o.microciclo, dataCurta(o.inicio), dataCurta(o.fim), o.sessoes_feitas.length, o.sessoes_restantes.length, o.esperado_pct ?? "—"]) : undefined}
          ajuda={<>{tr("Objetivo de cada jogador = fator semanal do microciclo × a referência de jogo DESSE jogador (por 90'). Conta só treinos. «Por sessão» = o que falta ÷ treinos que ainda restam no plano. Laranja = mais de 20 pontos abaixo do esperado; azul = mais de 20 acima.")}</>}
          acoes={d.microciclos.length > 0 && (
            <select value={mc ?? o?.microciclo ?? ""} onChange={(e) => setMc(Number(e.target.value))} style={campo} aria-label={tr("Microciclo")}>
              {d.microciclos.map((m) => <option key={m} value={m}>MC {m}</option>)}
            </select>
          )}>
          {tr("Objetivo da semana por jogador")}</SecaoTitulo>
        {!o ? <EstadoVazio acao={{ href: "/planeamento", label: tr("Abrir Microciclos") }} mensagem={tr("Não há microciclo para esta semana. Cria-o no Planeamento com os fatores semanais.")} />
          : !o.tem_fatores || o.metricas.length === 0 ? <EstadoVazio acao={{ href: "/planeamento", label: tr("Abrir Microciclos") }} mensagem={tr("O MC {0} ainda não tem fatores semanais (× jogo) definidos.", [o.microciclo])} />
          : (
            <Cartao padding={0}>
              <div style={{ overflowX: "auto" }}>
                <table style={tabela}>
                  <thead><tr>
                    <th style={{ ...th, textAlign: "left", cursor: "pointer" }} onClick={() => setOrdem("nome")}>{tr("Jogador")}{ordem === "nome" ? " ↓" : ""}</th>
                    {o.metricas.map((m) => (
                      <th key={m.chave} style={{ ...th, cursor: "pointer" }} onClick={() => setOrdem(m.chave)} title={tr("Ordenar por quem está mais atrás")}>
                        {tr(m.label)} <span style={{ fontWeight: 400 }}>{m.fator}× · {m.unidade}</span>{ordem === m.chave ? " ↑" : ""}
                      </th>
                    ))}
                  </tr></thead>
                  <tbody>
                    {jogadores.map((j) => (
                      <tr key={j.jogador} style={{ borderTop: `1px solid ${cores.borda}` }}>
                        <td style={{ ...td, textAlign: "left", fontWeight: 600, color: cores.textoForte, whiteSpace: "nowrap" }}>
                          {nomeOuOculto(j.jogador, oculto)}
                          <span style={{ color: cores.textoFraco, fontWeight: 400, fontSize: "0.74rem" }}> · {tr("{0} treino(s)", [j.sessoes])}</span>
                        </td>
                        {o.metricas.map((m) => {
                          const v = j.valores[m.chave];
                          const cor = v?.estado ? COR_ESTADO[v.estado] : cores.textoFraco;
                          return (
                            <td key={m.chave} style={td} title={v?.alvo != null ? tr("Feito {0} de {1} · falta {2}", [n(v.feito), n(v.alvo), n(v.falta)]) : tr("sem referência de jogo")}>
                              <div style={{ display: "flex", alignItems: "center", gap: 6, justifyContent: "flex-end" }}>
                                <div style={{ width: 54, height: 6, borderRadius: 3, background: cores.superficie, overflow: "hidden" }}>
                                  <div style={{ width: `${Math.min(v?.pct ?? 0, 100)}%`, height: "100%", background: cor }} />
                                </div>
                                <span style={{ fontWeight: 650, color: cor, minWidth: 40 }}>{v?.pct != null ? `${v.pct}%` : "—"}</span>
                              </div>
                              {v?.por_sessao != null && v.por_sessao > 0 && (
                                <div style={{ fontSize: "0.68rem", color: cores.textoSuave }}>{tr("+{0}/sessão", [n(v.por_sessao)])}</div>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Cartao>
          )}
      </section>
    </div>
  );
}

const tabela: React.CSSProperties = { width: "100%", borderCollapse: "collapse", fontVariantNumeric: "tabular-nums", minWidth: 640 };
const th: React.CSSProperties = { padding: "9px 12px", fontSize: "0.68rem", color: cores.textoSuave, fontWeight: 600, textAlign: "right", whiteSpace: "nowrap" };
const td: React.CSSProperties = { padding: "8px 12px", fontSize: "0.84rem", color: cores.texto, textAlign: "right", verticalAlign: "top" };
const campo: React.CSSProperties = { background: cores.bgCartao, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: cores.textoForte, fontSize: "0.8rem", padding: "4px 8px", height: 30 };
