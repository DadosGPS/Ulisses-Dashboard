"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { pedidoApi } from "@/lib/api-cliente";
import { cores, espaco, raio } from "@/lib/theme";
import { Cartao, Vazio, estiloBotao } from "@/components/ui/base";
import { useTr } from "@/lib/i18n/cliente";
import type { Tr } from "@/lib/i18n/core";

type Contagem = { respondidos: number; total: number } | null;
type Valores = { pse: number | null; duracao_min: number | null; distancia_m: number | null; hsr_m: number | null; sprint_m: number | null };
interface Dia {
  data: string;
  plano: { microciclo: number; perfil: string | null; tipo: string | null; dia_md: string | null; objetivo: string; planeado: Valores; pct?: Record<string, number> } | null;
  real: {
    tipo: string | null; dia_md: string | null; jogadores: number; pse_media: number | null; duracao_media: number | null;
    distancia_media: number | null; hsr_media: number | null; partilhada: boolean;
  } | null;
  eventos: { id: string; titulo: string; categoria: string }[];
  pse: Contagem;
  wellness: Contagem;
}
type InfoMicrociclo = { fatores: Record<string, number>; alvos?: Record<string, number>; pct_semana: Record<string, number> };
interface Resposta {
  inicio: string; fim: string; plantel: number; dias: Dia[];
  microciclos?: Record<string, InfoMicrociclo>;
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
  const tr = useTr();
  // ?data=AAAA-MM-DD abre o calendário nesse dia (ex.: vindo de um microciclo).
  const dataUrl = useSearchParams().get("data");
  const inicial = dataUrl && /^\d{4}-\d{2}-\d{2}$/.test(dataUrl) ? new Date(`${dataUrl}T00:00:00`) : new Date();
  const [vista, setVista] = useState<"mes" | "semana">(dataUrl ? "semana" : "mes");
  const [ancora, setAncora] = useState(() => inicial);
  const [dados, setDados] = useState<Resposta | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [selecionado, setSelecionado] = useState<string>(iso(inicial));

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
      setErro(e instanceof Error ? e.message : tr("Erro inesperado."));
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
    ? `${tr(MESES[ancora.getMonth()])} ${ancora.getFullYear()}`
    : `${inicio.getDate()} ${tr(MESES[inicio.getMonth()]).slice(0, 3)} – ${fim.getDate()} ${tr(MESES[fim.getMonth()]).slice(0, 3)} ${fim.getFullYear()}`;
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
          <button style={estiloBotao.secundario} onClick={() => mover(-1)} aria-label={tr("Anterior")}>‹</button>
          <button style={estiloBotao.secundario} onClick={() => { setAncora(new Date()); setSelecionado(hoje); }}>{tr("Hoje")}</button>
          <button style={estiloBotao.secundario} onClick={() => mover(1)} aria-label={tr("Seguinte")}>›</button>
          <span style={{ fontWeight: 700, color: cores.textoForte, fontSize: "1rem", marginLeft: espaco.sm, textTransform: "capitalize" }}>{titulo}</span>
          <div role="group" aria-label={tr("Vista")} style={{ display: "flex", gap: 4, marginLeft: "auto" }}>
            {(["mes", "semana"] as const).map((v) => (
              <button key={v} onClick={() => setVista(v)}
                style={vista === v ? estiloBotao.primario : estiloBotao.secundario}>{v === "mes" ? tr("Mês") : tr("Semana")}</button>
            ))}
          </div>
        </div>
      </Cartao>

      {erro && <Vazio>{erro}</Vazio>}

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gap: espaco.lg }} className="cal-grelha">
        <style>{tr("@media (min-width: 1100px) { .cal-grelha { grid-template-columns: 250px minmax(0, 1fr) !important; } }")}</style>

        {/* Lateral: resumo + dia selecionado */}
        <div style={{ display: "flex", flexDirection: "column", gap: espaco.lg }}>
          <Cartao>
            <Titulo>{tr("Resumo do período")}</Titulo>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: espaco.sm }}>
              {[["Treinos", resumo.Treino], ["Jogos", resumo.Jogo], ["Folgas", resumo.Folga], ["Outros", Object.values(extra).reduce((a, b) => a + b, 0)]].map(([r, v]) => (
                <div key={r} style={{ background: cores.superficie, borderRadius: raio.sm, padding: "6px 10px" }}>
                  <div style={{ fontSize: "0.72rem", color: cores.textoSuave }}>{tr(String(r))}</div>
                  <div style={{ fontSize: "1.1rem", fontWeight: 700, color: cores.textoForte }}>{v}</div>
                </div>
              ))}
            </div>
            {Object.keys(extra).length > 0 && (
              <>
                <Titulo style={{ marginTop: espaco.md }}>{tr("Conteúdo extra")}</Titulo>
                {Object.entries(extra).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
                  <div key={k} style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", color: cores.texto, padding: "2px 0" }}>
                    <span>{tr(k)}</span><strong>{v}</strong>
                  </div>
                ))}
              </>
            )}
          </Cartao>
          {dados && (
            <DetalheDia
              key={`${selecionado}-${JSON.stringify(diaSel?.plano ?? null)}`}
              data={selecionado}
              dia={diaSel}
              info={diaSel?.plano ? dados.microciclos?.[String(diaSel.plano.microciclo)] : undefined}
              categorias={dados.categorias}
              guardarPlano={async (corpo) => {
                await pedidoApi(`/api/teams/${teamId}/calendario/dia/${selecionado}`, "PUT", corpo);
                await carregar();
              }}
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
              {SEMANA.map((s) => <div key={s} style={{ padding: "8px 0", textAlign: "center", fontSize: "0.76rem", fontWeight: 600, color: cores.textoSuave }}>{tr(s)}</div>)}
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
        {tr("Clica num dia para planear (tipo, dia MD, objetivo, PSE, minutos e carga externa) ou registar o que foi feito. Os dias têm de pertencer a um microciclo — cria-os em")}{" "}<Link href="/planeamento" style={{ color: cores.textoForte }}>{tr("Planeamento")}</Link>{tr(". O realizado vem dos dados importados e das respostas dos jogadores; um dia já passado só com plano (sem dados) aparece esbatido.")}</p>
    </div>
  );
}

function rotuloPrincipal(dia: Dia | undefined, tr: Tr): { texto: string; cor: string } | null {
  if (!dia) return null;
  const tipo = dia.real?.tipo ?? dia.plano?.tipo;
  const md = dia.real?.dia_md ?? dia.plano?.dia_md;
  const obj = dia.plano?.objetivo;
  if (tipo === "Folga") return { texto: tr("Folga"), cor: cores.textoFraco };
  if (tipo === "Jogo") return { texto: obj ? `${tr("Jogo")} · ${obj}` : tr("Jogo"), cor: COR_MD.MD };
  if (!tipo && !md) return null;
  return { texto: [md, obj || (tipo === "Treino" ? tr("Treino") : "")].filter(Boolean).join(" · "), cor: (md && COR_MD[md]) || cores.info };
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
  const tr = useTr();
  const principal = rotuloPrincipal(dia, tr);
  const semDados = passado && !dia?.real;
  const chips: React.ReactNode[] = [];
  if (principal) chips.push(<Chip key="p" cor={principal.cor} fraco={semDados && principal.texto !== tr("Folga")} title={principal.texto}>{principal.texto}</Chip>);
  if (dia?.pse && dia.pse.total) chips.push(<Chip key="r" cor={COR_PSE}>{tr("PSE")}{" "}{dia.pse.respondidos}/{dia.pse.total}</Chip>);
  if (dia?.wellness && dia.wellness.total) chips.push(<Chip key="w" cor={COR_WELL}>{tr("Bem-estar")}{" "}{dia.wellness.respondidos}/{dia.wellness.total}</Chip>);
  for (const e of dia?.eventos ?? []) chips.push(<Chip key={e.id} cor={cores.textoSuave} title={tr(e.categoria)}>{e.titulo}</Chip>);
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
      {chips.length > max && <span style={{ fontSize: "0.66rem", color: cores.textoFraco }}>+{chips.length - max} {tr("mais")}</span>}
      {detalhe && dia?.plano?.tipo === "Treino" && resumoPlano(tr, dia.plano.planeado, dia.plano.pct) && (
        <div style={{ fontSize: "0.7rem", color: cores.textoSuave, lineHeight: 1.6, marginTop: 4 }}>
          <span style={{ color: cores.textoFraco }}>{tr("Plano:")}</span> {resumoPlano(tr, dia.plano.planeado, dia.plano.pct)}
        </div>
      )}
      {detalhe && dia?.real && dia.real.tipo && (
        <div style={{ fontSize: "0.7rem", color: cores.textoSuave, lineHeight: 1.6, marginTop: 4 }}>
          <span style={{ color: cores.textoFraco }}>{tr("Feito:")}</span> {dia.real.jogadores} {tr("jogadores")}{dia.real.duracao_media != null && <><br />{dia.real.duracao_media} {tr("min")}</>}
          {dia.real.pse_media != null && <><br />{tr("PSE")}{" "}{dia.real.pse_media.toLocaleString(tr.loc)}</>}
          {dia.real.distancia_media != null && <><br />{dia.real.distancia_media.toLocaleString(tr.loc)} m</>}
          {dia.real.hsr_media != null && <><br />{tr("HSR")}{" "}{dia.real.hsr_media.toLocaleString(tr.loc)} m</>}
        </div>
      )}
    </div>
  );
}

function resumoPlano(tr: Tr, p?: Valores, pct?: Record<string, number>) {
  if (!p) return "";
  return [
    p.pse != null ? `PSE ${p.pse.toLocaleString(tr.loc)}` : null,
    p.duracao_min != null ? `${p.duracao_min}′` : null,
    p.pse != null && p.duracao_min != null ? `${Math.round(p.pse * p.duracao_min)} UA` : null,
    ...VARS.filter((v) => pct?.[v.chave] != null).map((v) => `${tr(v.curto)} ${pct![v.chave].toLocaleString(tr.loc)}%`),
  ].filter(Boolean).join(" · ");
}

/** Carga externa do dia em % do objetivo semanal do microciclo. */
const VARS: { chave: string; rotulo: string; curto: string; unidade: string }[] = [
  { chave: "distancia", rotulo: "Distância total", curto: "Dist", unidade: "m" },
  { chave: "hsr", rotulo: "HSR", curto: "HSR", unidade: "m" },
  { chave: "sprint", rotulo: "Sprint", curto: "Sprint", unidade: "m" },
  { chave: "acc", rotulo: "Acelerações", curto: "Acc", unidade: "" },
  { chave: "dcc", rotulo: "Desacelerações", curto: "Dcc", unidade: "" },
];

const OPCOES_MD = ["MD-6", "MD-5", "MD-4", "MD-3", "MD-2", "MD-1", "MD+1", "MD+2", "MD+3"];
const CAMPOS: { chave: keyof Valores; rotulo: string }[] = [
  { chave: "pse", rotulo: "PSE (0–10)" },
  { chave: "duracao_min", rotulo: "Minutos" },
];

type CorpoPlano = { tipo: string; dia_md: string | null; objetivo: string; planeado: Record<string, number | null | Record<string, number | null>>; propagar_md: boolean };

function DetalheDia({ data, dia, info, categorias, guardarPlano, adicionar, apagar }: {
  data: string; dia?: Dia; info?: InfoMicrociclo; categorias: string[];
  guardarPlano: (c: CorpoPlano) => Promise<void>;
  adicionar: (titulo: string, categoria: string) => Promise<void>; apagar: (id: string) => Promise<void>;
}) {
  const tr = useTr();
  const d = new Date(`${data}T00:00:00`);
  const plano = dia?.plano;
  const [tipo, setTipo] = useState(plano?.tipo ?? (plano?.dia_md === "MD" ? "Jogo" : "Treino"));
  const [md, setMd] = useState(plano?.dia_md ?? "");
  const [objetivo, setObjetivo] = useState(plano?.objetivo ?? "");
  const [valores, setValores] = useState<Record<string, string>>(
    Object.fromEntries(CAMPOS.map((c) => [c.chave, plano?.planeado?.[c.chave] != null ? String(plano.planeado[c.chave]) : ""])));
  const [pct, setPct] = useState<Record<string, string>>(
    Object.fromEntries(VARS.map((v) => [v.chave, plano?.pct?.[v.chave] != null ? String(plano.pct[v.chave]) : ""])));
  const [propagar, setPropagar] = useState(true);
  const [titulo, setTitulo] = useState("");
  const [categoria, setCategoria] = useState(categorias[0] ?? "Outro");
  const [estado, setEstado] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);
  const [aGravar, setAGravar] = useState(false);
  const num = (v: string) => (v.trim() === "" ? null : Number(v.replace(",", ".")));
  const ua = (num(valores.pse) ?? 0) * (num(valores.duracao_min) ?? 0);

  return (
    <Cartao>
      <Titulo>{tr("{0}, {1} de {2}", [tr(SEMANA[semDia(d)]), d.getDate(), tr(MESES[d.getMonth()])])}</Titulo>

      {!plano ? (
        <div style={{ fontSize: "0.8rem", color: cores.textoSuave, lineHeight: 1.5 }}>
          {tr("Este dia ainda não pertence a nenhum microciclo. Cria o microciclo em")}{" "}<Link href="/planeamento" style={{ color: cores.textoForte }}>{tr("Planeamento")}</Link> {tr("para o poderes planear aqui.")}</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ fontSize: "0.74rem", color: cores.textoSuave }}>{tr("MC")}{" "}{String(plano.microciclo).padStart(2, "0")}{plano.perfil ? ` · ${plano.perfil}` : ""}</div>
          <div role="group" aria-label={tr("Tipo de dia")} style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 4 }}>
            {["Treino", "Jogo", "Folga"].map((t) => (
              <button key={t} onClick={() => setTipo(t)} style={{ ...(tipo === t ? estiloBotao.primario : estiloBotao.secundario), padding: "5px 0" }}>{tr(t)}</button>
            ))}
          </div>
          {tipo === "Treino" && (
            <Rot texto={tr("Dia MD")}>
              <select value={md} onChange={(e) => setMd(e.target.value)} style={campo}>
                <option value="">—</option>
                {OPCOES_MD.map((m) => <option key={m}>{m}</option>)}
              </select>
            </Rot>
          )}
          {tipo !== "Folga" && (
            <Rot texto={tipo === "Jogo" ? tr("Adversário") : tr("Objetivo")}>
              <input value={objetivo} onChange={(e) => setObjetivo(e.target.value)} placeholder={tipo === "Jogo" ? tr("ex.: vs SD Ribeiras") : tr("ex.: Força, Extensiva")} style={campo} />
            </Rot>
          )}
          {tipo === "Jogo" && (
            <label style={{ display: "flex", gap: 6, alignItems: "flex-start", fontSize: "0.76rem", color: cores.texto, lineHeight: 1.4 }}>
              <input type="checkbox" checked={propagar} onChange={(e) => setPropagar(e.target.checked)} />
              {tr("Contar os dias MD do microciclo a partir deste jogo")}</label>
          )}
          {tipo === "Treino" && (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
                {CAMPOS.map((c) => (
                  <Rot key={c.chave} texto={tr(c.rotulo)}>
                    <input inputMode="decimal" value={valores[c.chave]} onChange={(e) => setValores({ ...valores, [c.chave]: e.target.value })} style={{ ...campo, textAlign: "right" }} />
                  </Rot>
                ))}
                <Rot texto={tr("Carga (UA)")}><div style={{ ...campo, display: "flex", alignItems: "center", justifyContent: "flex-end", background: cores.superficie }}>{ua ? Math.round(ua) : "—"}</div></Rot>
              </div>
              <div style={{ fontSize: "0.72rem", color: cores.textoSuave, fontWeight: 600, marginTop: 4 }}>{tr("Carga externa — % do objetivo semanal")}</div>
              {!info || !Object.keys(info.fatores).length ? (
                <div style={{ fontSize: "0.74rem", color: cores.atencao, lineHeight: 1.4 }}>
                  {tr("Define o fator semanal deste microciclo em")}{" "}<Link href="/planeamento" style={{ color: cores.textoForte }}>{tr("Planeamento")}</Link> {tr("para veres a que valores correspondem as percentagens.")}</div>
              ) : null}
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {VARS.map((v) => {
                  const atual = num(pct[v.chave]);
                  const guardado = plano?.pct?.[v.chave] ?? 0;
                  const semana = (info?.pct_semana?.[v.chave] ?? 0) - guardado + (atual ?? 0);
                  const alvo = info?.alvos?.[v.chave];
                  const semFator = info && !(v.chave in (info.fatores ?? {}));
                  return (
                    <div key={v.chave} style={{ display: "grid", gridTemplateColumns: "1fr 64px", gap: 6, alignItems: "center" }}>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontSize: "0.76rem", color: cores.texto, fontWeight: 600 }}>{tr(v.rotulo)}</div>
                        <div style={{ fontSize: "0.68rem", color: cores.textoFraco, lineHeight: 1.3 }}>
                          {semFator ? tr("sem fator semanal") : alvo != null && atual != null ? `≈ ${Math.round((alvo * atual) / 100).toLocaleString(tr.loc)}${v.unidade ? ` ${v.unidade}` : ""} · ` : ""}
                          {!semFator && <span style={{ color: semana > 100.5 ? cores.perigo : semana >= 95 ? cores.sucesso : cores.textoFraco }}>{tr("semana")}{" "}{semana.toLocaleString(tr.loc, { maximumFractionDigits: 1 })}%</span>}
                        </div>
                      </div>
                      <div style={{ position: "relative" }}>
                        <input inputMode="decimal" aria-label={tr("{0} (% do objetivo semanal)", [tr(v.rotulo)])} value={pct[v.chave]}
                          onChange={(e) => setPct({ ...pct, [v.chave]: e.target.value.replace(",", ".") })}
                          style={{ ...campo, textAlign: "right", paddingRight: 20 }} />
                        <span style={{ position: "absolute", right: 7, top: "50%", transform: "translateY(-50%)", fontSize: "0.74rem", color: cores.textoFraco }}>%</span>
                      </div>
                    </div>
                  );
                })}
              </div>
              <span style={{ fontSize: "0.7rem", color: cores.textoFraco, lineHeight: 1.4 }}>
                {tr("Valores por jogador. “Semana” soma as % de todos os treinos do microciclo — o objetivo é chegar a 100 %.")}</span>
            </>
          )}
          <button style={estiloBotao.primario} disabled={aGravar} onClick={async () => {
            setEstado(null);
            setAGravar(true);
            try {
              await guardarPlano({
                tipo, dia_md: tipo === "Treino" ? md || null : null, objetivo,
                planeado: {
                  ...Object.fromEntries(CAMPOS.map((c) => [c.chave, num(valores[c.chave])])),
                  pct: Object.fromEntries(VARS.map((v) => [v.chave, num(pct[v.chave])])),
                },
                propagar_md: tipo === "Jogo" && propagar,
              });
              setEstado({ tipo: "ok", texto: tr("Plano do dia guardado.") });
            } catch (e) {
              setEstado({ tipo: "erro", texto: e instanceof Error ? e.message : tr("Erro.") });
            } finally {
              setAGravar(false);
            }
          }}>{aGravar ? tr("A guardar…") : tr("Guardar plano do dia")}</button>
          {estado && <span style={{ fontSize: "0.76rem", color: estado.tipo === "ok" ? cores.sucesso : cores.perigo }}>{estado.texto}</span>}
        </div>
      )}

      {dia?.real?.tipo && (
        <div style={{ fontSize: "0.78rem", color: cores.texto, marginTop: espaco.md, paddingTop: espaco.sm, borderTop: `1px solid ${cores.borda}`, lineHeight: 1.6 }}>
          <strong>{tr("Feito:")}</strong> {dia.real.jogadores} {tr("jogadores")}{dia.real.duracao_media != null && tr(" · {0} min", [dia.real.duracao_media])}
          {dia.real.pse_media != null && tr(" · PSE {0}", [dia.real.pse_media.toLocaleString(tr.loc)])}
          {dia.real.distancia_media != null && ` · ${dia.real.distancia_media.toLocaleString(tr.loc)} m`}
          {dia.real.hsr_media != null && tr(" · HSR {0} m", [dia.real.hsr_media.toLocaleString(tr.loc)])}
          {dia.real.partilhada && <div style={{ color: cores.textoSuave, fontSize: "0.72rem" }}>{tr("Inclui sessões de jogadores noutra equipa.")}</div>}
        </div>
      )}

      <div style={{ marginTop: espaco.md, paddingTop: espaco.sm, borderTop: `1px solid ${cores.borda}` }}>
        <div style={{ fontSize: "0.72rem", color: cores.textoSuave, fontWeight: 600, marginBottom: 4 }}>{tr("Mais neste dia")}</div>
        {dia?.eventos.map((e) => (
          <div key={e.id} style={{ display: "flex", justifyContent: "space-between", gap: 6, fontSize: "0.8rem", color: cores.texto, marginTop: 4 }}>
            <span>{e.titulo} <span style={{ color: cores.textoFraco }}>· {tr(e.categoria)}</span></span>
            <button style={{ ...estiloBotao.ligacao, color: cores.perigo }} onClick={() => apagar(e.id)} aria-label={tr("Apagar")}>×</button>
          </div>
        ))}
        <div style={{ marginTop: 6, display: "flex", flexDirection: "column", gap: 6 }}>
          <input value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder={tr("ex.: Prevenção de isquiotibiais")} style={campo} />
          <div style={{ display: "flex", gap: 6 }}>
            <select value={categoria} onChange={(e) => setCategoria(e.target.value)} style={{ ...campo, flex: 1 }}>
              {categorias.map((c) => <option key={c} value={c}>{tr(c)}</option>)}
            </select>
            <button style={estiloBotao.secundario} disabled={!titulo.trim()} onClick={async () => {
              setEstado(null);
              try {
                await adicionar(titulo, categoria);
                setTitulo("");
              } catch (e) {
                setEstado({ tipo: "erro", texto: e instanceof Error ? e.message : tr("Erro.") });
              }
            }}>{tr("Adicionar")}</button>
          </div>
        </div>
      </div>
    </Cartao>
  );
}

function Rot({ texto, children }: { texto: string; children: React.ReactNode }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 3, fontSize: "0.7rem", color: cores.textoSuave, fontWeight: 500 }}>
      {texto}
      {children}
    </label>
  );
}

function Titulo({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return <div style={{ fontSize: "0.7rem", fontWeight: 700, color: cores.acento, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: espaco.sm, ...style }}>{children}</div>;
}

const campo: React.CSSProperties = { background: cores.bgCartao, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: cores.textoForte, fontSize: "0.82rem", padding: "6px 8px", height: 32, boxSizing: "border-box", width: "100%" };
