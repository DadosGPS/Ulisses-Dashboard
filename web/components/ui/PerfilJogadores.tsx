"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { espaco, raio, cores } from "@/lib/theme";
import type { PerfilResponse } from "@/lib/types";
import { useTr } from "@/lib/i18n/cliente";
import { EstadoVazio } from "@/components/ui/base";

const TINTA = cores.texto;
const TINTA_SUAVE = cores.textoSuave;

// STEN 1–10, diverging à volta de 5.5: âmbar (abaixo da média do plantel) →
// neutro → azul (acima). Azul/âmbar é seguro para daltonismo.
function corSten(sten: number | null): { bg: string; fg: string } {
  if (sten === null || sten === undefined) return { bg: cores.superficie, fg: cores.textoFraco };
  const t = Math.max(-1, Math.min(1, (sten - 5.5) / 4.5)); // -1 (=1) … +1 (=10)
  const k = Math.abs(t);
  const cor = t >= 0 ? "rgb(37, 99, 235)" : "rgb(217, 119, 6)";
  const bg = `color-mix(in srgb, ${cor} ${Math.round(k * 100)}%, var(--bg-cartao))`;
  return { bg, fg: k > (t >= 0 ? 0.55 : 0.6) ? "#ffffff" : TINTA };
}

type Metrica = PerfilResponse["metricas"][number];

function fmtValor(v: number | null | undefined, m: Metrica, loc: string): string {
  if (v == null) return "—";
  if (m.chave === "corrida_1km_s") return `${Math.floor(v / 60)}:${String(Math.round(v % 60)).padStart(2, "0")}`;
  const casas = m.casas ?? 1;
  return v.toLocaleString(loc, { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

const rotuloCurto = (label: string) => label.replace(/^Drop jump — /, "DJ ");

export function PerfilJogadores({ dados }: { dados: PerfilResponse }) {
  const tr = useTr();
  const { oculto } = usePrivacidade();
  const router = useRouter();
  const pathname = usePathname();
  const [ver, setVer] = useState<"valor" | "sten">("valor");
  const [ordem, setOrdem] = useState<string>("sten_medio");
  const academia = dados.fonte === "academia";

  const jogadores = useMemo(() => {
    const l = [...dados.jogadores];
    if (ordem === "nome") return l.sort((a, b) => a.jogador.localeCompare(b.jogador));
    if (ordem === "sten_medio") return l.sort((a, b) => (b.sten_medio ?? -1) - (a.sten_medio ?? -1));
    return l.sort((a, b) => (b.testes[ordem]?.sten ?? -1) - (a.testes[ordem]?.sten ?? -1));
  }, [dados.jogadores, ordem]);

  if (!dados.tem_dados) {
    return (
      <EstadoVazio acao={{ href: "/academia", label: tr("Ir para a Academia") }}
        mensagem={tr("Ainda não há testes registados para esta equipa. Regista os testes de velocidade, 1 km e saltos na Academia → equipa → Registar testes.")} />
    );
  }

  const grupos: { grupo: string; n: number }[] = [];
  for (const m of dados.metricas) {
    const ult = grupos[grupos.length - 1];
    if (ult && ult.grupo === m.grupo) ult.n += 1;
    else grupos.push({ grupo: m.grupo, n: 1 });
  }
  const mudarMomento = (m: string) => router.replace(m ? `${pathname}?momento=${m}` : pathname, { scroll: false });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: espaco.md }}>
      <div style={{ display: "flex", gap: espaco.md, flexWrap: "wrap", alignItems: "center" }}>
        {academia && (
          <div role="group" aria-label={tr("Momento de avaliação")} style={{ display: "flex", gap: 4 }}>
            {[{ v: "", l: tr("Último") }, ...[1, 2, 3, 4].map((m) => ({ v: String(m), l: `T${m}` }))].map((o) => {
              const ativo = String(dados.momento ?? "") === o.v;
              const tem = !o.v || (dados.momentos ?? []).includes(Number(o.v));
              return (
                <button key={o.v || "ultimo"} disabled={!tem} onClick={() => mudarMomento(o.v)} aria-pressed={ativo}
                  style={{ ...pilula, borderColor: ativo ? cores.acento : cores.bordaForte, color: ativo ? cores.textoForte : tem ? cores.textoSuave : cores.textoFraco,
                    background: ativo ? `color-mix(in srgb, ${cores.acento} 14%, transparent)` : "transparent", fontWeight: ativo ? 600 : 400, cursor: tem ? "pointer" : "default" }}>
                  {o.l}
                </button>
              );
            })}
          </div>
        )}
        <div role="group" aria-label={tr("Mostrar")} style={{ display: "flex", gap: 4, marginLeft: "auto" }}>
          {(["valor", "sten"] as const).map((v) => (
            <button key={v} onClick={() => setVer(v)} aria-pressed={ver === v}
              style={{ ...pilula, borderColor: ver === v ? cores.acento : cores.bordaForte, color: ver === v ? cores.textoForte : cores.textoSuave, fontWeight: ver === v ? 600 : 400 }}>
              {v === "valor" ? tr("Valores") : "STEN"}
            </button>
          ))}
        </div>
      </div>

      <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ borderCollapse: "separate", borderSpacing: 2, fontSize: "0.8rem", fontVariantNumeric: "tabular-nums" }}>
            <thead>
              <tr>
                <th style={{ ...fixa, background: cores.bgCartao }} />
                <th />
                {grupos.map((g) => (
                  <th key={g.grupo} colSpan={g.n} style={{ ...cabecalho, borderBottom: `1px solid ${cores.borda}`, color: cores.textoSuave }}>{tr(g.grupo)}</th>
                ))}
              </tr>
              <tr>
                <th onClick={() => setOrdem("nome")} style={{ ...fixa, background: cores.bgCartao, textAlign: "left", fontSize: "0.72rem", color: TINTA_SUAVE, cursor: "pointer" }}>
                  {tr("Jogador · Posição")}{ordem === "nome" ? " ↓" : ""}</th>
                <th onClick={() => setOrdem("sten_medio")} style={{ ...cabecalho, cursor: "pointer" }} title={tr("Média dos STEN de todos os testes")}>
                  {tr("STEN médio")}{ordem === "sten_medio" ? " ↓" : ""}</th>
                {dados.metricas.map((m) => (
                  <th key={m.chave} onClick={() => setOrdem(m.chave)} style={{ ...cabecalho, cursor: "pointer" }}
                    title={tr(m.maior_melhor ? "Maior é melhor" : "Menor é melhor")}>
                    {tr(rotuloCurto(m.label))}{m.unidade ? <span style={{ fontWeight: 400, color: cores.textoFraco }}> {m.chave === "corrida_1km_s" ? "m:ss" : m.unidade}</span> : null}
                    {ordem === m.chave ? " ↓" : ""}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {jogadores.map((j) => (
                <tr key={j.jogador}>
                  <td style={{ ...fixa, background: cores.bgCartao, whiteSpace: "nowrap" }}>
                    {j.atleta_id ? (
                      <Link href={`/academia/atleta/${j.atleta_id}`} style={{ fontWeight: 600, color: TINTA, textDecoration: "none" }}>{nomeOuOculto(j.jogador, oculto)}</Link>
                    ) : <span style={{ fontWeight: 600, color: TINTA }}>{nomeOuOculto(j.jogador, oculto)}</span>}
                    {j.posicao && j.posicao !== "—" && <span style={{ color: cores.textoFraco, fontSize: "0.72rem" }}> · {j.posicao}</span>}
                  </td>
                  {(() => {
                    const c = corSten(j.sten_medio);
                    return <td style={{ ...celula, background: c.bg, color: c.fg, fontWeight: 700 }}>{j.sten_medio ?? "—"}</td>;
                  })()}
                  {dados.metricas.map((m) => {
                    const t = j.testes[m.chave];
                    const c = corSten(t?.sten ?? null);
                    return (
                      <td key={m.chave}
                        title={t ? tr("{0}: {1}{2} · STEN {3}", [tr(m.label), fmtValor(t.valor, m, tr.loc), m.unidade && m.chave !== "corrida_1km_s" ? " " + m.unidade : "", t.sten ?? "—"]) + (t.data ? ` · ${t.data}` : "") : tr("sem dados")}
                        style={{ ...celula, background: c.bg, color: c.fg, fontWeight: ver === "valor" ? 600 : 500 }}>
                        {t ? (ver === "valor" ? fmtValor(t.valor, m, tr.loc) : t.sten ?? "—") : "—"}
                      </td>
                    );
                  })}
                </tr>
              ))}
              {dados.medias && (
                <tr>
                  <td style={{ ...fixa, background: cores.bgCartao, fontWeight: 700, color: cores.textoForte, borderTop: `1px solid ${cores.bordaForte}` }}>{tr("Média da equipa")}</td>
                  <td style={{ ...celula, borderTop: `1px solid ${cores.bordaForte}` }} />
                  {dados.metricas.map((m) => (
                    <td key={m.chave} style={{ ...celula, fontWeight: 700, color: cores.textoForte, borderTop: `1px solid ${cores.bordaForte}` }}
                      title={tr("{0} jogador(es) com este teste", [dados.medias?.[m.chave]?.n ?? 0])}>
                      {fmtValor(dados.medias?.[m.chave]?.media, m, tr.loc)}
                    </td>
                  ))}
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      {!!dados.sem_testes?.length && (
        <p style={{ fontSize: "0.78rem", color: cores.textoSuave, margin: 0 }}>
          {tr("Sem testes neste momento: {0}", [dados.sem_testes.map((n) => nomeOuOculto(n, oculto)).join(", ")])}</p>
      )}
      <p style={{ fontSize: "0.74rem", color: cores.textoSuave, margin: 0, lineHeight: 1.5 }}>
        {tr("A cor de cada célula é o STEN (1–10) do jogador nesse teste face ao plantel: azul = acima da média da equipa, âmbar = abaixo. Nos tempos (velocidade, 1 km, contacto) menos é melhor — já está tido em conta. Clica num cabeçalho para ordenar.")}
        {academia && <> {tr("Testes registados na Academia; «Último» usa o valor mais recente da época de cada teste.")}</>}
      </p>
    </div>
  );
}

const pilula: React.CSSProperties = { border: "1px solid", borderRadius: 999, padding: "4px 12px", fontSize: "0.78rem", background: "transparent" };
const fixa: React.CSSProperties = { position: "sticky", left: 0, zIndex: 1, padding: "6px 10px", minWidth: 170 };
const cabecalho: React.CSSProperties = { minWidth: 66, textAlign: "center", padding: "6px 4px", fontSize: "0.7rem", color: TINTA_SUAVE, fontWeight: 600, verticalAlign: "bottom", whiteSpace: "nowrap" };
const celula: React.CSSProperties = { minWidth: 66, textAlign: "center", height: 32, borderRadius: 4, padding: "0 6px" };
