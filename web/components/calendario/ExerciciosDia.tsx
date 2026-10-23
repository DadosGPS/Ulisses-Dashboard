"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { pedidoApi } from "@/lib/api-cliente";
import { cores, raio } from "@/lib/theme";
import { estiloBotao } from "@/components/ui/base";
import { useTr } from "@/lib/i18n/cliente";

export type ItemExercicio = { id?: string; nome: string; minutos: number };
type ExBib = { id: string | null; nome: string; categoria: string | null; duracao_min: number | null; gps: { n: number; duracao_min?: number }; por_min: Record<string, number>; fonte: string | null };

const METRICAS = [
  { chave: "distancia", rotulo: "Dist", unidade: "m" },
  { chave: "hsr", rotulo: "HSR", unidade: "m" },
  { chave: "sprint", rotulo: "Sprint", unidade: "m" },
  { chave: "acc", rotulo: "Acc", unidade: "" },
  { chave: "dcc", rotulo: "Dcc", unidade: "" },
];

// A biblioteca muda pouco: um pedido por equipa enquanto a página está aberta.
const cache = new Map<string, Promise<ExBib[]>>();
function carregarBiblioteca(teamId: string) {
  if (!cache.has(teamId)) {
    cache.set(teamId, pedidoApi<{ exercicios: ExBib[] }>(`/api/academia/exercicios?team_id=${teamId}`).then((d) => d.exercicios ?? []).catch(() => []));
  }
  return cache.get(teamId)!;
}
const chave = (s: string) => s.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();

/** Exercícios planeados para o dia e a carga prevista por jogador
 * (soma de «por minuto» × minutos, com a carga típica de cada exercício). */
export function ExerciciosDia({ teamId, itens, onChange, alvos, onUsarComoPct }: {
  teamId: string;
  itens: ItemExercicio[];
  onChange: (itens: ItemExercicio[]) => void;
  /** Objetivo semanal absoluto por variável (fator × referência de jogo). */
  alvos?: Record<string, number>;
  onUsarComoPct?: (pct: Record<string, number>) => void;
}) {
  const tr = useTr();
  const [bib, setBib] = useState<ExBib[] | null>(null);
  const [escolha, setEscolha] = useState("");
  useEffect(() => { carregarBiblioteca(teamId).then(setBib); }, [teamId]);

  const porNome = new Map((bib ?? []).map((e) => [chave(e.nome), e]));
  const achar = (it: ItemExercicio) => (it.id && bib?.find((e) => e.id === it.id)) || porNome.get(chave(it.nome));
  const total: Record<string, number> = {};
  const semDados: string[] = [];
  for (const it of itens) {
    const e = achar(it);
    if (!e || !Object.keys(e.por_min).length) { semDados.push(it.nome); continue; }
    for (const [k, v] of Object.entries(e.por_min)) total[k] = (total[k] ?? 0) + v * it.minutos;
  }
  const minutos = itens.reduce((s, i) => s + i.minutos, 0);
  const pctPrevisto = Object.fromEntries(Object.entries(total).filter(([k]) => alvos?.[k]).map(([k, v]) => [k, Math.round((v / alvos![k]) * 1000) / 10]));

  function juntar() {
    const e = bib?.find((x) => (x.id ?? `gps:${x.nome}`) === escolha);
    if (!e) return;
    onChange([...itens, { ...(e.id ? { id: e.id } : {}), nome: e.nome, minutos: Math.round(e.duracao_min ?? e.gps.duracao_min ?? 10) }]);
    setEscolha("");
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <span style={{ fontSize: "0.72rem", color: cores.textoSuave, fontWeight: 600 }}>{tr("Exercícios da sessão")}</span>
        <Link href="/planeamento/exercicios" style={{ fontSize: "0.7rem", color: cores.acento }}>{tr("Biblioteca")}</Link>
      </div>
      {itens.map((it, i) => (
        <div key={`${it.nome}-${i}`} style={{ display: "grid", gridTemplateColumns: "1fr 58px 22px", gap: 6, alignItems: "center" }}>
          <span style={{ fontSize: "0.78rem", color: cores.texto, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={it.nome}>{it.nome}</span>
          <div style={{ position: "relative" }}>
            <input inputMode="numeric" aria-label={tr("Minutos de {0}", [it.nome])} value={it.minutos || ""}
              onChange={(e) => onChange(itens.map((x, j) => (j === i ? { ...x, minutos: Number(e.target.value.replace(/\D/g, "")) || 0 } : x)))}
              style={{ ...campo, textAlign: "right", paddingRight: 24 }} />
            <span style={{ position: "absolute", right: 6, top: "50%", transform: "translateY(-50%)", fontSize: "0.66rem", color: cores.textoFraco }}>min</span>
          </div>
          <button aria-label={tr("Tirar {0}", [it.nome])} onClick={() => onChange(itens.filter((_, j) => j !== i))}
            style={{ ...estiloBotao.ligacao, color: cores.textoFraco, fontSize: "0.9rem" }}>×</button>
        </div>
      ))}
      <div style={{ display: "flex", gap: 6 }}>
        <select value={escolha} onChange={(e) => setEscolha(e.target.value)} style={{ ...campo, flex: 1 }} aria-label={tr("Juntar exercício")}>
          <option value="">{bib == null ? tr("A carregar…") : bib.length ? tr("+ juntar exercício…") : tr("Biblioteca vazia")}</option>
          {(bib ?? []).map((e) => <option key={e.id ?? `gps:${e.nome}`} value={e.id ?? `gps:${e.nome}`}>{e.nome}{e.fonte ? "" : ` (${tr("sem carga")})`}</option>)}
        </select>
        <button style={estiloBotao.secundario} disabled={!escolha} onClick={juntar}>{tr("Juntar")}</button>
      </div>
      {itens.length > 0 && (
        <div style={{ background: cores.superficie, borderRadius: raio.sm, padding: "7px 9px", fontSize: "0.74rem", color: cores.texto, lineHeight: 1.5 }}>
          <div style={{ fontWeight: 600, marginBottom: 2 }}>{tr("Previsto por jogador · {0} min", [minutos])}</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "2px 10px" }}>
            {METRICAS.filter((m) => total[m.chave] != null).map((m) => (
              <span key={m.chave}>
                {m.rotulo} <strong>{Math.round(total[m.chave]).toLocaleString(tr.loc)}{m.unidade ? ` ${m.unidade}` : ""}</strong>
                {pctPrevisto[m.chave] != null && <span style={{ color: cores.textoSuave }}> · {pctPrevisto[m.chave].toLocaleString(tr.loc)}%</span>}
              </span>
            ))}
          </div>
          {semDados.length > 0 && <div style={{ color: cores.textoSuave }}>{tr("Sem carga conhecida: {0}", [semDados.join(", ")])}</div>}
          {onUsarComoPct && Object.keys(pctPrevisto).length > 0 && (
            <button onClick={() => onUsarComoPct(pctPrevisto)} style={{ ...estiloBotao.ligacao, fontSize: "0.74rem", marginTop: 2 }}>
              {tr("Usar como % do objetivo semanal")}</button>
          )}
        </div>
      )}
    </div>
  );
}

const campo: React.CSSProperties = { background: cores.bgCartao, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: cores.textoForte, fontSize: "0.8rem", padding: "5px 7px", height: 30, width: "100%", boxSizing: "border-box" };
