"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { pedidoApi } from "@/lib/api-cliente";
import { createClient } from "@/lib/supabase/client";
import { cores, espaco, raio } from "@/lib/theme";
import { PageHeader } from "@/components/layout/PageHeader";
import { Cartao, Etiqueta, SecaoTitulo, Vazio, estiloBotao } from "@/components/ui/base";
import { NavEquipa } from "./NavEquipa";
import { useTr, linguaDoCookie } from "@/lib/i18n/cliente";

type Contexto = "Campeonato" | "Taça" | "Torneio" | "Amigável";
interface Jogo {
  id: string; data: string; competicao: Contexto; adversario: string; numero: number | null; duracao_min: number;
  golos_marcados: number | null; golos_sofridos: number | null; notas: string | null; convocados: number; golos: number;
}
interface Resumo {
  atleta_id: string; nome: string; convocado: number; utilizado: number; titular: number; minutos: number;
  pct_minutos: number | null; golos: number; assistencias: number; por_contexto: Record<Contexto, number>;
}
interface Dados {
  disponivel: boolean; motivo?: string; rotulo: string; competicoes: Contexto[]; posicoes: string[];
  plantel: { atleta_id: string; nome: string }[]; jogos: Jogo[]; resumo: Resumo[];
  minutos_possiveis: number; por_contexto: Record<Contexto, number>;
}
type Linha = { convocado: boolean; titular: boolean; posicao: string; minutos: string; golos: string; assistencias: string };

const COR: Record<Contexto, string> = { Campeonato: "#3b82f6", "Taça": "#a855f7", Torneio: "#f59e0b", "Amigável": "#14b8a6" };
const dataPt = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;
const hoje = () => new Date().toISOString().slice(0, 10);

/** Jogos da equipa: registo de cada jogo e resumo da época por jogador. */
export function JogosEquipa({ teamId }: { teamId: string }) {
  const tr = useTr();
  const [dados, setDados] = useState<Dados | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [editar, setEditar] = useState<string | "novo" | null>(null);
  const [aviso, setAviso] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);

  async function carregar() {
    try {
      setDados(await pedidoApi<Dados>(`/api/academia/equipas/${teamId}/jogos`));
    } catch (e) {
      setErro(e instanceof Error ? e.message : tr("Erro inesperado."));
    }
  }
  useEffect(() => {
    carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [teamId]);

  if (erro) return <Moldura teamId={teamId} rotulo=""><Vazio>{erro}</Vazio></Moldura>;
  if (!dados) return <Moldura teamId={teamId} rotulo=""><p style={{ color: cores.textoSuave }}>{tr("A carregar…")}</p></Moldura>;
  if (!dados.disponivel) return <Moldura teamId={teamId} rotulo=""><Vazio>{dados.motivo}</Vazio></Moldura>;

  return (
    <Moldura teamId={teamId} rotulo={dados.rotulo}>
      {aviso && <div role="status" style={{ fontSize: "0.84rem", color: aviso.tipo === "ok" ? cores.sucesso : cores.perigo }}>{aviso.texto}</div>}

      <div style={{ display: "flex", gap: espaco.sm, flexWrap: "wrap", alignItems: "center" }}>
        {dados.competicoes.map((c) => (
          <div key={c} style={{ border: `1px solid ${cores.borda}`, borderLeft: `3px solid ${COR[c]}`, borderRadius: raio.sm, padding: "6px 12px", minWidth: 110 }}>
            <div style={{ fontSize: "0.68rem", color: cores.textoFraco, textTransform: "uppercase", letterSpacing: "0.05em" }}>{tr(c)}</div>
            <div style={{ fontSize: "1.1rem", fontWeight: 700, color: cores.textoForte }}>{dados.por_contexto[c]} <span style={{ fontSize: "0.74rem", fontWeight: 400, color: cores.textoSuave }}>{tr("jogos")}</span></div>
          </div>
        ))}
        <div style={{ marginLeft: "auto", display: "flex", gap: espaco.sm, flexWrap: "wrap" }}>
          <Importar teamId={teamId} feito={(t, ok) => { setAviso({ tipo: ok ? "ok" : "erro", texto: t }); carregar(); }} />
          <button style={estiloBotao.primario} onClick={() => { setEditar("novo"); setAviso(null); }}>{tr("+ Novo jogo")}</button>
        </div>
      </div>

      {editar && (
        <EditorJogo
          key={editar}
          teamId={teamId}
          dados={dados}
          jogoId={editar === "novo" ? null : editar}
          fechar={(msg) => { setEditar(null); if (msg) { setAviso({ tipo: "ok", texto: msg }); carregar(); } }}
        />
      )}

      <ResumoEpoca dados={dados} />

      <section>
        <SecaoTitulo subtitulo={tr("{0} jogo(s) · {1} minutos possíveis", [dados.jogos.length, dados.minutos_possiveis.toLocaleString(tr.loc)])}>{tr("Jogos")}</SecaoTitulo>
        {dados.jogos.length === 0 ? <Vazio>{tr("Ainda não há jogos. Usa “+ Novo jogo” ou importa a vossa folha (Excel ou CSV).")}</Vazio> : (
          <Cartao padding={0}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 640 }}>
                <thead><tr>{["Data", "Contexto", "Adversário", "Resultado", "Convocados", "Duração", ""].map((h) => <th key={h} style={th}>{tr(h)}</th>)}</tr></thead>
                <tbody>
                  {dados.jogos.map((j) => (
                    <tr key={j.id} style={{ borderTop: `1px solid ${cores.borda}` }}>
                      <td style={{ ...td, whiteSpace: "nowrap" }}>{dataPt(j.data)}</td>
                      <td style={td}><Etiqueta cor={COR[j.competicao]}>{tr(j.competicao)}</Etiqueta></td>
                      <td style={{ ...td, color: cores.textoForte, fontWeight: 600 }}>{j.adversario}{j.numero ? <span style={{ color: cores.textoFraco, fontWeight: 400 }}> · n.º {j.numero}</span> : null}</td>
                      <td style={td}>{j.golos_marcados != null && j.golos_sofridos != null ? `${j.golos_marcados}–${j.golos_sofridos}` : "—"}</td>
                      <td style={td}>{j.convocados}</td>
                      <td style={td}>{j.duracao_min}′</td>
                      <td style={{ ...td, textAlign: "right", whiteSpace: "nowrap" }}>
                        <button style={estiloBotao.ligacao} onClick={() => { setEditar(j.id); setAviso(null); }}>{tr("Editar")}</button>
                        <button style={{ ...estiloBotao.ligacao, color: cores.perigo, marginLeft: espaco.md }} onClick={async () => {
                          if (!confirm(tr("Apagar o jogo de {0} contra {1}?", [dataPt(j.data), j.adversario]))) return;
                          await pedidoApi(`/api/academia/equipas/${teamId}/jogos/${j.id}`, "DELETE");
                          setAviso({ tipo: "ok", texto: tr("Jogo apagado.") });
                          carregar();
                        }}>{tr("Apagar")}</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Cartao>
        )}
      </section>
    </Moldura>
  );
}

function Moldura({ teamId, rotulo, children }: { teamId: string; rotulo: string; children: React.ReactNode }) {
  const tr = useTr();
  return (
    <div>
      <PageHeader titulo={tr("Academia{0}", [rotulo ? ` · ${rotulo}` : ""])} subtitulo={tr("Jogos da época — minutos por contexto, golos e assistências")} />
      <NavEquipa teamId={teamId} />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px`, display: "flex", flexDirection: "column", gap: espaco.xl, maxWidth: 1300 }}>
        {children}
      </div>
    </div>
  );
}

// ── Resumo da época por jogador ──────────────────────────────────────────────
function ResumoEpoca({ dados }: { dados: Dados }) {
  const tr = useTr();
  const [ordem, setOrdem] = useState<"minutos" | "golos" | "assistencias" | "nome">("minutos");
  // Inclui quem ainda não foi convocado (0 minutos), para se ver o plantel todo.
  const linhas = useMemo(() => {
    const por = new Map(dados.resumo.map((r) => [r.atleta_id, r]));
    const todos = [...dados.resumo, ...dados.plantel.filter((p) => !por.has(p.atleta_id)).map((p) => ({
      atleta_id: p.atleta_id, nome: p.nome, convocado: 0, utilizado: 0, titular: 0, minutos: 0, pct_minutos: 0, golos: 0, assistencias: 0,
      por_contexto: { Campeonato: 0, "Taça": 0, Torneio: 0, "Amigável": 0 } as Record<Contexto, number>,
    }))];
    return todos.sort((a, b) => ordem === "nome" ? a.nome.localeCompare(b.nome) : (b[ordem] - a[ordem]) || a.nome.localeCompare(b.nome));
  }, [dados, ordem]);
  const total = (k: "golos" | "assistencias" | "minutos") => linhas.reduce((s, r) => s + r[k], 0);

  return (
    <section>
      <SecaoTitulo
        subtitulo={tr("% = minutos jogados ÷ minutos de todos os jogos da equipa. Os minutos por contexto somam o total.")}
        acoes={
          <select value={ordem} onChange={(e) => setOrdem(e.target.value as typeof ordem)} style={campo} aria-label={tr("Ordenar")}>
            <option value="minutos">{tr("Ordenar por minutos")}</option><option value="golos">{tr("Por golos")}</option>
            <option value="assistencias">{tr("Por assistências")}</option><option value="nome">{tr("Por nome")}</option>
          </select>
        }
      >
        {tr("Minutos e contribuições da época")}</SecaoTitulo>
      <Cartao padding={0}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 900, fontSize: "0.82rem" }}>
            <thead>
              <tr>
                <th style={th}>{tr("Jogador")}</th>
                {["Convoc.", "Utiliz.", "Titular", "Minutos", "% dos possíveis"].map((h) => <th key={h} style={{ ...th, textAlign: "right" }}>{tr(h)}</th>)}
                {dados.competicoes.map((c) => <th key={c} style={{ ...th, textAlign: "right", color: COR[c] }}>{tr(c)}</th>)}
                <th style={{ ...th, textAlign: "right" }}>{tr("Golos")}</th>
                <th style={{ ...th, textAlign: "right" }}>{tr("Assist.")}</th>
              </tr>
            </thead>
            <tbody>
              {linhas.map((r) => (
                <tr key={r.atleta_id} style={{ borderTop: `1px solid ${cores.borda}` }}>
                  <td style={{ ...td, whiteSpace: "nowrap" }}>
                    <Link href={`/academia/atleta/${r.atleta_id}`} style={{ color: cores.textoForte, fontWeight: 600, textDecoration: "none" }}>{r.nome}</Link>
                  </td>
                  <td style={num}>{r.convocado}</td>
                  <td style={num}>{r.utilizado}</td>
                  <td style={num}>{r.titular}</td>
                  <td style={{ ...num, fontWeight: 700, color: cores.textoForte }}>{r.minutos.toLocaleString(tr.loc)}</td>
                  <td style={num}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 6 }}>
                      <div style={{ width: 60, height: 6, borderRadius: 3, background: cores.superficie, overflow: "hidden" }}>
                        <div style={{ width: `${Math.min(100, r.pct_minutos ?? 0)}%`, height: "100%", background: cores.acento }} />
                      </div>
                      <span style={{ minWidth: 40 }}>{r.pct_minutos != null ? `${r.pct_minutos.toLocaleString(tr.loc)} %` : "—"}</span>
                    </div>
                  </td>
                  {dados.competicoes.map((c) => <td key={c} style={{ ...num, color: r.por_contexto[c] ? cores.texto : cores.textoFraco }}>{r.por_contexto[c] || "—"}</td>)}
                  <td style={{ ...num, fontWeight: r.golos ? 700 : 400 }}>{r.golos || "—"}</td>
                  <td style={{ ...num, fontWeight: r.assistencias ? 700 : 400 }}>{r.assistencias || "—"}</td>
                </tr>
              ))}
              <tr style={{ borderTop: `2px solid ${cores.bordaForte}`, background: cores.superficie }}>
                <td style={{ ...td, fontWeight: 700 }}>{tr("Equipa")}</td>
                <td colSpan={3} style={td} />
                <td style={{ ...num, fontWeight: 700 }}>{total("minutos").toLocaleString(tr.loc)}</td>
                <td style={td} />
                {dados.competicoes.map((c) => <td key={c} style={td} />)}
                <td style={{ ...num, fontWeight: 700 }}>{total("golos")}</td>
                <td style={{ ...num, fontWeight: 700 }}>{total("assistencias")}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Cartao>
    </section>
  );
}

// ── Editor de um jogo ────────────────────────────────────────────────────────
function EditorJogo({ teamId, dados, jogoId, fechar }: { teamId: string; dados: Dados; jogoId: string | null; fechar: (msg?: string) => void }) {
  const tr = useTr();
  const vazio: Linha = { convocado: false, titular: false, posicao: "", minutos: "", golos: "", assistencias: "" };
  const [jogo, setJogo] = useState({ data: hoje(), competicao: "Campeonato" as Contexto, adversario: "", numero: "", duracao_min: "80", golos_marcados: "", golos_sofridos: "", notas: "" });
  const [linhas, setLinhas] = useState<Record<string, Linha>>(Object.fromEntries(dados.plantel.map((p) => [p.atleta_id, { ...vazio }])));
  const [estado, setEstado] = useState<string | null>(null);
  const [aGravar, setAGravar] = useState(false);

  useEffect(() => {
    if (!jogoId) return;
    pedidoApi<{ jogo: Jogo; participacoes: { atleta_id: string; posicao: string | null; minutos: number; titular: boolean; golos: number; assistencias: number }[] }>(
      `/api/academia/equipas/${teamId}/jogos/${jogoId}`,
    ).then((r) => {
      const j = r.jogo;
      setJogo({ data: j.data, competicao: j.competicao, adversario: j.adversario, numero: j.numero ? String(j.numero) : "", duracao_min: String(j.duracao_min),
        golos_marcados: j.golos_marcados != null ? String(j.golos_marcados) : "", golos_sofridos: j.golos_sofridos != null ? String(j.golos_sofridos) : "", notas: j.notas ?? "" });
      setLinhas((ls) => {
        const n = { ...ls };
        for (const p of r.participacoes) n[p.atleta_id] = { convocado: true, titular: p.titular, posicao: p.posicao ?? "", minutos: String(p.minutos), golos: p.golos ? String(p.golos) : "", assistencias: p.assistencias ? String(p.assistencias) : "" };
        return n;
      });
    }).catch((e) => setEstado(e.message));
  }, [jogoId, teamId]);

  const set = (aid: string, m: Partial<Linha>) => setLinhas((ls) => ({ ...ls, [aid]: { ...ls[aid], ...m, convocado: m.convocado ?? true } }));
  const convocados = Object.values(linhas).filter((l) => l.convocado).length;

  async function guardar() {
    setEstado(null);
    if (!jogo.adversario.trim()) { setEstado(tr("Indica o adversário.")); return; }
    setAGravar(true);
    try {
      const corpo = {
        jogo: { ...jogo, numero: jogo.numero || null, golos_marcados: jogo.golos_marcados === "" ? null : jogo.golos_marcados, golos_sofridos: jogo.golos_sofridos === "" ? null : jogo.golos_sofridos },
        participacoes: Object.entries(linhas).filter(([, l]) => l.convocado).map(([atleta_id, l]) => ({
          atleta_id, titular: l.titular, posicao: l.posicao || null, minutos: Number(l.minutos || 0), golos: Number(l.golos || 0), assistencias: Number(l.assistencias || 0),
        })),
      };
      await pedidoApi(jogoId ? `/api/academia/equipas/${teamId}/jogos/${jogoId}` : `/api/academia/equipas/${teamId}/jogos`, jogoId ? "PUT" : "POST", corpo);
      fechar(jogoId ? tr("Jogo atualizado.") : tr("Jogo registado."));
    } catch (e) {
      setEstado(e instanceof Error ? e.message : tr("Erro."));
    } finally {
      setAGravar(false);
    }
  }

  return (
    <Cartao destaque={cores.acento}>
      <div style={{ fontWeight: 700, color: cores.textoForte, marginBottom: espaco.md }}>{jogoId ? tr("Editar jogo") : tr("Novo jogo")}</div>
      <div style={{ display: "flex", gap: espaco.md, flexWrap: "wrap", alignItems: "flex-end" }}>
        <Rot t={tr("Data")}><input type="date" value={jogo.data} onChange={(e) => setJogo({ ...jogo, data: e.target.value })} style={campo} /></Rot>
        <Rot t={tr("Contexto")}>
          <select value={jogo.competicao} onChange={(e) => setJogo({ ...jogo, competicao: e.target.value as Contexto })} style={campo}>
            {dados.competicoes.map((c) => <option key={c} value={c}>{tr(c)}</option>)}
          </select>
        </Rot>
        <Rot t={tr("Adversário")}><input value={jogo.adversario} onChange={(e) => setJogo({ ...jogo, adversario: e.target.value })} placeholder={tr("ex.: Bjärreds FF")} style={{ ...campo, width: 200 }} /></Rot>
        <Rot t={tr("Duração (min)")}><input inputMode="numeric" value={jogo.duracao_min} onChange={(e) => setJogo({ ...jogo, duracao_min: e.target.value.replace(/\D/g, "") })} style={{ ...campo, width: 80 }} /></Rot>
        <Rot t={tr("Resultado")}>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <input inputMode="numeric" value={jogo.golos_marcados} onChange={(e) => setJogo({ ...jogo, golos_marcados: e.target.value.replace(/\D/g, "") })} style={{ ...campo, width: 44, textAlign: "center" }} aria-label={tr("Golos marcados")} />
            <span>–</span>
            <input inputMode="numeric" value={jogo.golos_sofridos} onChange={(e) => setJogo({ ...jogo, golos_sofridos: e.target.value.replace(/\D/g, "") })} style={{ ...campo, width: 44, textAlign: "center" }} aria-label={tr("Golos sofridos")} />
          </div>
        </Rot>
        <Rot t={tr("N.º do jogo")}><input inputMode="numeric" value={jogo.numero} onChange={(e) => setJogo({ ...jogo, numero: e.target.value.replace(/\D/g, "") })} style={{ ...campo, width: 70 }} /></Rot>
      </div>

      <div style={{ marginTop: espaco.md, fontSize: "0.78rem", color: cores.textoSuave }}>
        {tr("Marca os convocados. Ao marcar")}{" "}<strong>{tr("titular")}</strong>{tr(", os minutos ficam com a duração do jogo (podes alterar).")}{" "}{convocados} {tr("convocado(s).")}</div>
      <div style={{ overflowX: "auto", marginTop: espaco.sm }}>
        <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 720, fontSize: "0.82rem" }}>
          <thead><tr>{["Conv.", "Jogador", "Titular", "Posição", "Minutos", "Golos", "Assist."].map((h) => <th key={h} style={th}>{tr(h)}</th>)}</tr></thead>
          <tbody>
            {dados.plantel.map((p) => {
              const l = linhas[p.atleta_id] ?? vazio;
              return (
                <tr key={p.atleta_id} style={{ borderTop: `1px solid ${cores.borda}`, opacity: l.convocado ? 1 : 0.55 }}>
                  <td style={td}><input type="checkbox" aria-label={tr("Convocado: {0}", [p.nome])} checked={l.convocado} onChange={(e) => setLinhas((ls) => ({ ...ls, [p.atleta_id]: { ...l, convocado: e.target.checked } }))} /></td>
                  <td style={{ ...td, fontWeight: 600, color: cores.textoForte, whiteSpace: "nowrap" }}>{p.nome}</td>
                  <td style={td}><input type="checkbox" aria-label={tr("Titular: {0}", [p.nome])} checked={l.titular} onChange={(e) => set(p.atleta_id, { titular: e.target.checked, minutos: e.target.checked && !l.minutos ? jogo.duracao_min : l.minutos })} /></td>
                  <td style={td}>
                    <select value={l.posicao} onChange={(e) => set(p.atleta_id, { posicao: e.target.value })} style={{ ...campo, height: 28 }}>
                      <option value="">—</option>
                      {dados.posicoes.map((x) => <option key={x} value={x}>{tr(x)}</option>)}
                    </select>
                  </td>
                  {(["minutos", "golos", "assistencias"] as const).map((k) => (
                    <td key={k} style={td}>
                      <input inputMode="numeric" value={l[k]} onChange={(e) => set(p.atleta_id, { [k]: e.target.value.replace(/\D/g, "") })} style={{ ...campo, width: 60, height: 28, textAlign: "right" }} />
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div style={{ display: "flex", gap: espaco.md, alignItems: "center", marginTop: espaco.md }}>
        <button style={estiloBotao.primario} disabled={aGravar} onClick={guardar}>{aGravar ? tr("A guardar…") : tr("Guardar jogo")}</button>
        <button style={estiloBotao.secundario} onClick={() => fechar()}>{tr("Cancelar")}</button>
        {estado && <span style={{ fontSize: "0.82rem", color: cores.perigo }}>{estado}</span>}
      </div>
    </Cartao>
  );
}

// ── Importar a folha (Excel/CSV) ─────────────────────────────────────────────
function Importar({ teamId, feito }: { teamId: string; feito: (texto: string, ok: boolean) => void }) {
  const tr = useTr();
  const ref = useRef<HTMLInputElement>(null);
  const [aEnviar, setAEnviar] = useState(false);
  async function enviar(f: File) {
    setAEnviar(true);
    try {
      const { data: { session } } = await createClient().auth.getSession();
      if (!session) throw new Error(tr("Sessão expirada. Volta a entrar."));
      const fd = new FormData();
      fd.append("ficheiro", f);
      fd.append("duracao_min", "80");
      const r = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/academia/equipas/${teamId}/jogos-importar`, {
        method: "POST", headers: { Authorization: `Bearer ${session.access_token}`, "X-Lingua": linguaDoCookie() }, body: fd,
      });
      const j = await r.json().catch(() => null);
      if (!r.ok) throw new Error(j?.detail ?? tr("Não foi possível importar."));
      const falta = j.nao_encontrados?.length
        ? " " + tr("Não encontrei na equipa: {0} — adiciona-os em Jogadores (mesmo nome) e volta a importar.", [j.nao_encontrados.join(", ")])
        : "";
      feito(tr("Importado: {0} jogo(s) ({1} novo(s)), {2} registo(s) de jogadores.{3}", [j.jogos, j.jogos_novos, j.participacoes, falta]), true);
    } catch (e) {
      feito(e instanceof Error ? e.message : tr("Erro ao importar."), false);
    } finally {
      setAEnviar(false);
      if (ref.current) ref.current.value = "";
    }
  }
  return (
    <>
      <input ref={ref} type="file" accept=".xlsx,.xls,.csv" hidden onChange={(e) => e.target.files?.[0] && enviar(e.target.files[0])} />
      <button style={estiloBotao.secundario} disabled={aEnviar} onClick={() => ref.current?.click()}
        title={tr("Uma linha por jogador e jogo: equipa, data, competição, ano, n.º, adversário, jogador, posição, minutos, titular, golos, assistências")}>
        {aEnviar ? tr("A importar…") : tr("Importar folha (Excel/CSV)")}
      </button>
    </>
  );
}

function Rot({ t, children }: { t: string; children: React.ReactNode }) {
  return <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: "0.72rem", color: cores.textoSuave, fontWeight: 500 }}>{t}{children}</label>;
}

const campo: React.CSSProperties = { background: cores.bgCartao, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: cores.textoForte, fontSize: "0.82rem", padding: "5px 8px", height: 32, boxSizing: "border-box" };
const th: React.CSSProperties = { padding: `8px ${espaco.sm}px`, fontSize: "0.68rem", fontWeight: 600, color: cores.textoSuave, textAlign: "left", whiteSpace: "nowrap" };
const td: React.CSSProperties = { padding: `6px ${espaco.sm}px`, color: cores.texto };
const num: React.CSSProperties = { ...td, textAlign: "right", fontVariantNumeric: "tabular-nums" };
