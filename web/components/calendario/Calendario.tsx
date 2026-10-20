"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { pedidoApi } from "@/lib/api-cliente";
import { cores, espaco, raio } from "@/lib/theme";
import { Cartao, Vazio, estiloBotao } from "@/components/ui/base";

type Contagem = { respondidos: number; total: number } | null;
interface Dia {
  data: string;
  plano: { microciclo: number; perfil: string | null; tipo: string | null; dia_md: string | null; objetivo: string } | null;
  real: {
    tipo: string | null; dia_md: string | null; jogadores: number; pse_media: number | null; duracao_media: number | null;
    distancia_media: number | null; hsr_media: number | null; partilhada: boolean;
  } | null;
  eventos: { id: string; titulo: string; categoria: string }[];
  pse: Contagem;
  wellness: Contagem;
}
interface Resposta {
  inicio: string; fim: string; plantel: number; dias: Dia[];
  resumo: Record<"Treino" | "Jogo" | "Folga", number>;
  extra: [string, number][];
  categorias: string[];
}

const SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];

const COR_MD: Record<string, string> = {
  "MD+1": "#14b8a6", "MD+2": "#0ea5e9", "MD+3": "#0ea5e9",
  "MD-6": "#a855f7", "MD-5": "#a855f7", "MD-4": "#8b5cf6", "MD-3": "#f97316", "MD-2": "#3b82f6", "MD-1": "#22c55e",
  MD: "#ef4444",
};
const COR_PSE = "#f59e0b";
const COR_WELL = "#a78bfa";

function iso(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function semDia(d: Date) {
  return (d.getDay() + 6) % 7; // segunda = 0
}
function somar(d: Date, n: number) {
  const x = new Date(d);
  x.setDate(x.getDate() + n);
  return x;
}

/** Calendário do departamento: plano + o que foi feito em cada dia. */
export function Calendario({ teamId }: { teamId: string }) {
  const [vista, setVista] = useState<"mes" | "semana">("mes");
  const [ancora, setAncora] = useState(() => new Date());
  const [dados, setDados] = useState<Resposta | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [selecionado, setSelecionado] = useState<string>(iso(new Date()));

  // Intervalo visível: mês completo em semanas (seg→dom) ou a semana.
  const [inicio, fim] = useMemo(() => {
    if (vista === "semana") {
      const a = somar(ancora, -semDia(ancora));
      return [a, somar(a, 6)];
    }
    const primeiro = new Date(ancora.getFullYear(), ancora.getMonth(), 1);
    const ultimo = new Date(ancora.getFullYear(), ancora.getMonth() + 1, 0);
    return [somar(primeiro, -semDia(primeiro)), somar(ultimo, 6 - semDia(ultimo))];
  }, [ancora, vista]);

  async function carregar() {
    try {
      setDados(await pedidoApi<Resposta>(`/api/teams/${teamId}/calendario?inicio=${iso(inicio)}&fim=${iso(fim)}`));
      setErro(null);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro inesperado.");
    }
  }
  useEffect(() => {
    carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [teamId, iso(inicio), iso(fim)]);

  function mover(n: number) {
    setAncora((a) => (vista === "semana" ? somar(a, 7 * n) : new Date(a.getFullYear(), a.getMonth() + n, 1)));
  }

  const hoje = iso(new Date());
  const titulo = vista === "mes"
    ? `${MESES[ancora.getMonth()]} ${ancora.getFullYear()}`
    : `${inicio.getDate()} ${MESES[inicio.getMonth()].slice(0, 3)} – ${fim.getDate()} ${MESES[fim.getMonth()].slice(0, 3)} ${fim.getFullYear()}`;
  const porData = new Map((dados?.dias ?? []).map((d) => [d.data, d]));
  const diaSel = porData.get(selecionado);
  // Resumo só do mês (na vista mensal), sem os dias das semanas vizinhas.
  const doPeriodo = (dados?.dias ?? []).filter((d) => vista === "semana" || Number(d.data.slice(5, 7)) === ancora.getMonth() + 1);
  const resumo = { Treino: 0, Jogo: 0, Folga: 0 } as Record<string, number>;
  const extra: Record<string, number> = {};
  for (const d of doPeriodo) {
    const t = d.real?.tipo ?? d.plano?.tipo;
    if (t && t in resumo) resumo[t] += 1;
    for (const e of d.eventos) extra[e.categoria] = (extra[e.categoria] ?? 0) + 1;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: espaco.lg }}>
      <Cartao>
        <div style={{ display: "flex", gap: espaco.sm, alignItems: "center", flexWrap: "wrap" }}>
          <button style={estiloBotao.secundario} onClick={() => mover(-1)} aria-label="Anterior">‹</button>
          <button style={estiloBotao.secundario} onClick={() => { setAncora(new Date()); setSelecionado(hoje); }}>Hoje</button>
          <button style={estiloBotao.secundario} onClick={() => mover(1)} aria-label="Seguinte">›</button>
          <span style={{ fontWeight: 700, color: cores.textoForte, fontSize: "1rem", marginLeft: espaco.sm, textTransform: "capitalize" }}>{titulo}</span>
          <div role="group" aria-label="Vista" style={{ display: "flex", gap: 4, marginLeft: "auto" }}>
            {(["mes", "semana"] as const).map((v) => (
              <button key={v} onClick={() => setVista(v)}
                style={vista === v ? estiloBotao.primario : estiloBotao.secundario}>{v === "mes" ? "Mês" : "Semana"}</button>
            ))}
          </div>
        </div>
      </Cartao>

      {erro && <Vazio>{erro}</Vazio>}

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gap: espaco.lg }} className="cal-grelha">
        <style>{`@media (min-width: 1100px) { .cal-grelha { grid-template-columns: 250px minmax(0, 1fr) !important; } }`}</style>

        {/* Lateral: resumo + dia selecionado */}
        <div style={{ display: "flex", flexDirection: "column", gap: espaco.lg }}>
          <Cartao>
            <Titulo>Resumo do período</Titulo>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: espaco.sm }}>
              {[["Treinos", resumo.Treino], ["Jogos", resumo.Jogo], ["Folgas", resumo.Folga], ["Outros", Object.values(extra).reduce((a, b) => a + b, 0)]].map(([r, v]) => (
                <div key={r} style={{ background: cores.superficie, borderRadius: raio.sm, padding: "6px 10px" }}>
                  <div style={{ fontSize: "0.72rem", color: cores.textoSuave }}>{r}</div>
                  <div style={{ fontSize: "1.1rem", fontWeight: 700, color: cores.textoForte }}>{v}</div>
                </div>
              ))}
            </div>
            {Object.keys(extra).length > 0 && (
              <>
                <Titulo style={{ marginTop: espaco.md }}>Conteúdo extra</Titulo>
                {Object.entries(extra).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
                  <div key={k} style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", color: cores.texto, padding: "2px 0" }}>
                    <span>{k}</span><strong>{v}</strong>
                  </div>
                ))}
              </>
            )}
          </Cartao>
          {dados && (
            <DetalheDia
              key={selecionado}
              data={selecionado}
              dia={diaSel}
              categorias={dados.categorias}
              adicionar={async (titulo, categoria) => {
                await pedidoApi(`/api/teams/${teamId}/calendario/eventos`, "POST", { data: selecionado, titulo, categoria });
                await carregar();
              }}
              apagar={async (id) => {
                await pedidoApi(`/api/teams/${teamId}/calendario/eventos/${id}`, "DELETE");
                await carregar();
              }}
            />
          )}
        </div>

        {/* Grelha */}
        <Cartao padding={0} style={{ overflowX: "auto" }}>
          <div style={{ minWidth: 760 }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(7, minmax(0, 1fr))", borderBottom: `1px solid ${cores.borda}` }}>
              {SEMANA.map((s) => <div key={s} style={{ padding: "8px 0", textAlign: "center", fontSize: "0.76rem", fontWeight: 600, color: cores.textoSuave }}>{s}</div>)}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(7, minmax(0, 1fr))" }}>
              {Array.from({ length: Math.round((fim.getTime() - inicio.getTime()) / 86400000) + 1 }, (_, i) => somar(inicio, i)).map((d, i) => {
                const k = iso(d);
                const dia = porData.get(k);
                const fora = vista === "mes" && d.getMonth() !== ancora.getMonth();
                return (
                  <Celula key={k} data={d} dia={dia} fora={fora} hoje={k === hoje} passado={k < hoje} selecionado={k === selecionado}
                    detalhe={vista === "semana"} primeiraColuna={i % 7 === 0} onClick={() => setSelecionado(k)} />
                );
              })}
            </div>
          </div>
        </Cartao>
      </div>

      <p style={{ fontSize: "0.76rem", color: cores.textoSuave, margin: 0, lineHeight: 1.6 }}>
        O plano de cada dia vem do <Link href="/planeamento/sessoes" style={{ color: cores.textoForte }}>Planeamento → Sessões</Link>; o realizado vem dos dados importados e das respostas dos jogadores.
        Um dia já passado só com plano (sem dados) aparece esbatido.
      </p>
    </div>
  );
}

function rotuloPrincipal(dia?: Dia): { texto: string; cor: string } | null {
  if (!dia) return null;
  const tipo = dia.real?.tipo ?? dia.plano?.tipo;
  const md = dia.real?.dia_md ?? dia.plano?.dia_md;
  const obj = dia.plano?.objetivo;
  if (tipo === "Folga") return { texto: "Folga", cor: cores.textoFraco };
  if (tipo === "Jogo") return { texto: obj ? `Jogo · ${obj}` : "Jogo", cor: COR_MD.MD };
  if (!tipo && !md) return null;
  return { texto: [md, obj || (tipo === "Treino" ? "Treino" : "")].filter(Boolean).join(" · "), cor: (md && COR_MD[md]) || cores.info };
}

function Chip({ cor, children, fraco, title }: { cor: string; children: React.ReactNode; fraco?: boolean; title?: string }) {
  return (
    <div title={title} style={{
      fontSize: "0.7rem", fontWeight: 600, color: cor, background: `color-mix(in srgb, ${cor} 14%, transparent)`,
      border: `1px solid color-mix(in srgb, ${cor} 35%, transparent)`, borderRadius: 5, padding: "2px 6px",
      whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", opacity: fraco ? 0.45 : 1,
    }}>{children}</div>
  );
}

function Celula({ data, dia, fora, hoje, passado, selecionado, detalhe, primeiraColuna, onClick }: {
  data: Date; dia?: Dia; fora: boolean; hoje: boolean; passado: boolean; selecionado: boolean; detalhe: boolean; primeiraColuna: boolean; onClick: () => void;
}) {
  const principal = rotuloPrincipal(dia);
  const semDados = passado && !dia?.real;
  const chips: React.ReactNode[] = [];
  if (principal) chips.push(<Chip key="p" cor={principal.cor} fraco={semDados && principal.texto !== "Folga"} title={principal.texto}>{principal.texto}</Chip>);
  if (dia?.pse && dia.pse.total) chips.push(<Chip key="r" cor={COR_PSE}>PSE {dia.pse.respondidos}/{dia.pse.total}</Chip>);
  if (dia?.wellness && dia.wellness.total) chips.push(<Chip key="w" cor={COR_WELL}>Bem-estar {dia.wellness.respondidos}/{dia.wellness.total}</Chip>);
  for (const e of dia?.eventos ?? []) chips.push(<Chip key={e.id} cor={cores.textoSuave} title={e.categoria}>{e.titulo}</Chip>);
  const max = detalhe ? 12 : 4;

  return (
    <div onClick={onClick} role="button" aria-label={iso(data)}
      style={{
        minHeight: detalhe ? 260 : 112, padding: 6, cursor: "pointer", display: "flex", flexDirection: "column", gap: 3,
        borderTop: `1px solid ${cores.borda}`, borderLeft: primeiraColuna ? "none" : `1px solid ${cores.borda}`,
        background: selecionado ? cores.acentoSuave : fora ? cores.superficie : undefined, opacity: fora ? 0.6 : 1,
      }}>
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <span style={{
          fontSize: "0.76rem", fontWeight: 600, minWidth: 22, height: 22, display: "inline-flex", alignItems: "center", justifyContent: "center",
          borderRadius: 11, color: hoje ? cores.sobreAcento : cores.textoSuave, background: hoje ? cores.acento : "transparent",
        }}>{data.getDate()}</span>
      </div>
      {chips.slice(0, max)}
      {chips.length > max && <span style={{ fontSize: "0.66rem", color: cores.textoFraco }}>+{chips.length - max} mais</span>}
      {detalhe && dia?.real && dia.real.tipo && (
        <div style={{ fontSize: "0.7rem", color: cores.textoSuave, lineHeight: 1.6, marginTop: 4 }}>
          {dia.real.jogadores} jogadores
          {dia.real.duracao_media != null && <><br />{dia.real.duracao_media} min</>}
          {dia.real.pse_media != null && <><br />PSE {dia.real.pse_media.toLocaleString("pt-PT")}</>}
          {dia.real.distancia_media != null && <><br />{dia.real.distancia_media.toLocaleString("pt-PT")} m</>}
          {dia.real.hsr_media != null && <><br />HSR {dia.real.hsr_media.toLocaleString("pt-PT")} m</>}
        </div>
      )}
    </div>
  );
}

function DetalheDia({ data, dia, categorias, adicionar, apagar }: {
  data: string; dia?: Dia; categorias: string[];
  adicionar: (titulo: string, categoria: string) => Promise<void>; apagar: (id: string) => Promise<void>;
}) {
  const [titulo, setTitulo] = useState("");
  const [categoria, setCategoria] = useState(categorias[0] ?? "Outro");
  const [estado, setEstado] = useState<string | null>(null);
  const d = new Date(`${data}T00:00:00`);
  const principal = rotuloPrincipal(dia);
  return (
    <Cartao>
      <Titulo>{SEMANA[semDia(d)]}, {d.getDate()} de {MESES[d.getMonth()]}</Titulo>
      {principal ? <Chip cor={principal.cor}>{principal.texto}</Chip> : <div style={{ fontSize: "0.8rem", color: cores.textoFraco }}>Sem plano nem dados.</div>}
      {dia?.plano && <div style={{ fontSize: "0.74rem", color: cores.textoSuave, marginTop: 4 }}>MC {String(dia.plano.microciclo).padStart(2, "0")}{dia.plano.perfil ? ` · ${dia.plano.perfil}` : ""}</div>}
      {dia?.real?.tipo && (
        <div style={{ fontSize: "0.78rem", color: cores.texto, marginTop: espaco.sm, lineHeight: 1.6 }}>
          Feito: {dia.real.jogadores} jogadores
          {dia.real.duracao_media != null && ` · ${dia.real.duracao_media} min`}
          {dia.real.pse_media != null && ` · PSE ${dia.real.pse_media.toLocaleString("pt-PT")}`}
          {dia.real.distancia_media != null && ` · ${dia.real.distancia_media.toLocaleString("pt-PT")} m`}
          {dia.real.partilhada && <div style={{ color: cores.textoSuave, fontSize: "0.72rem" }}>Inclui sessões de jogadores noutra equipa.</div>}
        </div>
      )}
      {dia?.eventos.map((e) => (
        <div key={e.id} style={{ display: "flex", justifyContent: "space-between", gap: 6, fontSize: "0.8rem", color: cores.texto, marginTop: 6 }}>
          <span>{e.titulo} <span style={{ color: cores.textoFraco }}>· {e.categoria}</span></span>
          <button style={{ ...estiloBotao.ligacao, color: cores.perigo }} onClick={() => apagar(e.id)} aria-label="Apagar">×</button>
        </div>
      ))}
      <div style={{ marginTop: espaco.md, display: "flex", flexDirection: "column", gap: 6 }}>
        <input value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder="Acrescentar: ex. Prevenção de isquiotibiais" style={campo} />
        <div style={{ display: "flex", gap: 6 }}>
          <select value={categoria} onChange={(e) => setCategoria(e.target.value)} style={{ ...campo, flex: 1 }}>
            {categorias.map((c) => <option key={c}>{c}</option>)}
          </select>
          <button style={estiloBotao.primario} disabled={!titulo.trim()} onClick={async () => {
            setEstado(null);
            try {
              await adicionar(titulo, categoria);
              setTitulo("");
            } catch (e) {
              setEstado(e instanceof Error ? e.message : "Erro.");
            }
          }}>Adicionar</button>
        </div>
        {estado && <span style={{ fontSize: "0.76rem", color: cores.perigo }}>{estado}</span>}
      </div>
    </Cartao>
  );
}

function Titulo({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return <div style={{ fontSize: "0.7rem", fontWeight: 700, color: cores.acento, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: espaco.sm, ...style }}>{children}</div>;
}

const campo: React.CSSProperties = { background: cores.bgCartao, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: cores.textoForte, fontSize: "0.82rem", padding: "6px 8px", height: 32, boxSizing: "border-box", width: "100%" };
