"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { cores, espaco, raio } from "@/lib/theme";
import { NomeJogador } from "@/components/ui/NomeJogador";

type ChaveMetrica = "pct_distancia" | "pct_hsr" | "pct_sprint" | "pct_vmax";

interface Etapa {
  nome: string;
  pct_distancia: number | null;
  pct_hsr: number | null;
  pct_sprint: number | null;
  pct_vmax: number | null;
}

interface EtapaAvaliada extends Etapa {
  estado: "concluida" | "atual" | "pendente";
  sessoes_cumpridas: number;
  data_conclusao: string | null;
  melhor: Record<ChaveMetrica, number | null>;
}

interface Plano {
  id: string;
  player_id: string;
  jogador: string;
  data_inicio: string;
  sessoes_por_etapa: number;
  estado: "ativo" | "concluido" | "cancelado";
  notas: string | null;
  referencias: Partial<Record<ChaveMetrica, { valor: number; fonte: string }>>;
  sessoes: { data: string; dia_md: string | null; jogo: boolean; pct: Record<ChaveMetrica, number | null>; conta_para_etapa: number | null }[];
  etapas: EtapaAvaliada[];
  etapa_atual: number | null;
  concluido: boolean;
  progresso_pct: number;
}

interface JogadorOpcao {
  player_id: string;
  nome: string;
  estado: string;
  estado_desde: string | null;
}

export interface RtpResponse {
  disponivel: boolean;
  motivo: string | null;
  etapas_padrao: Etapa[];
  sessoes_por_etapa_padrao: number;
  metricas: { chave: ChaveMetrica; label: string }[];
  jogadores: JogadorOpcao[];
  planos: Plano[];
  sugestoes: JogadorOpcao[];
}

const METRICAS: { chave: ChaveMetrica; label: string; unidade: string }[] = [
  { chave: "pct_distancia", label: "Distância", unidade: "m" },
  { chave: "pct_hsr", label: "HSR", unidade: "m" },
  { chave: "pct_sprint", label: "Sprint", unidade: "m" },
  { chave: "pct_vmax", label: "Vel. máx", unidade: "km/h" },
];

const FONTE: Record<string, string> = {
  media_90: "média por 90' pré-lesão",
  posicao: "mediana da posição",
  equipa: "mediana da equipa",
  pico: "pico em jogo",
  recorde: "recorde pré-lesão",
};

const hoje = () => new Date().toISOString().slice(0, 10);

export function RegressoJogo({ teamId, dadosIniciais }: { teamId: string; dadosIniciais: RtpResponse }) {
  const [dados, setDados] = useState(dadosIniciais);
  const [erro, setErro] = useState<string | null>(null);
  const [aGravar, setAGravar] = useState(false);
  const [novo, setNovo] = useState<{ player_id: string; data_inicio: string; sessoes: number; etapas: Etapa[] } | null>(null);
  const [editar, setEditar] = useState<{ id: string; sessoes: number; etapas: Etapa[] } | null>(null);
  const api = `${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/rtp`;

  async function pedido(url: string, metodo: string, corpo?: unknown) {
    const { data: { session } } = await createClient().auth.getSession();
    if (!session) throw new Error("Sessão expirada. Volta a entrar.");
    const res = await fetch(url, {
      method: metodo,
      headers: { Authorization: `Bearer ${session.access_token}`, "Content-Type": "application/json" },
      body: corpo ? JSON.stringify(corpo) : undefined,
    });
    if (!res.ok) {
      const j = await res.json().catch(() => null);
      throw new Error(j?.detail ?? "Não foi possível guardar.");
    }
    return res.json();
  }

  async function executar(acao: () => Promise<unknown>) {
    setErro(null);
    setAGravar(true);
    try {
      await acao();
      setDados(await pedido(api, "GET"));
      setNovo(null);
      setEditar(null);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro inesperado.");
    } finally {
      setAGravar(false);
    }
  }

  function abrirNovo(j?: JogadorOpcao) {
    setNovo({
      player_id: j?.player_id ?? dados.jogadores[0]?.player_id ?? "",
      data_inicio: j?.estado_desde ?? hoje(),
      sessoes: dados.sessoes_por_etapa_padrao,
      etapas: dados.etapas_padrao.map((e) => ({ ...e })),
    });
  }

  if (!dados.disponivel) {
    return <Caixa cor={cores.atencao}>{dados.motivo}</Caixa>;
  }

  const ativos = dados.planos.filter((p) => p.estado === "ativo");
  const concluidos = dados.planos.filter((p) => p.estado === "concluido");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: espaco.xl }}>
      <p style={{ fontSize: "0.8rem", color: cores.textoSuave, margin: 0, maxWidth: 900 }}>
        Cada etapa tem metas por sessão em % da referência de jogo do jogador antes do início do plano (média por 90 minutos dos últimos jogos completos; velocidade máxima = recorde pré-lesão).
        A etapa fica cumprida quando o número definido de sessões atinge todas as metas, e só depois começam a contar sessões para a seguinte. Tudo é avaliado a partir das sessões GPS importadas.
      </p>

      {erro && <Caixa cor={cores.perigo}>{erro}</Caixa>}

      {dados.sugestoes.length > 0 && !novo && (
        <Caixa cor={cores.info}>
          Sem plano de regresso:{" "}
          {dados.sugestoes.map((j, i) => (
            <span key={j.player_id}>
              {i > 0 && " · "}
              <NomeJogador nome={j.nome} /> ({j.estado === "em_recuperacao" ? "em recuperação" : "lesionado"}){" "}
              <button onClick={() => abrirNovo(j)} style={linkBtn}>criar plano</button>
            </span>
          ))}
        </Caixa>
      )}

      {novo ? (
        <div style={cartao}>
          <h3 style={titulo}>Novo plano</h3>
          <div style={{ display: "flex", gap: espaco.md, flexWrap: "wrap", marginBottom: espaco.md }}>
            <label style={rotulo}>Jogador
              <select value={novo.player_id} onChange={(e) => setNovo({ ...novo, player_id: e.target.value })} style={campo}>
                {dados.jogadores.map((j) => <option key={j.player_id} value={j.player_id}>{j.nome}</option>)}
              </select>
            </label>
            <label style={rotulo}>Início do plano
              <input type="date" value={novo.data_inicio} onChange={(e) => setNovo({ ...novo, data_inicio: e.target.value })} style={campo} />
            </label>
            <label style={rotulo}>Sessões por etapa
              <input type="number" min={1} max={10} value={novo.sessoes} onChange={(e) => setNovo({ ...novo, sessoes: Number(e.target.value) })} style={{ ...campo, width: 90 }} />
            </label>
          </div>
          <EditorEtapas etapas={novo.etapas} onChange={(etapas) => setNovo({ ...novo, etapas })} />
          <div style={{ display: "flex", gap: espaco.sm, marginTop: espaco.md }}>
            <button disabled={aGravar || !novo.player_id} style={btnPrimario}
              onClick={() => executar(() => pedido(api, "POST", { player_id: novo.player_id, data_inicio: novo.data_inicio, sessoes_por_etapa: novo.sessoes, etapas: novo.etapas }))}>
              {aGravar ? "A guardar…" : "Criar plano"}
            </button>
            <button onClick={() => setNovo(null)} style={btnSecundario}>Cancelar</button>
          </div>
        </div>
      ) : (
        <div><button onClick={() => abrirNovo()} style={btnPrimario}>+ Novo plano de regresso</button></div>
      )}

      {ativos.length === 0 && !novo && <p style={{ color: cores.textoSuave, fontSize: "0.85rem", margin: 0 }}>Não há planos ativos.</p>}

      {ativos.map((p) => (
        <div key={p.id} style={cartao}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: espaco.md, flexWrap: "wrap" }}>
            <h3 style={{ ...titulo, margin: 0 }}>
              <NomeJogador nome={p.jogador} />
              <span style={{ color: cores.textoSuave, fontWeight: 400, fontSize: "0.82rem" }}>
                {" "}· desde {new Date(`${p.data_inicio}T00:00:00`).toLocaleDateString("pt-PT")} · {p.sessoes_por_etapa} sessões por etapa
              </span>
            </h3>
            <div style={{ display: "flex", gap: espaco.sm }}>
              <button style={btnSecundario} onClick={() => setEditar(editar?.id === p.id ? null : { id: p.id, sessoes: p.sessoes_por_etapa, etapas: p.etapas.map(({ nome, pct_distancia, pct_hsr, pct_sprint, pct_vmax }) => ({ nome, pct_distancia, pct_hsr, pct_sprint, pct_vmax })) })}>
                {editar?.id === p.id ? "Fechar edição" : "Editar etapas"}
              </button>
              <button style={btnSecundario} disabled={aGravar} onClick={() => executar(() => pedido(`${api}/${p.id}`, "PUT", { estado: "concluido" }))}>Marcar como concluído</button>
              <button style={{ ...btnSecundario, color: cores.perigo }} disabled={aGravar}
                onClick={() => { if (confirm("Cancelar este plano? Deixa de aparecer na lista.")) executar(() => pedido(`${api}/${p.id}`, "PUT", { estado: "cancelado" })); }}>
                Cancelar plano
              </button>
            </div>
          </div>

          <div style={{ margin: `${espaco.md}px 0` }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", color: cores.textoSuave, marginBottom: 4 }}>
              <span>{p.concluido ? "Todas as etapas cumpridas — pronto para a decisão de regresso" : `Etapa ${p.etapa_atual} de ${p.etapas.length}`}</span>
              <span style={{ fontVariantNumeric: "tabular-nums" }}>{p.progresso_pct}%</span>
            </div>
            <div style={{ height: 8, background: "rgb(var(--ink) / 0.06)", borderRadius: 4 }}>
              <div style={{ width: `${p.progresso_pct}%`, height: "100%", background: p.concluido ? cores.sucesso : cores.info, borderRadius: 4 }} />
            </div>
          </div>

          {editar?.id === p.id ? (
            <div>
              <label style={{ ...rotulo, marginBottom: espaco.sm }}>Sessões por etapa
                <input type="number" min={1} max={10} value={editar.sessoes} onChange={(e) => setEditar({ ...editar, sessoes: Number(e.target.value) })} style={{ ...campo, width: 90 }} />
              </label>
              <EditorEtapas etapas={editar.etapas} onChange={(etapas) => setEditar({ ...editar, etapas })} />
              <button disabled={aGravar} style={{ ...btnPrimario, marginTop: espaco.md }}
                onClick={() => executar(() => pedido(`${api}/${p.id}`, "PUT", { etapas: editar.etapas, sessoes_por_etapa: editar.sessoes }))}>
                {aGravar ? "A guardar…" : "Guardar etapas"}
              </button>
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: `repeat(${Math.max(1, p.etapas.length)}, minmax(170px, 1fr))`, gap: espaco.sm, overflowX: "auto" }}>
              {p.etapas.map((e, i) => <CartaoEtapa key={i} etapa={e} indice={i} n={p.sessoes_por_etapa} />)}
            </div>
          )}

          <div style={{ fontSize: "0.74rem", color: cores.textoSuave, marginTop: espaco.md }}>
            Referência pré-lesão:{" "}
            {METRICAS.filter((m) => p.referencias[m.chave]).map((m, i) => {
              const r = p.referencias[m.chave]!;
              return <span key={m.chave}>{i > 0 && " · "}{m.label} {Math.round(r.valor).toLocaleString("pt-PT")} {m.unidade} ({FONTE[r.fonte] ?? r.fonte})</span>;
            })}
            {Object.keys(p.referencias).length === 0 && "sem dados de jogo anteriores ao plano — as metas não podem ser avaliadas."}
          </div>

          {p.sessoes.length > 0 && (
            <div style={{ overflowX: "auto", marginTop: espaco.md }}>
              <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 560 }}>
                <thead>
                  <tr>
                    {["Sessão", ...METRICAS.map((m) => `${m.label} %`), "Conta para"].map((h) => <th key={h} style={th}>{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {p.sessoes.map((s) => (
                    <tr key={s.data} style={{ borderTop: `1px solid ${cores.borda}` }}>
                      <td style={td}>{new Date(`${s.data}T00:00:00`).toLocaleDateString("pt-PT", { day: "numeric", month: "short" })}{s.dia_md ? ` · ${s.dia_md}` : ""}{s.jogo ? " · jogo" : ""}</td>
                      {METRICAS.map((m) => <td key={m.chave} style={{ ...td, fontVariantNumeric: "tabular-nums" }}>{s.pct[m.chave] != null ? `${s.pct[m.chave]}%` : "—"}</td>)}
                      <td style={{ ...td, color: s.conta_para_etapa ? cores.sucesso : cores.textoFraco }}>{s.conta_para_etapa ? `Etapa ${s.conta_para_etapa}` : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ))}

      {concluidos.length > 0 && (
        <div>
          <h3 style={titulo}>Concluídos</h3>
          {concluidos.map((p) => (
            <div key={p.id} style={{ fontSize: "0.82rem", color: cores.textoSuave, padding: "4px 0" }}>
              <NomeJogador nome={p.jogador} /> · desde {new Date(`${p.data_inicio}T00:00:00`).toLocaleDateString("pt-PT")} · {p.progresso_pct}% das etapas
              {" "}<button style={linkBtn} disabled={aGravar} onClick={() => executar(() => pedido(`${api}/${p.id}`, "PUT", { estado: "ativo" }))}>reabrir</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CartaoEtapa({ etapa, indice, n }: { etapa: EtapaAvaliada; indice: number; n: number }) {
  const cor = etapa.estado === "concluida" ? cores.sucesso : etapa.estado === "atual" ? cores.info : cores.textoFraco;
  return (
    <div style={{ border: `1px solid ${etapa.estado === "atual" ? cor : cores.borda}`, borderTop: `3px solid ${cor}`, borderRadius: raio.sm, padding: espaco.sm, background: "rgb(var(--ink) / 0.02)" }}>
      <div style={{ fontSize: "0.8rem", fontWeight: 700, color: cores.textoForte }}>{indice + 1}. {etapa.nome}</div>
      <div style={{ fontSize: "0.7rem", fontWeight: 700, color: cor, margin: "2px 0 6px" }}>
        {etapa.estado === "concluida" ? `Cumprida a ${new Date(`${etapa.data_conclusao}T00:00:00`).toLocaleDateString("pt-PT", { day: "numeric", month: "short" })}`
          : etapa.estado === "atual" ? `Em curso · ${etapa.sessoes_cumpridas}/${n} sessões` : "Por começar"}
      </div>
      {METRICAS.filter((m) => etapa[m.chave] != null).map((m) => {
        const melhor = etapa.melhor?.[m.chave];
        const ok = melhor != null && melhor >= (etapa[m.chave] as number);
        return (
          <div key={m.chave} style={{ display: "flex", justifyContent: "space-between", fontSize: "0.74rem", color: cores.textoSuave, fontVariantNumeric: "tabular-nums" }}>
            <span>{m.label} ≥ {etapa[m.chave]}%</span>
            {etapa.estado !== "pendente" && melhor != null && <span style={{ color: ok ? cores.sucesso : cores.texto }}>máx {melhor}%</span>}
          </div>
        );
      })}
    </div>
  );
}

function EditorEtapas({ etapas, onChange }: { etapas: Etapa[]; onChange: (e: Etapa[]) => void }) {
  const alterar = (i: number, campoNome: keyof Etapa, valor: string) => {
    const novas = etapas.map((e, k) => (k !== i ? e : {
      ...e,
      [campoNome]: campoNome === "nome" ? valor : valor === "" ? null : Number(valor),
    }));
    onChange(novas);
  };
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ borderCollapse: "collapse", minWidth: 560 }}>
        <thead>
          <tr>
            <th style={th}>Etapa</th>
            {METRICAS.map((m) => <th key={m.chave} style={th}>{m.label} ≥ %</th>)}
            <th style={th} />
          </tr>
        </thead>
        <tbody>
          {etapas.map((e, i) => (
            <tr key={i}>
              <td style={td}><input value={e.nome} onChange={(ev) => alterar(i, "nome", ev.target.value)} style={{ ...campo, width: 150 }} /></td>
              {METRICAS.map((m) => (
                <td key={m.chave} style={td}>
                  <input type="number" min={0} max={200} placeholder="—" value={e[m.chave] ?? ""} onChange={(ev) => alterar(i, m.chave, ev.target.value)} style={{ ...campo, width: 72 }} />
                </td>
              ))}
              <td style={td}>
                <button style={linkBtn} onClick={() => onChange(etapas.filter((_, k) => k !== i))} disabled={etapas.length <= 1}>remover</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button style={{ ...linkBtn, marginTop: 6 }} onClick={() => onChange([...etapas, { nome: `Etapa ${etapas.length + 1}`, pct_distancia: null, pct_hsr: null, pct_sprint: null, pct_vmax: null }])}>
        + adicionar etapa
      </button>
      <div style={{ fontSize: "0.72rem", color: cores.textoSuave, marginTop: 4 }}>Deixa em branco as métricas que não contam para uma etapa.</div>
    </div>
  );
}

function Caixa({ cor, children }: { cor: string; children: React.ReactNode }) {
  return (
    <div style={{ background: `color-mix(in srgb, ${cor} 10%, transparent)`, border: `1px solid color-mix(in srgb, ${cor} 35%, transparent)`, borderRadius: raio.md, padding: espaco.md, fontSize: "0.84rem", color: cores.texto }}>
      {children}
    </div>
  );
}

const cartao: React.CSSProperties = { background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.lg };
const titulo: React.CSSProperties = { fontSize: "0.98rem", fontWeight: 700, color: cores.textoForte, margin: `0 0 ${espaco.md}px` };
const rotulo: React.CSSProperties = { display: "flex", flexDirection: "column", gap: 4, fontSize: "0.72rem", color: cores.textoSuave, fontWeight: 600 };
const campo: React.CSSProperties = { background: cores.bg, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: cores.textoForte, fontSize: "0.84rem", padding: "6px 8px" };
const btnPrimario: React.CSSProperties = { background: cores.info, color: "white", border: "none", borderRadius: raio.sm, padding: "8px 14px", fontSize: "0.84rem", fontWeight: 700, cursor: "pointer" };
const btnSecundario: React.CSSProperties = { background: "rgb(var(--ink) / 0.04)", color: cores.texto, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, padding: "6px 12px", fontSize: "0.8rem", fontWeight: 600, cursor: "pointer" };
const linkBtn: React.CSSProperties = { background: "none", border: "none", color: cores.info, cursor: "pointer", fontSize: "0.8rem", fontWeight: 600, padding: 0 };
const th: React.CSSProperties = { textAlign: "left", padding: "6px 8px", fontSize: "0.62rem", letterSpacing: "0.06em", textTransform: "uppercase", color: cores.textoSuave, fontWeight: 600 };
const td: React.CSSProperties = { padding: "6px 8px", fontSize: "0.8rem", color: cores.texto };
