"use client";

import { useEffect, useState } from "react";
import { pedidoApi } from "@/lib/api-cliente";
import { cores, espaco, raio } from "@/lib/theme";
import { Cartao, Etiqueta, SecaoTitulo, Vazio } from "@/components/ui/base";
import { useTr } from "@/lib/i18n/cliente";
import { COR_PERFIL } from "./tipos";

type Jogo = { data: string; adversario: string | null; competicao: string | null; resultado: string | null; origem: string };
type Semana = {
  id: string; numero: number; nome: string | null; perfil: string | null; fase: string | null; tipo: string | null;
  inicio: string; fim: string; estado: "passado" | "atual" | "futuro";
  fatores: Record<string, number>; planeado: Record<string, number>;
  real: { treino: Record<string, number>; carga_interna: number | null; n_treinos: number; n_jogos: number };
  jogos: Jogo[]; variacao_pct: number | null; pico: boolean;
};
interface Epoca {
  rotulo: string | null; epoca: string | null; inicio: string | null; fim: string | null; hoje: string;
  fatores: { chave: string; label: string; unidade: string }[];
  fases: { fase: string; inicio: string; fim: string; microciclos: number }[];
  semanas: Semana[]; jogos: Jogo[]; pico_variacao_pct: number;
}

const COR_FASE: Record<string, string> = {
  "Pré-época": "#6366f1", "1.ª volta": "#0ea5e9", "2.ª volta": "#0891b2", "Pausa competitiva": "#a3a3a3", "Transição": "#78716c",
};
const METRICAS = [
  { chave: "distancia", label: "Distância", unidade: "m", cor: cores.distanciaTotal },
  { chave: "hsr", label: "HSR", unidade: "m", cor: cores.hsr },
  { chave: "sprint", label: "Sprint", unidade: "m", cor: cores.sprint },
  { chave: "acc", label: "Acelerações", unidade: "n", cor: cores.acc },
  { chave: "dcc", label: "Desacelerações", unidade: "n", cor: cores.dcc },
  { chave: "carga_interna", label: "Carga interna", unidade: "UA", cor: cores.cargaInterna },
];
const LARG = 72; // px por semana
const ALT_GRAF = 120;

function valorReal(s: Semana, k: string) {
  return k === "carga_interna" ? s.real.carga_interna : s.real.treino[k] ?? null;
}

/** Macrociclo: a época toda — fases, microciclos, jogos e carga por semana. */
export function EpocaVista({ teamId }: { teamId: string }) {
  const tr = useTr();
  const [dados, setDados] = useState<Epoca | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [metrica, setMetrica] = useState("distancia");

  useEffect(() => {
    pedidoApi<Epoca>(`/api/teams/${teamId}/epoca`).then(setDados).catch((e) => setErro(e.message));
  }, [teamId]);

  if (erro) return <Vazio>{erro}</Vazio>;
  if (!dados) return <p style={{ color: cores.textoSuave, fontSize: "0.88rem" }}>{tr("A carregar…")}</p>;
  if (!dados.semanas.length) return <Vazio>{tr("Ainda não há microciclos. Cria-os no separador Microciclos para veres a época inteira aqui.")}</Vazio>;

  const m = METRICAS.find((x) => x.chave === metrica)!;
  const fmt = (v: number | null | undefined) => (v == null ? "—" : Math.round(v).toLocaleString(tr.loc));
  const maximo = Math.max(1, ...dados.semanas.flatMap((s) => [valorReal(s, metrica) ?? 0, s.planeado[metrica] ?? 0]));
  const atual = dados.semanas.find((s) => s.estado === "atual");
  const jogados = dados.jogos.filter((j) => j.data <= dados.hoje).length;
  const picos = dados.semanas.filter((s) => s.pico).length;
  const cumprimento = dados.semanas.filter((s) => s.estado !== "futuro" && s.planeado[metrica] && valorReal(s, metrica) != null)
    .map((s) => (valorReal(s, metrica)! / s.planeado[metrica]) * 100);
  const mediaCumprimento = cumprimento.length ? cumprimento.reduce((a, b) => a + b, 0) / cumprimento.length : null;

  // Meses: para cada semana, o mês do seu início — junta semanas seguidas do mesmo mês.
  const meses: { rotulo: string; n: number }[] = [];
  for (const s of dados.semanas) {
    const d = new Date(`${s.inicio}T00:00:00`);
    const r = `${d.toLocaleDateString(tr.loc, { month: "short" }).replace(".", "")} ${String(d.getFullYear()).slice(2)}`;
    if (meses.length && meses[meses.length - 1].rotulo === r) meses[meses.length - 1].n++;
    else meses.push({ rotulo: r, n: 1 });
  }
  // Fases: semanas seguidas com a mesma fase.
  const fases: { fase: string | null; n: number }[] = [];
  for (const s of dados.semanas) {
    if (fases.length && fases[fases.length - 1].fase === s.fase) fases[fases.length - 1].n++;
    else fases.push({ fase: s.fase, n: 1 });
  }
  const largura = dados.semanas.length * LARG;
  const fundoColuna = (s: Semana) => (s.estado === "atual" ? `color-mix(in srgb, ${cores.acento} 10%, transparent)` : "transparent");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: espaco.xl }}>
      <div className="grelha-kpis" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))" }}>
        <Resumo titulo={tr("Microciclos")} valor={String(dados.semanas.length)} sub={atual ? tr("agora: MC {0}", [atual.numero]) : tr("nenhum em curso")} />
        <Resumo titulo={tr("Jogos")} valor={`${jogados} / ${dados.jogos.length}`} sub={tr("realizados / na época")} />
        <Resumo titulo={tr("Fase atual")} valor={atual?.fase ? tr(atual.fase) : "—"} sub={atual?.perfil ? tr(atual.perfil) : ""} />
        <Resumo titulo={tr("Cumprimento do plano")} valor={mediaCumprimento == null ? "—" : `${Math.round(mediaCumprimento)}%`} sub={tr("{0} dos treinos, semanas passadas", [tr(m.label)])} />
        <Resumo titulo={tr("Subidas bruscas")} valor={String(picos)} sub={tr("semanas com carga interna > +{0}%", [dados.pico_variacao_pct])} alerta={picos > 0} />
      </div>

      <section>
        <SecaoTitulo
          ajuda={tr("Uma coluna por microciclo. Barras = carga de treino por jogador (média do plantel, sem jogos); traço = o planeado (fator semanal × referência de jogo). Na carga interna entram treinos e jogos e não há planeado. A coluna realçada é a semana atual.")}
          acoes={
            <div role="tablist" style={{ display: "flex", gap: 2, padding: 3, borderRadius: 9, background: cores.superficie, flexWrap: "wrap" }}>
              {METRICAS.map((x) => (
                <button key={x.chave} role="tab" aria-selected={metrica === x.chave} onClick={() => setMetrica(x.chave)}
                  style={{ border: "none", borderRadius: 7, padding: "4px 10px", fontSize: "0.76rem", fontWeight: 600, cursor: "pointer",
                    background: metrica === x.chave ? cores.bgCartao : "transparent", color: metrica === x.chave ? cores.textoForte : cores.textoSuave }}>
                  {tr(x.label)}
                </button>
              ))}
            </div>
          }
        >{tr("Época {0}", [dados.epoca ?? ""])}</SecaoTitulo>

        <Cartao padding={0}>
          <div style={{ overflowX: "auto" }}>
            <div style={{ display: "grid", gridTemplateColumns: `110px ${largura}px`, minWidth: 110 + largura }}>
              <Rotulo>{tr("Mês")}</Rotulo>
              <div style={{ display: "flex" }}>
                {meses.map((x, i) => <div key={i} style={{ width: x.n * LARG, ...celulaTopo, textTransform: "capitalize" }}>{x.rotulo}</div>)}
              </div>

              <Rotulo>{tr("Fase")}</Rotulo>
              <div style={{ display: "flex", padding: "4px 0" }}>
                {fases.map((f, i) => (
                  <div key={i} style={{ width: f.n * LARG, padding: "0 2px", boxSizing: "border-box" }}>
                    {f.fase && <div title={tr(f.fase)} style={{ background: COR_FASE[f.fase] ?? cores.textoSuave, color: "#fff", borderRadius: 6, fontSize: "0.7rem", fontWeight: 600, padding: "3px 6px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{tr(f.fase)}</div>}
                  </div>
                ))}
              </div>

              <Rotulo>{tr("Microciclo")}</Rotulo>
              <div style={{ display: "flex" }}>
                {dados.semanas.map((s) => (
                  <div key={s.id} style={{ width: LARG, padding: "4px 2px", boxSizing: "border-box", background: fundoColuna(s) }}
                    title={[`MC ${s.numero}`, s.nome, s.perfil && tr(s.perfil), `${s.inicio.slice(8)}/${s.inicio.slice(5, 7)} – ${s.fim.slice(8)}/${s.fim.slice(5, 7)}`].filter(Boolean).join(" · ")}>
                    <div style={{ borderRadius: 6, border: `1px solid ${cores.borda}`, borderTop: `3px solid ${(s.perfil && COR_PERFIL[s.perfil]) || cores.bordaForte}`, padding: "3px 4px", textAlign: "center", opacity: s.estado === "futuro" ? 0.65 : 1 }}>
                      <div style={{ fontSize: "0.74rem", fontWeight: 700, color: cores.textoForte }}>MC {s.numero}</div>
                      <div style={{ fontSize: "0.62rem", color: cores.textoSuave, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{s.perfil ? tr(s.perfil) : "—"}</div>
                    </div>
                  </div>
                ))}
              </div>

              <Rotulo>{tr("Jogos")}</Rotulo>
              <div style={{ display: "flex" }}>
                {dados.semanas.map((s) => (
                  <div key={s.id} style={{ width: LARG, padding: "4px 2px", boxSizing: "border-box", display: "flex", flexDirection: "column", gap: 2, alignItems: "center", background: fundoColuna(s) }}>
                    {s.jogos.map((j) => (
                      <span key={j.data} title={[j.data.split("-").reverse().join("/"), j.adversario && `vs ${j.adversario}`, j.competicao && tr(j.competicao), j.resultado].filter(Boolean).join(" · ")}
                        style={{ fontSize: "0.64rem", fontWeight: 600, padding: "1px 6px", borderRadius: 999, maxWidth: LARG - 6, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                          background: j.data <= dados.hoje ? cores.textoForte : "transparent", color: j.data <= dados.hoje ? cores.bg : cores.textoForte, border: `1px solid ${cores.textoForte}` }}>
                        {j.resultado ?? `${j.data.slice(8)}/${j.data.slice(5, 7)}`}
                      </span>
                    ))}
                  </div>
                ))}
              </div>

              <Rotulo>{tr(m.label)}<br /><span style={{ fontWeight: 400, color: cores.textoFraco }}>{tr("por jogador")}</span></Rotulo>
              <div style={{ display: "flex", alignItems: "flex-end", height: ALT_GRAF + 26, paddingTop: 6 }}>
                {dados.semanas.map((s) => {
                  const v = valorReal(s, metrica);
                  const p = metrica === "carga_interna" ? null : s.planeado[metrica] ?? null;
                  const h = v != null ? (v / maximo) * ALT_GRAF : 0;
                  const hp = p != null ? (p / maximo) * ALT_GRAF : null;
                  const pct = v != null && p ? Math.round((v / p) * 100) : null;
                  return (
                    <div key={s.id} title={[`MC ${s.numero}`, `${tr("Realizado")}: ${fmt(v)} ${m.unidade}`, p != null ? `${tr("Planeado")}: ${fmt(p)} ${m.unidade}` : null, pct != null ? `${pct}%` : null].filter(Boolean).join("\n")}
                      style={{ width: LARG, height: "100%", position: "relative", display: "flex", flexDirection: "column", justifyContent: "flex-end", alignItems: "center", background: fundoColuna(s) }}>
                      <span style={{ fontSize: "0.62rem", color: cores.textoSuave, marginBottom: 2, fontVariantNumeric: "tabular-nums" }}>{v != null ? (pct != null ? `${pct}%` : fmt(v)) : ""}</span>
                      <div style={{ width: 30, height: Math.max(h, v != null ? 2 : 0), background: m.cor, borderRadius: "4px 4px 0 0", opacity: s.estado === "atual" ? 0.7 : 1 }} />
                      {hp != null && <div style={{ position: "absolute", bottom: hp, left: 12, right: 12, borderTop: `2px dashed ${cores.textoForte}` }} />}
                    </div>
                  );
                })}
              </div>

              <Rotulo>{tr("Variação")}<br /><span style={{ fontWeight: 400, color: cores.textoFraco }}>{tr("carga interna")}</span></Rotulo>
              <div style={{ display: "flex" }}>
                {dados.semanas.map((s) => (
                  <div key={s.id} style={{ width: LARG, textAlign: "center", padding: "6px 0", fontSize: "0.72rem", fontVariantNumeric: "tabular-nums", background: fundoColuna(s),
                    color: s.pico ? cores.atencao : cores.textoSuave, fontWeight: s.pico ? 700 : 400 }}>
                    {s.variacao_pct == null ? "—" : `${s.variacao_pct > 0 ? "+" : ""}${Math.round(s.variacao_pct)}%`}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Cartao>
        <div style={{ display: "flex", gap: espaco.md, flexWrap: "wrap", marginTop: espaco.sm, fontSize: "0.72rem", color: cores.textoSuave, alignItems: "center" }}>
          {Object.entries(COR_PERFIL).map(([p, c]) => <Etiqueta key={p} cor={c}>{tr(p)}</Etiqueta>)}
          <span><span style={{ display: "inline-block", width: 16, borderTop: `2px dashed ${cores.textoForte}`, verticalAlign: "middle", marginRight: 4 }} />{tr("planeado")}</span>
        </div>
      </section>

      <section>
        <SecaoTitulo>{tr("Semana a semana")}</SecaoTitulo>
        <Cartao padding={0}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem", minWidth: 760 }}>
              <thead>
                <tr>
                  {["MC", "Datas", "Fase", "Perfil", "Treinos", "Jogos", tr("{0} — planeado", [tr(m.label)]), "Realizado", "%", "Carga interna", "Variação"].map((h, i) => (
                    <th key={i} style={{ ...th, textAlign: i >= 4 ? "right" : "left" }}>{tr(h)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dados.semanas.map((s) => {
                  const v = valorReal(s, metrica), p = metrica === "carga_interna" ? null : s.planeado[metrica];
                  const pct = v != null && p ? Math.round((v / p) * 100) : null;
                  return (
                    <tr key={s.id} style={{ borderTop: `1px solid ${cores.borda}`, background: s.estado === "atual" ? fundoColuna(s) : undefined, color: s.estado === "futuro" ? cores.textoSuave : cores.texto }}>
                      <td style={{ ...td, fontWeight: 700, color: cores.textoForte }}>{s.numero}</td>
                      <td style={td}>{s.inicio.slice(8)}/{s.inicio.slice(5, 7)} – {s.fim.slice(8)}/{s.fim.slice(5, 7)}</td>
                      <td style={td}>{s.fase ? tr(s.fase) : "—"}</td>
                      <td style={td}>{s.perfil ? <Etiqueta cor={COR_PERFIL[s.perfil] ?? cores.textoSuave}>{tr(s.perfil)}</Etiqueta> : "—"}</td>
                      <td style={tdN}>{s.real.n_treinos || "—"}</td>
                      <td style={tdN}>{s.jogos.length ? s.jogos.map((j) => j.resultado ?? (j.adversario ? `vs ${j.adversario}` : "✓")).join(", ") : "—"}</td>
                      <td style={tdN}>{metrica === "carga_interna" ? "—" : fmt(p)}</td>
                      <td style={tdN}>{fmt(v)}</td>
                      <td style={{ ...tdN, fontWeight: 600, color: pct == null ? cores.textoFraco : pct > 115 ? cores.atencao : pct < 85 ? cores.info : cores.sucesso }}>{pct == null ? "—" : `${pct}%`}</td>
                      <td style={tdN}>{fmt(s.real.carga_interna)}</td>
                      <td style={{ ...tdN, color: s.pico ? cores.atencao : undefined, fontWeight: s.pico ? 700 : 400 }}>{s.variacao_pct == null ? "—" : `${s.variacao_pct > 0 ? "+" : ""}${Math.round(s.variacao_pct)}%`}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Cartao>
      </section>
    </div>
  );
}

function Rotulo({ children }: { children: React.ReactNode }) {
  return <div style={{ padding: "8px 12px", fontSize: "0.7rem", fontWeight: 600, color: cores.textoSuave, borderRight: `1px solid ${cores.borda}`, display: "flex", flexDirection: "column", justifyContent: "center", lineHeight: 1.3 }}>{children}</div>;
}

function Resumo({ titulo, valor, sub, alerta }: { titulo: string; valor: string; sub: string; alerta?: boolean }) {
  return (
    <div style={{ border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md, background: cores.bgCartao }}>
      <div style={{ fontSize: "0.74rem", color: cores.textoSuave }}>{titulo}</div>
      <div className="font-display" style={{ fontSize: "1.45rem", fontWeight: 650, color: alerta ? cores.atencao : cores.textoForte, lineHeight: 1.2, marginTop: 2 }}>{valor}</div>
      <div style={{ fontSize: "0.72rem", color: cores.textoFraco }}>{sub}</div>
    </div>
  );
}

const celulaTopo: React.CSSProperties = { padding: "8px 6px", fontSize: "0.7rem", fontWeight: 600, color: cores.textoSuave, borderLeft: `1px solid ${cores.borda}`, boxSizing: "border-box" };
const th: React.CSSProperties = { padding: `9px ${espaco.sm}px`, fontSize: "0.66rem", fontWeight: 600, color: cores.textoSuave, whiteSpace: "nowrap" };
const td: React.CSSProperties = { padding: `7px ${espaco.sm}px`, whiteSpace: "nowrap" };
const tdN: React.CSSProperties = { ...td, textAlign: "right", fontVariantNumeric: "tabular-nums" };
