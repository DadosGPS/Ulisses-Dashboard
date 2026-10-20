"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { pedidoApi } from "@/lib/api-cliente";
import { cores, espaco, raio } from "@/lib/theme";
import { Cartao, Etiqueta, SecaoTitulo, Vazio, estiloBotao } from "@/components/ui/base";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { COR_PERFIL, dataCurta, fmtFator, mediaFatores, type ListaMicrociclos, type Microciclo } from "./tipos";

type Form = {
  numero: string; nome: string; tipo: string; perfil: string; fase: string;
  data_inicio: string; data_fim: string; notas: string;
  fatores: Record<string, { ativo: boolean; valor: string }>;
};

function somarDias(iso: string, n: number) {
  const d = new Date(`${iso}T00:00:00`);
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}

function proximaSegunda() {
  const d = new Date();
  d.setDate(d.getDate() + ((8 - d.getDay()) % 7 || 7));
  return d.toISOString().slice(0, 10);
}

function paraForm(m: Microciclo | null, chaves: string[], dados: ListaMicrociclos): Form {
  const ult = dados.microciclos[dados.microciclos.length - 1];
  const ini = m?.data_inicio ?? (ult ? somarDias(ult.data_fim, 1) : proximaSegunda());
  return {
    numero: String(m?.numero ?? (ult ? ult.numero + 1 : 1)),
    nome: m?.nome ?? "",
    tipo: m?.tipo ?? "Normal",
    perfil: m?.perfil ?? "",
    fase: m?.fase ?? "",
    data_inicio: ini,
    data_fim: m?.data_fim ?? somarDias(ini, 6),
    notas: m?.notas ?? "",
    fatores: Object.fromEntries(chaves.map((k) => [k, { ativo: m ? k in m.fatores : true, valor: m && k in m.fatores ? String(m.fatores[k]) : "" }])),
  };
}

/** Separador Microciclos: linha temporal da época + edição do microciclo. */
export function Microciclos({ teamId }: { teamId: string }) {
  const router = useRouter();
  const params = useSearchParams();
  const mcParam = params.get("mc");
  const [dados, setDados] = useState<ListaMicrociclos | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);
  const [novo, setNovo] = useState(false);
  const [form, setForm] = useState<Form | null>(null);
  const [gerarAberto, setGerarAberto] = useState(false);
  const [aGravar, setAGravar] = useState(false);

  async function carregar() {
    try {
      setDados(await pedidoApi<ListaMicrociclos>(`/api/teams/${teamId}/microciclos`));
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro inesperado.");
    }
  }
  useEffect(() => {
    carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [teamId]);

  const mcs = dados?.microciclos ?? [];
  const chaves = (dados?.fatores ?? []).map((f) => f.chave);
  // Selecionado: o do URL; senão o que contém hoje; senão o último.
  const selecionado = useMemo(() => {
    if (!mcs.length) return null;
    const porUrl = mcs.find((m) => String(m.numero) === mcParam);
    if (porUrl) return porUrl;
    const hoje = new Date().toISOString().slice(0, 10);
    return mcs.find((m) => m.data_inicio <= hoje && hoje <= m.data_fim) ?? mcs[mcs.length - 1];
  }, [mcs, mcParam]);

  useEffect(() => {
    if (dados && !novo) setForm(paraForm(selecionado, chaves, dados));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dados, selecionado?.id, novo]);

  function escolher(numero: number) {
    setNovo(false);
    const q = new URLSearchParams(params.toString());
    q.set("mc", String(numero));
    router.replace(`/planeamento?${q.toString()}`, { scroll: false });
  }

  async function executar(acao: () => Promise<unknown>, ok: string, depois?: (r: unknown) => void) {
    setAviso(null);
    setAGravar(true);
    try {
      const r = await acao();
      setAviso({ tipo: "ok", texto: ok });
      await carregar();
      depois?.(r);
    } catch (e) {
      setAviso({ tipo: "erro", texto: e instanceof Error ? e.message : "Erro inesperado." });
    } finally {
      setAGravar(false);
    }
  }

  if (erro) return <Vazio>{erro}</Vazio>;
  if (!dados) return <p style={{ color: cores.textoSuave, fontSize: "0.88rem" }}>A carregar…</p>;
  if (!dados.disponivel) return <Vazio>{dados.motivo}</Vazio>;

  function corpo(f: Form) {
    return {
      numero: Number(f.numero), nome: f.nome || null, tipo: f.tipo, perfil: f.perfil || null, fase: f.fase || null,
      data_inicio: f.data_inicio, data_fim: f.data_fim, notas: f.notas || null,
      fatores: Object.fromEntries(Object.entries(f.fatores).filter(([, v]) => v.ativo && v.valor !== "").map(([k, v]) => [k, Number(v.valor.replace(",", "."))])),
    };
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: espaco.xl }}>
      {aviso && <div style={{ fontSize: "0.84rem", color: aviso.tipo === "ok" ? cores.sucesso : cores.perigo }}>{aviso.texto}</div>}

      {/* ── Linha temporal ─────────────────────────────────────────── */}
      <section>
        <SecaoTitulo
          subtitulo="Número, perfil e fator semanal planeado vs realizado (carga de treino da semana em múltiplos de um jogo)."
          acoes={
            <>
              <button style={estiloBotao.secundario} onClick={() => setGerarAberto((v) => !v)}>Gerar microciclos</button>
              <button style={estiloBotao.primario} onClick={() => { setNovo(true); setForm(paraForm(null, chaves, dados)); }}>+ Criar microciclo</button>
            </>
          }
        >
          Época · linha temporal de microciclos
        </SecaoTitulo>

        {gerarAberto && <Gerar perfis={dados.perfis} gerar={(b) => executar(
          () => pedidoApi<{ criados: number }>(`/api/teams/${teamId}/microciclos/gerar`, "POST", b),
          "Microciclos gerados.", () => setGerarAberto(false),
        )} />}

        {mcs.length === 0 ? (
          <Vazio>Ainda não há microciclos. Usa “Gerar microciclos” para criar as semanas da época de uma vez, ou “+ Criar microciclo”.</Vazio>
        ) : (
          <div style={{ display: "flex", gap: espaco.md, overflowX: "auto", paddingBottom: espaco.sm }}>
            {mcs.map((m) => {
              const ativo = !novo && selecionado?.id === m.id;
              const cor = (m.perfil && COR_PERFIL[m.perfil]) || cores.bordaForte;
              const alvo = mediaFatores(m.fatores);
              const real = mediaFatores(Object.fromEntries(Object.entries(m.reais ?? {}).filter(([k]) => k in m.fatores)));
              return (
                <div key={m.id} onClick={() => escolher(m.numero)} role="button"
                  style={{
                    flex: "0 0 196px", cursor: "pointer", background: cores.bgCartao, borderRadius: raio.md,
                    border: `1px solid ${ativo ? cores.acento : cores.borda}`, borderLeft: `3px solid ${cor}`,
                    padding: `${espaco.md}px ${espaco.md}px ${espaco.sm}px`, boxShadow: ativo ? `0 0 0 1px ${cores.acento}` : undefined,
                  }}>
                  <div style={{ fontWeight: 700, color: cores.textoForte, fontSize: "0.92rem" }}>MC {String(m.numero).padStart(2, "0")}</div>
                  <div style={{ fontSize: "0.72rem", color: cores.textoSuave, fontVariantNumeric: "tabular-nums" }}>
                    {dataCurta(m.data_inicio).slice(0, 5)} → {dataCurta(m.data_fim)}
                  </div>
                  <div style={{ display: "flex", gap: 4, flexWrap: "wrap", margin: "6px 0" }}>
                    <Etiqueta cor={cores.textoSuave}>{m.tipo}</Etiqueta>
                    {m.perfil && <Etiqueta cor={cor}>{m.perfil}</Etiqueta>}
                  </div>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                    <span className="font-display" style={{ fontSize: "1.15rem", fontWeight: 700, color: cores.textoForte, fontVariantNumeric: "tabular-nums" }}>{fmtFator(alvo)}</span>
                    {real != null && <span style={{ fontSize: "0.74rem", color: cores.textoSuave }}>real {fmtFator(real)}</span>}
                  </div>
                  <div style={{ fontSize: "0.7rem", color: cores.textoFraco }}>{m.n_treinos ? `${m.n_treinos} treinos planeados` : "sessões por planear"}</div>
                  <div style={{ display: "flex", gap: espaco.sm, marginTop: espaco.sm, borderTop: `1px solid ${cores.borda}`, paddingTop: 6 }} onClick={(e) => e.stopPropagation()}>
                    <button style={estiloBotao.ligacao} onClick={() => escolher(m.numero)}>Editar</button>
                    <button style={estiloBotao.ligacao} disabled={aGravar} onClick={() => executar(
                      () => pedidoApi<{ numero: number }>(`/api/teams/${teamId}/microciclos/${m.id}/duplicar`, "POST"),
                      `MC ${m.numero} duplicado para a semana seguinte ao último microciclo.`,
                      (r) => escolher((r as { numero: number }).numero),
                    )}>Duplicar</button>
                    <button style={{ ...estiloBotao.ligacao, color: cores.perigo }} onClick={() => {
                      if (confirm(`Apagar o MC ${m.numero} e o plano das suas sessões?`))
                        executar(() => pedidoApi(`/api/teams/${teamId}/microciclos/${m.id}`, "DELETE"), `MC ${m.numero} apagado.`);
                    }}>Apagar</button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* ── Edição ─────────────────────────────────────────────────── */}
      {form && (novo || selecionado) && (
        <Editor
          dados={dados}
          form={form}
          setForm={setForm}
          novo={novo}
          reais={novo ? {} : selecionado?.reais ?? {}}
          aGravar={aGravar}
          numeroSelecionado={selecionado?.numero}
          cancelar={() => setNovo(false)}
          guardar={() => executar(
            () => novo
              ? pedidoApi<{ numero: number }>(`/api/teams/${teamId}/microciclos`, "POST", corpo(form))
              : pedidoApi(`/api/teams/${teamId}/microciclos/${selecionado!.id}`, "PUT", corpo(form)),
            novo ? `MC ${form.numero} criado.` : `MC ${form.numero} guardado.`,
            () => escolher(Number(form.numero)),
          )}
        />
      )}

      {mcs.length > 1 && <Evolucao dados={dados} />}
    </div>
  );
}

function Editor({ dados, form, setForm, novo, reais, aGravar, numeroSelecionado, cancelar, guardar }: {
  dados: ListaMicrociclos; form: Form; setForm: (f: Form) => void; novo: boolean; reais: Record<string, number>;
  aGravar: boolean; numeroSelecionado?: number; cancelar: () => void; guardar: () => void;
}) {
  const set = (k: keyof Form, v: string) => setForm({ ...form, [k]: v });
  const nDias = Math.round((new Date(form.data_fim).getTime() - new Date(form.data_inicio).getTime()) / 86400000) + 1;
  return (
    <section>
      <Cartao>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: espaco.md, flexWrap: "wrap", marginBottom: espaco.lg }}>
          <div>
            <div style={{ fontSize: "0.66rem", color: cores.acento, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>
              {novo ? "Novo microciclo" : "Microciclo planeado"}
            </div>
            <div style={{ fontWeight: 700, color: cores.textoForte, fontSize: "1.05rem" }}>
              MC {form.numero.padStart(2, "0")} · {dataCurta(form.data_inicio)} → {dataCurta(form.data_fim)} · {form.tipo}
            </div>
            <div style={{ fontSize: "0.8rem", color: cores.textoSuave }}>{[form.perfil, form.fase, `${nDias > 0 ? nDias : "—"} dias`].filter(Boolean).join(" · ")}</div>
          </div>
          {!novo && numeroSelecionado != null && (
            <Link href={`/calendario?data=${form.data_inicio}`} style={{ ...estiloBotao.primario, textDecoration: "none" }}>Planear os dias no calendário →</Link>
          )}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: espaco.md }}>
          <Campo rotulo="N.º microciclo"><input inputMode="numeric" value={form.numero} onChange={(e) => set("numero", e.target.value.replace(/\D/g, ""))} style={campo} /></Campo>
          <Campo rotulo="Nome"><input value={form.nome} placeholder={`MC ${form.numero.padStart(2, "0")}`} onChange={(e) => set("nome", e.target.value)} style={campo} /></Campo>
          <Campo rotulo="Tipo"><Sel valor={form.tipo} opcoes={dados.tipos} onChange={(v) => set("tipo", v)} /></Campo>
          <Campo rotulo="Perfil"><Sel valor={form.perfil} opcoes={dados.perfis} vazio onChange={(v) => set("perfil", v)} /></Campo>
          <Campo rotulo="Início"><input type="date" value={form.data_inicio} onChange={(e) => setForm({ ...form, data_inicio: e.target.value, data_fim: form.data_fim < e.target.value ? somarDias(e.target.value, 6) : form.data_fim })} style={campo} /></Campo>
          <Campo rotulo="Fim"><input type="date" value={form.data_fim} min={form.data_inicio} onChange={(e) => set("data_fim", e.target.value)} style={campo} /></Campo>
          <Campo rotulo="Fase da época"><Sel valor={form.fase} opcoes={dados.fases} vazio onChange={(v) => set("fase", v)} /></Campo>
          <Campo rotulo="Notas"><input value={form.notas} onChange={(e) => set("notas", e.target.value)} placeholder="opcional" style={campo} /></Campo>
        </div>

        <div style={{ marginTop: espaco.lg, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
          <div style={{ fontWeight: 600, color: cores.textoForte, fontSize: "0.9rem" }}>Fator semanal</div>
          <p style={{ fontSize: "0.76rem", color: cores.textoSuave, margin: "2px 0 10px", lineHeight: 1.5 }}>
            Alvo da semana de TREINO (jogos fora) em múltiplos da referência de jogo da equipa — média por 90′ dos últimos jogos completos.
            Ex.: 2,5 = a soma da semana, por jogador, chega a 250 % de um jogo.
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: espaco.md }}>
            {dados.fatores.map((f) => {
              const v = form.fatores[f.chave] ?? { ativo: false, valor: "" };
              const num = Number(v.valor.replace(",", "."));
              const ref = dados.referencia[f.chave];
              return (
                <div key={f.chave} style={{ border: `1px solid ${cores.borda}`, borderRadius: raio.sm, padding: espaco.sm, opacity: v.ativo ? 1 : 0.55 }}>
                  <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.8rem", fontWeight: 600, color: cores.textoForte }}>
                    <input type="checkbox" checked={v.ativo} onChange={(e) => setForm({ ...form, fatores: { ...form.fatores, [f.chave]: { ...v, ativo: e.target.checked } } })} />
                    {f.label}
                  </label>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 6 }}>
                    <input inputMode="decimal" disabled={!v.ativo} value={v.valor} placeholder="ex.: 2,5"
                      onChange={(e) => setForm({ ...form, fatores: { ...form.fatores, [f.chave]: { ...v, valor: e.target.value } } })}
                      style={{ ...campo, width: "100%" }} />
                    <span style={{ fontSize: "0.7rem", color: cores.textoFraco, whiteSpace: "nowrap" }}>× jogo</span>
                  </div>
                  <div style={{ fontSize: "0.7rem", color: cores.textoSuave, marginTop: 4, lineHeight: 1.5 }}>
                    {v.valor && !Number.isNaN(num) ? `${Math.round(num * 100)} %` : "—"}
                    {ref && v.valor && !Number.isNaN(num) ? ` · ${Math.round(num * ref).toLocaleString("pt-PT")} ${f.unidade}/jogador` : ""}
                    {!ref && " · sem referência de jogo"}
                    {reais[f.chave] != null && <><br />Real: <strong style={{ color: cores.texto }}>{fmtFator(reais[f.chave])}</strong></>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div style={{ display: "flex", gap: espaco.md, marginTop: espaco.lg }}>
          <button style={estiloBotao.primario} disabled={aGravar} onClick={guardar}>{aGravar ? "A guardar…" : novo ? "Criar microciclo" : "Guardar"}</button>
          {novo && <button style={estiloBotao.secundario} onClick={cancelar}>Cancelar</button>}
        </div>
      </Cartao>
    </section>
  );
}

function Gerar({ perfis, gerar }: { perfis: string[]; gerar: (b: { inicio: string; semanas: number; numero_inicial: number | null; perfil: string | null }) => void }) {
  const [f, setF] = useState({ inicio: proximaSegunda(), semanas: "10", numero: "", perfil: "" });
  return (
    <Cartao style={{ marginBottom: espaco.md }}>
      <div style={{ display: "flex", gap: espaco.md, flexWrap: "wrap", alignItems: "flex-end" }}>
        <Campo rotulo="Primeiro dia"><input type="date" value={f.inicio} onChange={(e) => setF({ ...f, inicio: e.target.value })} style={campo} /></Campo>
        <Campo rotulo="N.º de semanas"><input inputMode="numeric" value={f.semanas} onChange={(e) => setF({ ...f, semanas: e.target.value.replace(/\D/g, "") })} style={{ ...campo, width: 90 }} /></Campo>
        <Campo rotulo="Começar no MC"><input inputMode="numeric" value={f.numero} placeholder="seguinte" onChange={(e) => setF({ ...f, numero: e.target.value.replace(/\D/g, "") })} style={{ ...campo, width: 100 }} /></Campo>
        <Campo rotulo="Perfil"><Sel valor={f.perfil} opcoes={perfis} vazio onChange={(v) => setF({ ...f, perfil: v })} /></Campo>
        <button style={estiloBotao.primario} onClick={() => gerar({ inicio: f.inicio, semanas: Number(f.semanas || 0), numero_inicial: f.numero ? Number(f.numero) : null, perfil: f.perfil || null })}>
          Gerar
        </button>
      </div>
      <p style={{ fontSize: "0.74rem", color: cores.textoSuave, margin: `${espaco.sm}px 0 0` }}>
        Cria semanas de 7 dias seguidas. Semanas que se sobreponham a microciclos já existentes são saltadas.
      </p>
    </Cartao>
  );
}

function Evolucao({ dados }: { dados: ListaMicrociclos }) {
  const [chave, setChave] = useState(dados.fatores.find((f) => f.chave === "hsr")?.chave ?? dados.fatores[0]?.chave);
  const x = dados.microciclos.map((m) => `MC ${String(m.numero).padStart(2, "0")}`);
  return (
    <section>
      <SecaoTitulo
        subtitulo="Fator planeado (barras) vs carga de treino realizada (linha), em múltiplos de um jogo."
        acoes={
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
            {dados.fatores.map((f) => (
              <button key={f.chave} onClick={() => setChave(f.chave)}
                style={{ ...estiloBotao.secundario, padding: "4px 10px", fontSize: "0.76rem", ...(chave === f.chave ? { borderColor: cores.acento, color: cores.textoForte } : {}) }}>
                {f.label}
              </button>
            ))}
          </div>
        }
      >
        Planeado vs realizado por microciclo
      </SecaoTitulo>
      <Cartao>
        <PlotlyChart
          data={[
            { x, y: dados.microciclos.map((m) => m.fatores[chave] ?? null), type: "bar", name: "Planeado", marker: { color: "rgba(59,130,246,0.35)" }, hovertemplate: "%{x}<br>Planeado ×%{y}<extra></extra>" },
            { x, y: dados.microciclos.map((m) => m.reais?.[chave] ?? null), type: "scatter", mode: "lines+markers", name: "Realizado", line: { color: cores.hsr, width: 2 }, connectgaps: false, hovertemplate: "%{x}<br>Real ×%{y}<extra></extra>" },
          ]}
          layout={{ legend: { orientation: "h", y: -0.2 }, yaxis: { title: { text: "× jogo" }, rangemode: "tozero" }, barmode: "overlay" }}
          altura={260}
        />
      </Cartao>
    </section>
  );
}

function Sel({ valor, opcoes, vazio, onChange }: { valor: string; opcoes: string[]; vazio?: boolean; onChange: (v: string) => void }) {
  return (
    <select value={valor} onChange={(e) => onChange(e.target.value)} style={campo}>
      {vazio && <option value="">—</option>}
      {opcoes.map((o) => <option key={o} value={o}>{o}</option>)}
    </select>
  );
}

function Campo({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: "0.72rem", color: cores.textoSuave, fontWeight: 500 }}>
      {rotulo}
      {children}
    </label>
  );
}

const campo: React.CSSProperties = { background: cores.bgCartao, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: cores.textoForte, fontSize: "0.84rem", padding: "6px 8px", height: 34, width: "100%", boxSizing: "border-box" };
