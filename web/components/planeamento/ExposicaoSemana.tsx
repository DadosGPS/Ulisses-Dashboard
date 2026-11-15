"use client";

import { useCallback, useEffect, useState } from "react";
import { cores, espaco, estado, raio } from "@/lib/theme";
import { Cartao, Etiqueta, SecaoTitulo, Vazio } from "@/components/ui/base";
import { NomeJogador } from "@/components/ui/NomeJogador";
import { pedidoApi } from "@/lib/api-cliente";
import { useTr } from "@/lib/i18n/cliente";
import type { Tr } from "@/lib/i18n/core";

/** Exposição da semana vs jogo (HSR / Sprint acumulados ÷ referência de jogo
 * de cada jogador). Vivia no antigo Centro de Controlo; agora está na Semana. */
export interface JogadorExposicao {
  jogador: string;
  posicao: string;
  ratio: number;
  zona: "baixo" | "ok" | "alto";
  n_treinos?: number;
  acumulado?: number;
  referencia?: number;
  fonte_referencia?: "media_jogo" | "media_90" | "posicao" | "equipa" | "pico";
  em_falta?: number;
}

export interface MetricaExposicao {
  chave: string;
  label: string;
  ref: [number, number];
  ref_ate_hoje?: [number, number];
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
  progresso?: { fracao: number; treinos_feitos: number | null; treinos_tipicos: number | null; completo: boolean };
  metricas: MetricaExposicao[];
}


// Exposição baixa pede ação (falta estímulo); elevada é para vigiar.
const COR_ZONA: Record<string, string> = { baixo: estado.agir, ok: estado.ok, alto: estado.vigiar };
const LABEL_ZONA: Record<string, string> = { baixo: "Exposição baixa", ok: "Na referência", alto: "Exposição elevada" };

/** Carrega e mostra a exposição do microciclo atual (com seletor de microciclo). */
export function ExposicaoSemanaPainel({ teamId }: { teamId: string }) {
  const [dados, setDados] = useState<ExposicaoSemana | null>(null);
  const [aCarregar, setACarregar] = useState(false);
  const carregar = useCallback(async (mc?: number) => {
    setACarregar(true);
    try {
      setDados(await pedidoApi<ExposicaoSemana>(`/api/teams/${teamId}/dashboard/exposicao-semana${mc ? `?microciclo=${mc}` : ""}`));
    } catch {
      setDados({ tem_dados: false, motivo: null, microciclo: null, metricas: [] });
    } finally {
      setACarregar(false);
    }
  }, [teamId]);
  useEffect(() => { carregar(); }, [carregar]);
  if (!dados) return null;
  return <Exposicao exposicao={dados} aCarregar={aCarregar} onMicrociclo={(mc) => carregar(mc)} />;
}

// ── Exposição da semana: um cartão, separadores HSR / Sprint ────────────────
const FONTE_LABEL: Record<string, string> = {
  media_jogo: "média por jogo completo dos últimos jogos completos",
  posicao: "sem jogos completos — mediana da posição",
  equipa: "sem jogos completos — mediana da equipa",
  pico: "pico em jogo (jogos sem minutos registados)",
};

function dica(j: JogadorExposicao, label: string, tr: Tr): string | undefined {
  const partes: string[] = [];
  if (j.acumulado != null && j.referencia != null) partes.push(tr("{0}: {1} m acumulados ÷ {2} m de referência", [label, Math.round(j.acumulado), Math.round(j.referencia)]));
  if (j.fonte_referencia) partes.push(tr("Referência: {0}", [tr(FONTE_LABEL[j.fonte_referencia] ?? j.fonte_referencia)]));
  if (j.n_treinos != null) partes.push(tr("{0} treino(s) somados", [j.n_treinos]));
  return partes.length ? partes.join("\n") : undefined;
}

export function Exposicao({ exposicao, aCarregar, onMicrociclo }: { exposicao: ExposicaoSemana; aCarregar?: boolean; onMicrociclo: (mc: number) => void }) {
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
        ajuda={tr("Soma dos treinos do microciclo (jogos excluídos) ÷ referência de jogo do jogador (média por jogo completo da equipa dos últimos jogos com ≥ 75 % dos minutos). Passa o rato num jogador para ver o cálculo.")}
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
            {exposicao.progresso && !exposicao.progresso.completo && m.ref_ate_hoje && (
              <span style={{ fontSize: "0.74rem", color: cores.textoFraco }}>
                {tr("Semana em curso: {0} de ~{1} treinos — mínimo até hoje {2}×", [exposicao.progresso.treinos_feitos ?? 0, exposicao.progresso.treinos_tipicos ?? "?", m.ref_ate_hoje[0].toFixed(2)])}
              </span>
            )}
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

const selectEstilo: React.CSSProperties = { background: cores.bgCartao, color: cores.texto, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, padding: "5px 8px", fontSize: "0.8rem", cursor: "pointer" };
