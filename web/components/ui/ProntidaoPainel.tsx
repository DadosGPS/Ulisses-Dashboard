"use client";

import { cores, espaco, raio } from "@/lib/theme";
import { NomeJogador } from "@/components/ui/NomeJogador";
import { useTr } from "@/lib/i18n/cliente";

type ChaveItem = "sono" | "energia" | "dor_musc" | "stress" | "humor" | "prontidao" | "dor";
type EstadoW = "atencao" | "vigiar" | "ok" | "antiga";

interface Item {
  valor: number;
  habitual: number | null;
  diferenca: number | null;
  z_pior: number | null;      // > 0 = pior que o habitual dele (já orientado pela escala)
  base: "md" | "todos" | null;
  n: number;
  semana_passada: number | null;
  extremo: boolean;
}

interface Wellness {
  data: string;
  dias_desde: number;
  dia_md: string | null;
  estado: EstadoW;
  itens: Partial<Record<ChaveItem, Item>>;
  pode_treinar: boolean | null;
  local_dor: string | null;
}

interface JogadorProntidao {
  jogador: string;
  posicao: string;
  estado_jogador: string;
  wellness: Wellness | null;
}

export interface ProntidaoResponse {
  tem_dados: boolean;
  motivo: string | null;
  data_referencia?: string;
  dia_md_hoje?: string | null;
  cobertura?: { wellness_hoje?: number; wellness_atencao?: number; wellness_vigiar?: number; total: number };
  jogadores: JogadorProntidao[];
}

/** Colunas na ordem e na escala do questionário: o número é exatamente o
 * que o jogador escolheu. Só aparecem as que alguém respondeu. */
const ITENS: { chave: ChaveItem; label: string; escala: string }[] = [
  { chave: "energia", label: "Energia", escala: "5 = muita energia" },
  { chave: "dor_musc", label: "Dor muscular", escala: "5 = muita dor" },
  { chave: "sono", label: "Sono", escala: "5 = muito bom" },
  { chave: "prontidao", label: "Prontidão", escala: "5 = muito pronto" },
  { chave: "stress", label: "Stress", escala: "5 = muito stress" },
  { chave: "dor", label: "Dor", escala: "5 = muita dor" },
  { chave: "humor", label: "Humor", escala: "5 = muito bom" },
];

const COR_ESTADO: Record<Exclude<EstadoW, "antiga">, string> = {
  atencao: cores.perigo,
  vigiar: cores.atencao,
  ok: cores.textoFraco,
};
const SECOES: { estado: Exclude<EstadoW, "antiga">; titulo: string }[] = [
  { estado: "atencao", titulo: "Atenção" },
  { estado: "vigiar", titulo: "Vigiar" },
  { estado: "ok", titulo: "Dentro do habitual" },
];
const ESTADO_JOGADOR: Record<string, string> = { lesionado: "lesionado", em_recuperacao: "em recuperação", ausente: "ausente" };

/** Cor da célula: vermelho se ≥ 1,5 DP pior que o habitual dele nesse dia MD
 * (ou na ponta má da escala), laranja se ≥ 1 DP; senão neutra. */
function corItem(i: Item): string | null {
  if (i.extremo || (i.z_pior ?? 0) >= 1.5) return cores.perigo;
  if ((i.z_pior ?? 0) >= 1) return cores.atencao;
  return null;
}

const fmt = (v: number, loc: string) => v.toLocaleString(loc, { maximumFractionDigits: 1 });

export function ProntidaoPainel({ dados }: { dados: ProntidaoResponse }) {
  const tr = useTr();
  const respostasHoje = dados.jogadores.filter((j) => j.wellness && j.wellness.dias_desde === 0);
  const semResposta = dados.jogadores
    .filter((j) => !j.wellness || j.wellness.dias_desde > 0)
    .sort((a, b) => String(a.jogador).localeCompare(String(b.jogador)));
  const colunas = ITENS.filter((c) => respostasHoje.some((j) => j.wellness?.itens[c.chave]));
  const temPode = respostasHoje.some((j) => j.wellness?.pode_treinar != null);
  const temLocal = respostasHoje.some((j) => j.wellness?.local_dor);
  const total = dados.cobertura?.total ?? dados.jogadores.length;
  const nSecao = (e: EstadoW) => respostasHoje.filter((j) => j.wellness?.estado === e).length;
  const pctResp = total ? Math.round((respostasHoje.length / total) * 100) : 0;

  return (
    <div>
      {/* Resumo */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: espaco.md, marginBottom: espaco.lg }}>
        <Cartao rotulo={tr("Responderam hoje")} extra={dados.dia_md_hoje ? <Etiqueta texto={dados.dia_md_hoje} /> : null}>
          <span>{respostasHoje.length}</span>
          <span style={{ fontSize: "0.95rem", color: cores.textoSuave, fontWeight: 500 }}> / {total}</span>
          <div style={{ height: 5, borderRadius: 999, background: cores.superficie, marginTop: 8, overflow: "hidden" }}>
            <div style={{ width: `${pctResp}%`, height: "100%", background: cores.acento, borderRadius: 999 }} />
          </div>
        </Cartao>
        <Cartao rotulo={tr("Atenção")} cor={cores.perigo}><span style={{ color: nSecao("atencao") ? cores.perigo : undefined }}>{nSecao("atencao")}</span></Cartao>
        <Cartao rotulo={tr("Vigiar")} cor={cores.atencao}><span style={{ color: nSecao("vigiar") ? cores.atencao : undefined }}>{nSecao("vigiar")}</span></Cartao>
        <Cartao rotulo={tr("Sem resposta hoje")}><span style={{ color: semResposta.length ? cores.textoForte : cores.textoSuave }}>{semResposta.length}</span></Cartao>
      </div>

      {respostasHoje.length > 0 ? (
        <div style={{ overflowX: "auto", background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, boxShadow: "var(--shadow-card)" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 680 }}>
            <thead>
              <tr>
                <th style={{ ...th, paddingLeft: 18 }}>{tr("Jogador")}</th>
                {colunas.map((c) => (
                  <th key={c.chave} style={{ ...th, textAlign: "center" }}>
                    <div style={{ color: cores.texto, fontWeight: 600 }}>{tr(c.label)}</div>
                    <div style={{ fontWeight: 400, fontSize: "0.66rem", color: cores.textoFraco, marginTop: 2 }}>{tr(c.escala)}</div>
                  </th>
                ))}
                {temPode && <th style={{ ...th, textAlign: "center" }}><div style={{ color: cores.texto, fontWeight: 600 }}>{tr("Pode treinar")}</div></th>}
                {temLocal && <th style={th}><div style={{ color: cores.texto, fontWeight: 600 }}>{tr("Local da dor")}</div></th>}
              </tr>
            </thead>
            {SECOES.map(({ estado, titulo }) => {
              const linhas = respostasHoje
                .filter((j) => j.wellness?.estado === estado)
                .sort((a, b) => maxZ(b) - maxZ(a) || String(a.jogador).localeCompare(String(b.jogador)));
              if (!linhas.length) return null;
              const span = 1 + colunas.length + (temPode ? 1 : 0) + (temLocal ? 1 : 0);
              return (
                <tbody key={estado}>
                  <tr>
                    <td colSpan={span} style={{ padding: "14px 18px 6px", fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", color: estado === "ok" ? cores.textoSuave : COR_ESTADO[estado], borderTop: `1px solid ${cores.borda}` }}>
                      {tr(titulo)} · {linhas.length}
                    </td>
                  </tr>
                  {linhas.map((j) => (
                    <Linha key={j.jogador} j={j} colunas={colunas} temPode={temPode} temLocal={temLocal} />
                  ))}
                </tbody>
              );
            })}
          </table>
        </div>
      ) : (
        <div style={{ padding: espaco.xl, textAlign: "center", color: cores.textoSuave, background: cores.bgCartao, border: `1px dashed ${cores.borda}`, borderRadius: raio.md }}>
          {tr("Ainda ninguém respondeu ao questionário hoje.")}
        </div>
      )}

      <p style={{ fontSize: "0.74rem", color: cores.textoSuave, margin: `${espaco.md}px 2px 0`, lineHeight: 1.6 }}>
        <Ponto cor={cores.perigo} /> {tr("bem pior que o habitual dele neste dia MD ou na ponta má da escala")}
        <span style={{ margin: "0 10px" }} />
        <Ponto cor={cores.atencao} /> {tr("pior que o habitual")}
        <span style={{ margin: "0 10px" }} />
        {tr("O número pequeno é a diferença para o habitual dele. Passa o rato por cima para ver o habitual e a semana passada.")}
      </p>

      {semResposta.length > 0 && (
        <div style={{ marginTop: espaco.lg }}>
          <div style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", color: cores.textoSuave, marginBottom: 8 }}>
            {tr("Sem resposta hoje")} · {semResposta.length}
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {semResposta.map((j) => (
              <span key={j.jogador} style={{ fontSize: "0.78rem", padding: "5px 10px", borderRadius: 999, background: cores.superficie, border: `1px solid ${cores.borda}`, color: cores.texto }}>
                <NomeJogador nome={j.jogador} ficha />
                <span style={{ color: cores.textoFraco }}>
                  {" · "}{j.estado_jogador && j.estado_jogador !== "apto" ? tr(ESTADO_JOGADOR[j.estado_jogador] ?? j.estado_jogador) : j.wellness ? tr("última há {0} d", [j.wellness.dias_desde]) : tr("nunca respondeu")}
                </span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function maxZ(j: JogadorProntidao): number {
  return Math.max(0, ...Object.values(j.wellness?.itens ?? {}).map((i) => (i?.extremo ? 9 : i?.z_pior ?? 0)));
}

function Linha({ j, colunas, temPode, temLocal }: { j: JogadorProntidao; colunas: typeof ITENS; temPode: boolean; temLocal: boolean }) {
  const tr = useTr();
  const w = j.wellness!;
  const corLinha = w.estado === "antiga" ? cores.textoFraco : COR_ESTADO[w.estado];
  return (
    <tr style={{ borderTop: `1px solid ${cores.borda}` }}>
      <td style={{ ...td, paddingLeft: 18, position: "relative" }}>
        <span style={{ position: "absolute", left: 0, top: 8, bottom: 8, width: 3, borderRadius: 3, background: w.estado === "ok" ? "transparent" : corLinha }} />
        <div style={{ fontWeight: 600, color: cores.textoForte }}><NomeJogador nome={j.jogador} ficha /></div>
        {j.posicao && j.posicao !== "—" && <div style={{ fontSize: "0.7rem", color: cores.textoSuave }}>{j.posicao}</div>}
      </td>
      {colunas.map((c) => {
        const i = w.itens[c.chave];
        return <td key={c.chave} style={{ ...td, textAlign: "center" }}>{i ? <Celula i={i} md={w.dia_md} /> : <span style={{ color: cores.textoFraco }}>—</span>}</td>;
      })}
      {temPode && (
        <td style={{ ...td, textAlign: "center" }}>
          {w.pode_treinar == null ? <span style={{ color: cores.textoFraco }}>—</span> : (
            <span style={{
              fontSize: "0.72rem", fontWeight: 700, padding: "3px 10px", borderRadius: 999,
              color: w.pode_treinar ? cores.textoSuave : cores.perigo,
              background: w.pode_treinar ? cores.superficie : `color-mix(in srgb, ${cores.perigo} 14%, transparent)`,
            }}>{w.pode_treinar ? tr("Sim") : tr("Não")}</span>
          )}
        </td>
      )}
      {temLocal && <td style={{ ...td, fontSize: "0.76rem", color: w.local_dor ? cores.texto : cores.textoFraco }}>{w.local_dor ?? "—"}</td>}
    </tr>
  );
}

function Celula({ i, md }: { i: Item; md: string | null }) {
  const tr = useTr();
  const cor = corItem(i);
  const dif = i.diferenca;
  const dica = [
    i.habitual != null
      ? i.base === "md" && md
        ? tr("Habitual dele à {0}: {1} ({2} respostas)", [md, fmt(i.habitual, tr.loc), i.n])
        : tr("Habitual dele (todos os dias): {0} ({1} respostas)", [fmt(i.habitual, tr.loc), i.n])
      : tr("Ainda sem respostas suficientes para o habitual"),
    i.semana_passada != null && md ? tr("{0} da semana passada: {1}", [md, i.semana_passada]) : null,
  ].filter(Boolean).join(" · ");
  return (
    <div title={dica} style={{ display: "inline-flex", flexDirection: "column", alignItems: "center", gap: 2, cursor: "default" }}>
      <span style={{
        width: 38, height: 38, display: "inline-flex", alignItems: "center", justifyContent: "center",
        borderRadius: 10, fontWeight: 700, fontSize: "1rem", fontVariantNumeric: "tabular-nums",
        color: cor ?? cores.textoForte,
        background: cor ? `color-mix(in srgb, ${cor} 16%, transparent)` : cores.superficie,
        border: `1px solid ${cor ? `color-mix(in srgb, ${cor} 45%, transparent)` : cores.borda}`,
      }}>{i.valor}</span>
      <span style={{ fontSize: "0.66rem", height: 12, color: cor ?? cores.textoFraco, fontVariantNumeric: "tabular-nums" }}>
        {dif != null && Math.abs(dif) >= 1 ? `${dif > 0 ? "+" : "−"}${fmt(Math.abs(dif), tr.loc)}` : ""}
      </span>
    </div>
  );
}

function Cartao({ rotulo, cor, extra, children }: { rotulo: string; cor?: string; extra?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: `${espaco.md}px ${espaco.lg}px`, boxShadow: "var(--shadow-card)" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, fontSize: "0.76rem", color: cores.textoSuave }}>
        <span style={{ display: "inline-flex", alignItems: "center", gap: 7 }}>{cor && <Ponto cor={cor} />}{rotulo}</span>
        {extra}
      </div>
      <div className="font-display" style={{ fontSize: "1.7rem", fontWeight: 600, lineHeight: 1.25, marginTop: 4, color: cores.textoForte }}>{children}</div>
    </div>
  );
}

function Etiqueta({ texto }: { texto: string }) {
  return <span style={{ fontSize: "0.68rem", fontWeight: 700, padding: "2px 8px", borderRadius: 999, background: cores.acentoSuave, color: cores.acento }}>{texto}</span>;
}

function Ponto({ cor }: { cor: string }) {
  return <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: cor, verticalAlign: "middle" }} />;
}

const th: React.CSSProperties = { textAlign: "left", padding: "12px 10px 10px", fontSize: "0.74rem", color: cores.textoSuave, fontWeight: 600, verticalAlign: "bottom" };
const td: React.CSSProperties = { padding: "8px 10px", fontSize: "0.84rem", color: cores.texto, verticalAlign: "middle" };
