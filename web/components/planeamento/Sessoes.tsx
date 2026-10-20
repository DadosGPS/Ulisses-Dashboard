"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { pedidoApi } from "@/lib/api-cliente";
import { cores, espaco, raio } from "@/lib/theme";
import { Cartao, Etiqueta, SecaoTitulo, Vazio, estiloBotao } from "@/components/ui/base";
import { COR_PERFIL, dataCurta, fmtFator, type DiaSessao, type ListaMicrociclos, type Plano, type SessoesMicrociclo } from "./tipos";

const DIAS_SEMANA = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
const OPCOES_MD = ["MD-6", "MD-5", "MD-4", "MD-3", "MD-2", "MD-1", "MD", "MD+1", "MD+2", "MD+3"];
const CARGA: { chave: keyof Plano; fator: string; label: string; unidade: string }[] = [
  { chave: "distancia_m", fator: "distancia", label: "Distância", unidade: "m" },
  { chave: "hsr_m", fator: "hsr", label: "HSR", unidade: "m" },
  { chave: "sprint_m", fator: "sprint", label: "Sprint", unidade: "m" },
];

type Linha = Omit<DiaSessao, "planeado"> & { planeado: Record<keyof Plano, string> };

function mdRelativo(dia: string, jogo: string) {
  const d = Math.round((new Date(`${dia}T00:00:00`).getTime() - new Date(`${jogo}T00:00:00`).getTime()) / 86400000);
  return d === 0 ? "MD" : `MD${d > 0 ? "+" : ""}${d}`;
}

const n = (v: string) => (v.trim() === "" ? null : Number(v.replace(",", ".")));
const txt = (v: number | null | undefined) => (v == null ? "" : String(v));
const fmt = (v: number | null | undefined, casas = 0) => (v == null ? "—" : v.toLocaleString("pt-PT", { maximumFractionDigits: casas }));

/** Separador Sessões: plano dia a dia do microciclo escolhido, com o real ao lado. */
export function Sessoes({ teamId }: { teamId: string }) {
  const router = useRouter();
  const params = useSearchParams();
  const mcParam = params.get("mc");
  const [lista, setLista] = useState<ListaMicrociclos | null>(null);
  const [dados, setDados] = useState<SessoesMicrociclo | null>(null);
  const [linhas, setLinhas] = useState<Linha[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);
  const [aGravar, setAGravar] = useState(false);

  useEffect(() => {
    pedidoApi<ListaMicrociclos>(`/api/teams/${teamId}/microciclos`).then(setLista).catch((e) => setErro(e.message));
  }, [teamId]);

  const mcs = lista?.microciclos ?? [];
  const atual = useMemo(() => {
    if (!mcs.length) return null;
    const hoje = new Date().toISOString().slice(0, 10);
    return mcs.find((m) => String(m.numero) === mcParam)
      ?? mcs.find((m) => m.data_inicio <= hoje && hoje <= m.data_fim) ?? mcs[mcs.length - 1];
  }, [mcs, mcParam]);
  const idx = atual ? mcs.findIndex((m) => m.id === atual.id) : -1;

  async function carregar(id: string) {
    try {
      const d = await pedidoApi<SessoesMicrociclo>(`/api/teams/${teamId}/microciclos/${id}/sessoes`);
      setDados(d);
      setLinhas(d.dias.map((x) => ({ ...x, planeado: Object.fromEntries(Object.entries(x.planeado).map(([k, v]) => [k, txt(v)])) as Linha["planeado"] })));
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro inesperado.");
    }
  }
  useEffect(() => {
    if (atual) carregar(atual.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [atual?.id]);

  function irPara(numero: number) {
    const q = new URLSearchParams(params.toString());
    q.set("mc", String(numero));
    setAviso(null);
    router.replace(`/planeamento/sessoes?${q.toString()}`, { scroll: false });
  }

  function alterar(i: number, mud: Partial<Linha>) {
    setLinhas((ls) => ls.map((l, j) => (j === i ? { ...l, ...mud } : l)));
  }

  function definirJogo(data: string) {
    setLinhas((ls) => ls.map((l) => {
      if (!data) return l;
      const md = mdRelativo(l.data, data);
      if (l.data === data) return { ...l, tipo: "Jogo", dia_md: "MD" };
      return { ...l, dia_md: l.tipo === "Folga" ? null : md, tipo: l.tipo === "Jogo" ? "Treino" : l.tipo };
    }));
  }

  if (erro) return <Vazio>{erro}</Vazio>;
  if (!lista) return <p style={{ color: cores.textoSuave, fontSize: "0.88rem" }}>A carregar…</p>;
  if (!lista.disponivel) return <Vazio>{lista.motivo}</Vazio>;
  if (!atual) return <Vazio>Ainda não há microciclos. Cria-os primeiro no separador <Link href="/planeamento" style={{ color: cores.textoForte }}>Microciclos</Link>.</Vazio>;

  const ref = dados?.referencia ?? {};
  const treinos = linhas.filter((l) => l.tipo === "Treino");
  const soma = (k: keyof Plano) => treinos.reduce((s, l) => s + (n(l.planeado[k]) ?? 0), 0);
  const uaTotal = treinos.reduce((s, l) => s + (n(l.planeado.pse) ?? 0) * (n(l.planeado.duracao_min) ?? 0), 0);
  const jogo = linhas.find((l) => l.tipo === "Jogo")?.data ?? "";
  const cor = (atual.perfil && COR_PERFIL[atual.perfil]) || cores.bordaForte;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: espaco.lg }}>
      {/* Seletor de microciclo */}
      <div style={{ display: "flex", gap: espaco.sm, alignItems: "center", flexWrap: "wrap" }}>
        <button style={estiloBotao.secundario} disabled={idx <= 0} onClick={() => irPara(mcs[idx - 1].numero)} aria-label="Microciclo anterior">‹</button>
        <select value={atual.numero} onChange={(e) => irPara(Number(e.target.value))} style={{ ...campo, flex: "1 1 280px", height: 34 }}>
          {mcs.map((m) => <option key={m.id} value={m.numero}>MC {String(m.numero).padStart(2, "0")} · {dataCurta(m.data_inicio)} → {dataCurta(m.data_fim)} · {m.tipo}{m.perfil ? ` · ${m.perfil}` : ""}</option>)}
        </select>
        <button style={estiloBotao.secundario} disabled={idx >= mcs.length - 1} onClick={() => irPara(mcs[idx + 1].numero)} aria-label="Microciclo seguinte">›</button>
        <Link href={`/planeamento?mc=${atual.numero}`} style={{ ...estiloBotao.secundario, textDecoration: "none" }}>Editar microciclo</Link>
      </div>

      {/* Resumo + alvo semanal */}
      <Cartao destaque={cor}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: espaco.md, flexWrap: "wrap", alignItems: "flex-start" }}>
          <div>
            <div style={{ fontWeight: 700, color: cores.textoForte }}>MC {String(atual.numero).padStart(2, "0")} · {dataCurta(atual.data_inicio)} → {dataCurta(atual.data_fim)}</div>
            <div style={{ display: "flex", gap: 6, marginTop: 4, flexWrap: "wrap" }}>
              <Etiqueta cor={cores.textoSuave}>{atual.tipo}</Etiqueta>
              {atual.perfil && <Etiqueta cor={cor}>{atual.perfil}</Etiqueta>}
              {atual.fase && <Etiqueta cor={cores.textoSuave}>{atual.fase}</Etiqueta>}
            </div>
          </div>
          <Campo rotulo="Dia do jogo (preenche os dias MD)">
            <select value={jogo} onChange={(e) => definirJogo(e.target.value)} style={campo}>
              <option value="">—</option>
              {linhas.map((l) => <option key={l.data} value={l.data}>{DIAS_SEMANA[new Date(`${l.data}T00:00:00`).getDay()]} {dataCurta(l.data).slice(0, 5)}</option>)}
            </select>
          </Campo>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: espaco.md, marginTop: espaco.md }}>
          {CARGA.map((c) => {
            const alvoF = atual.fatores[c.fator];
            const r = ref[c.fator];
            const planeadoF = r ? soma(c.chave) / r : null;
            const realF = dados?.reais?.[c.fator];
            return (
              <div key={c.chave} style={{ background: cores.superficie, borderRadius: raio.sm, padding: espaco.sm }}>
                <div style={{ fontSize: "0.66rem", color: cores.textoFraco, textTransform: "uppercase", letterSpacing: "0.05em" }}>{c.label} da semana</div>
                <div style={{ fontSize: "0.92rem", color: cores.textoForte, fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
                  {fmt(soma(c.chave))} {c.unidade} <span style={{ color: cores.textoSuave, fontWeight: 400 }}>{fmtFator(planeadoF == null ? null : Math.round(planeadoF * 100) / 100)}</span>
                </div>
                <div style={{ fontSize: "0.72rem", color: cores.textoSuave }}>
                  alvo {fmtFator(alvoF)}{alvoF && r ? ` = ${fmt(alvoF * r)} ${c.unidade}` : ""} · real {fmtFator(realF)}
                </div>
              </div>
            );
          })}
          <div style={{ background: cores.superficie, borderRadius: raio.sm, padding: espaco.sm }}>
            <div style={{ fontSize: "0.66rem", color: cores.textoFraco, textTransform: "uppercase", letterSpacing: "0.05em" }}>Carga interna planeada</div>
            <div style={{ fontSize: "0.92rem", color: cores.textoForte, fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>{fmt(uaTotal)} UA</div>
            <div style={{ fontSize: "0.72rem", color: cores.textoSuave }}>{treinos.length} treinos · PSE × minutos</div>
          </div>
        </div>
      </Cartao>

      {/* Plano dia a dia */}
      <section>
        <SecaoTitulo subtitulo="Escolhe o tipo de cada dia e planeia os treinos. Os valores são por jogador; por baixo aparece o real (média da equipa nesse dia).">
          Sessões do microciclo
        </SecaoTitulo>
        {!dados ? <p style={{ color: cores.textoSuave, fontSize: "0.85rem" }}>A carregar…</p> : (
          <Cartao padding={0}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 980 }}>
                <thead>
                  <tr>{["Dia", "Tipo", "Dia MD", "Objetivo", "PSE", "Min", "UA", "Distância (m)", "HSR (m)", "Sprint (m)"].map((h) => <th key={h} style={th}>{h}</th>)}</tr>
                </thead>
                <tbody>
                  {linhas.map((l, i) => {
                    const dia = new Date(`${l.data}T00:00:00`);
                    const treino = l.tipo === "Treino";
                    const ua = (n(l.planeado.pse) ?? 0) * (n(l.planeado.duracao_min) ?? 0);
                    const hoje = l.data === new Date().toISOString().slice(0, 10);
                    return (
                      <tr key={l.data} style={{ borderTop: `1px solid ${cores.borda}`, background: l.tipo === "Jogo" ? "rgba(239,68,68,0.06)" : l.tipo === "Folga" ? cores.superficie : undefined }}>
                        <td style={{ ...td, whiteSpace: "nowrap" }}>
                          <div style={{ fontWeight: 600, color: hoje ? cores.acento : cores.textoForte }}>{DIAS_SEMANA[dia.getDay()]}</div>
                          <div style={{ fontSize: "0.72rem", color: cores.textoSuave }}>{dataCurta(l.data).slice(0, 5)}</div>
                        </td>
                        <td style={td}>
                          <select value={l.tipo} onChange={(e) => alterar(i, { tipo: e.target.value as Linha["tipo"], dia_md: e.target.value === "Folga" ? null : e.target.value === "Jogo" ? "MD" : l.dia_md })} style={{ ...campo, width: 86 }}>
                            {["Treino", "Jogo", "Folga"].map((t) => <option key={t}>{t}</option>)}
                          </select>
                        </td>
                        <td style={td}>
                          <select value={l.dia_md ?? ""} disabled={l.tipo === "Folga"} onChange={(e) => alterar(i, { dia_md: e.target.value || null })} style={{ ...campo, width: 82 }}>
                            <option value="">—</option>
                            {OPCOES_MD.map((m) => <option key={m}>{m}</option>)}
                          </select>
                        </td>
                        <td style={td}>
                          <input value={l.objetivo} disabled={l.tipo === "Folga"} placeholder={l.tipo === "Jogo" ? "Adversário" : treino ? "ex.: Força, Tático" : ""} onChange={(e) => alterar(i, { objetivo: e.target.value })} style={{ ...campo, width: 150 }} />
                        </td>
                        {(["pse", "duracao_min"] as const).map((k) => (
                          <td key={k} style={td}>
                            <Num valor={l.planeado[k]} ativo={treino} largura={56} onChange={(v) => alterar(i, { planeado: { ...l.planeado, [k]: v } })} />
                            <Real v={l.real?.[k]} casas={k === "pse" ? 1 : 0} />
                          </td>
                        ))}
                        <td style={{ ...td, fontVariantNumeric: "tabular-nums", color: treino && ua ? cores.textoForte : cores.textoFraco }}>
                          {treino && ua ? fmt(ua) : "—"}
                          <Real v={l.real?.pse != null && l.real?.duracao_min != null ? l.real.pse * l.real.duracao_min : null} />
                        </td>
                        {CARGA.map((c) => {
                          const v = n(l.planeado[c.chave]);
                          const r = ref[c.fator];
                          return (
                            <td key={c.chave} style={td}>
                              <Num valor={l.planeado[c.chave]} ativo={treino} largura={78} onChange={(val) => alterar(i, { planeado: { ...l.planeado, [c.chave]: val } })} />
                              <div style={{ fontSize: "0.68rem", color: cores.textoFraco, minHeight: 14 }}>
                                {treino && v != null && r ? `${Math.round((v / r) * 100)} % jogo` : ""}
                                {l.real?.[c.chave] != null && <span> · real {fmt(l.real[c.chave] as number)}</span>}
                              </div>
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Cartao>
        )}
        <div style={{ display: "flex", gap: espaco.md, alignItems: "center", marginTop: espaco.md, flexWrap: "wrap" }}>
          <button style={estiloBotao.primario} disabled={aGravar || !dados} onClick={async () => {
            setAviso(null);
            setAGravar(true);
            try {
              await pedidoApi(`/api/teams/${teamId}/microciclos/${atual.id}/sessoes`, "PUT", {
                dias: linhas.map((l) => ({
                  data: l.data, dia_md: l.dia_md, tipo: l.tipo, objetivo: l.objetivo,
                  planeado: Object.fromEntries(Object.entries(l.planeado).map(([k, v]) => [k, n(v)])),
                })),
              });
              setAviso({ tipo: "ok", texto: "Plano das sessões guardado." });
              await carregar(atual.id);
            } catch (e) {
              setAviso({ tipo: "erro", texto: e instanceof Error ? e.message : "Erro inesperado." });
            } finally {
              setAGravar(false);
            }
          }}>{aGravar ? "A guardar…" : "Guardar plano"}</button>
          {aviso && <span style={{ fontSize: "0.84rem", color: aviso.tipo === "ok" ? cores.sucesso : cores.perigo }}>{aviso.texto}</span>}
          {dados && !dados.tem_duracao && <span style={{ fontSize: "0.76rem", color: cores.atencao }}>A duração só fica guardada depois de aplicares a migração 0012.</span>}
        </div>
      </section>
    </div>
  );
}

function Num({ valor, ativo, largura, onChange }: { valor: string; ativo: boolean; largura: number; onChange: (v: string) => void }) {
  return (
    <input inputMode="decimal" value={ativo ? valor : ""} disabled={!ativo} onChange={(e) => onChange(e.target.value.replace(",", "."))}
      style={{ ...campo, width: largura, textAlign: "right", opacity: ativo ? 1 : 0.4 }} />
  );
}

function Real({ v, casas = 0 }: { v: number | null | undefined; casas?: number }) {
  return <div style={{ fontSize: "0.68rem", color: cores.textoFraco, minHeight: 14 }}>{v != null ? `real ${fmt(v, casas)}` : ""}</div>;
}

function Campo({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: "0.72rem", color: cores.textoSuave, fontWeight: 500 }}>
      {rotulo}
      {children}
    </label>
  );
}

const campo: React.CSSProperties = { background: cores.bgCartao, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: cores.textoForte, fontSize: "0.82rem", padding: "5px 7px", height: 30, boxSizing: "border-box" };
const th: React.CSSProperties = { padding: `9px ${espaco.sm}px`, fontSize: "0.68rem", fontWeight: 500, color: cores.textoFraco, letterSpacing: "0.03em", textAlign: "left", whiteSpace: "nowrap" };
const td: React.CSSProperties = { padding: `8px ${espaco.sm}px`, fontSize: "0.84rem", color: cores.texto, verticalAlign: "top" };
