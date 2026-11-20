"use client";

/**
 * Gráficos leves e interativos (SVG/HTML, sem bibliotecas) para os relatórios:
 *  · BarrasJogadores — uma barra por jogador (com segmentos, faixa de
 *    referência e marcador), clicável para abrir o detalhe;
 *  · BarrasAgrupadas — categorias × séries (ex.: posição: jogo vs época);
 *  · Mostrador — meio círculo com a faixa habitual (±1 DP) e o ponteiro;
 *  · Radar — perfis de percentil (0–100) de até 4 jogadores.
 * Cores: as da linguagem de cor da app (theme.ts) e as cores das métricas.
 */
import { useState } from "react";
import { cores, desvio, espaco, estado, raio, letra } from "@/lib/theme";

// ── Dica (tooltip) que segue o rato ──────────────────────────────────────────
function Dica({ x, y, children }: { x: number; y: number; children: React.ReactNode }) {
  return (
    <div role="tooltip" style={{
      position: "fixed", left: x + 14, top: y + 12, zIndex: 50, pointerEvents: "none", maxWidth: 280,
      background: cores.bgElevado, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm,
      padding: "8px 12px", fontSize: letra.pequeno, color: cores.texto, boxShadow: "0 6px 20px rgb(0 0 0 / 0.25)", lineHeight: 1.45,
    }}>{children}</div>
  );
}

function useDica() {
  const [d, setD] = useState<{ x: number; y: number; conteudo: React.ReactNode } | null>(null);
  return {
    dica: d && <Dica x={d.x} y={d.y}>{d.conteudo}</Dica>,
    mostrar: (e: React.MouseEvent, conteudo: React.ReactNode) => setD({ x: e.clientX, y: e.clientY, conteudo }),
    esconder: () => setD(null),
  };
}

// ── Barras por jogador ───────────────────────────────────────────────────────
export interface Segmento { valor: number; cor: string; rotulo?: string }
export interface LinhaBarra {
  id: string;
  rotulo: string;
  sub?: string;
  segmentos: Segmento[];
  /** Texto à direita da barra (ex.: «104 %» ou «639 m»). */
  texto: string;
  corTexto?: string;
  /** Marcador vertical (ex.: o habitual do jogador). */
  marcador?: number | null;
  /** Faixa por trás da barra (ex.: habitual ± 1 DP). */
  faixaLinha?: [number, number] | null;
  esmaecido?: boolean;
  dica?: React.ReactNode;
}

export function BarrasJogadores({ linhas, max, faixa, referencia, onClick, selecionado, larguraRotulo = 150, altura = 18 }: {
  linhas: LinhaBarra[];
  max?: number;
  /** Faixa comum a todas as linhas (ex.: 90–110 % do alvo). */
  faixa?: [number, number] | null;
  /** Linha vertical comum (ex.: 100 % do alvo). */
  referencia?: number | null;
  onClick?: (id: string) => void;
  selecionado?: string | null;
  larguraRotulo?: number;
  altura?: number;
}) {
  const { dica, mostrar, esconder } = useDica();
  const topo = Math.max(
    max ?? 0,
    ...linhas.map((l) => l.segmentos.reduce((s, x) => s + Math.max(0, x.valor), 0)),
    ...linhas.map((l) => l.marcador ?? 0), ...linhas.map((l) => l.faixaLinha?.[1] ?? 0),
    faixa?.[1] ?? 0, referencia ?? 0, 1,
  ) * 1.04;
  const pct = (v: number) => `${Math.max(0, Math.min(100, (v / topo) * 100))}%`;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }} onMouseLeave={esconder}>
      {linhas.map((l) => {
        const ativo = selecionado === l.id;
        return (
          <div key={l.id} role={onClick ? "button" : undefined} tabIndex={onClick ? 0 : undefined}
            onClick={() => onClick?.(l.id)} onKeyDown={(e) => { if (onClick && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); onClick(l.id); } }}
            onMouseMove={(e) => l.dica && mostrar(e, l.dica)} onMouseLeave={esconder}
            style={{ display: "grid", gridTemplateColumns: `${larguraRotulo}px 1fr 64px`, alignItems: "center", gap: espaco.sm,
              padding: "2px 4px", borderRadius: 6, cursor: onClick ? "pointer" : "default", opacity: l.esmaecido ? 0.45 : 1,
              background: ativo ? `color-mix(in srgb, ${cores.acento} 12%, transparent)` : undefined,
              outline: ativo ? `1px solid color-mix(in srgb, ${cores.acento} 45%, transparent)` : undefined }}>
            <span style={{ fontSize: letra.pequeno, color: cores.textoForte, fontWeight: ativo ? 700 : 550, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {l.rotulo}{l.sub && <span style={{ color: cores.textoFraco, fontWeight: 400 }}> · {l.sub}</span>}
            </span>
            <div style={{ position: "relative", height: altura, background: cores.superficie, borderRadius: 4, overflow: "hidden" }}>
              {faixa && <div style={{ position: "absolute", top: 0, bottom: 0, left: pct(faixa[0]), width: `calc(${pct(faixa[1])} - ${pct(faixa[0])})`, background: `color-mix(in srgb, ${estado.ok} 16%, transparent)` }} />}
              {l.faixaLinha && <div style={{ position: "absolute", top: 0, bottom: 0, left: pct(l.faixaLinha[0]), width: `calc(${pct(l.faixaLinha[1])} - ${pct(l.faixaLinha[0])})`, background: `color-mix(in srgb, ${cores.textoSuave} 18%, transparent)` }} />}
              <div style={{ position: "absolute", top: 3, bottom: 3, left: 0, display: "flex", width: "100%" }}>
                {l.segmentos.map((s, i) => (
                  <div key={i} style={{ width: pct(Math.max(0, s.valor)), background: s.cor, borderRadius: i === l.segmentos.length - 1 ? "0 3px 3px 0" : 0, transition: "width 0.35s ease" }} />
                ))}
              </div>
              {referencia != null && <div style={{ position: "absolute", top: 0, bottom: 0, left: pct(referencia), width: 2, background: cores.textoForte, opacity: 0.55 }} />}
              {l.marcador != null && <div title="" style={{ position: "absolute", top: 1, bottom: 1, left: `calc(${pct(l.marcador)} - 1px)`, width: 3, borderRadius: 2, background: cores.textoForte }} />}
            </div>
            <span style={{ fontSize: letra.pequeno, fontWeight: 600, textAlign: "right", color: l.corTexto ?? cores.texto, fontVariantNumeric: "tabular-nums" }}>{l.texto}</span>
          </div>
        );
      })}
      {dica}
    </div>
  );
}

// ── Barras agrupadas (vertical) ──────────────────────────────────────────────
export interface CategoriaBarras {
  rotulo: string;
  sub?: React.ReactNode;
  series: { valor: number | null; cor: string; rotulo: string; texto?: string }[];
}

export function BarrasAgrupadas({ categorias, altura = 170, formato = (v: number) => String(Math.round(v)), onClick }: {
  categorias: CategoriaBarras[];
  altura?: number;
  formato?: (v: number) => string;
  onClick?: (rotulo: string) => void;
}) {
  const { dica, mostrar, esconder } = useDica();
  const max = Math.max(1, ...categorias.flatMap((c) => c.series.map((s) => s.valor ?? 0))) * 1.12;
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: espaco.md, height: altura + 46, paddingTop: 4 }} onMouseLeave={esconder}>
      {categorias.map((c) => (
        <div key={c.rotulo} onClick={() => onClick?.(c.rotulo)} style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", alignItems: "center", cursor: onClick ? "pointer" : "default" }}>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 4, height: altura, width: "100%", justifyContent: "center" }}>
            {c.series.map((s, i) => (
              <div key={i} style={{ flex: 1, maxWidth: 34, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "flex-end", height: "100%" }}
                onMouseMove={(e) => mostrar(e, <><b>{c.rotulo}</b> · {s.rotulo}<br />{s.valor != null ? (s.texto ?? formato(s.valor)) : "—"}</>)}>
                <span style={{ fontSize: letra.legenda, color: cores.textoSuave, marginBottom: 2, fontVariantNumeric: "tabular-nums" }}>{s.valor != null ? (s.texto ?? formato(s.valor)) : ""}</span>
                <div style={{ width: "100%", height: `${((s.valor ?? 0) / max) * 100}%`, minHeight: s.valor ? 2 : 0, background: s.cor, borderRadius: "3px 3px 0 0", transition: "height 0.35s ease" }} />
              </div>
            ))}
          </div>
          <div style={{ borderTop: `1px solid ${cores.borda}`, width: "100%", textAlign: "center", paddingTop: 4, fontSize: letra.pequeno, fontWeight: 600, color: cores.textoForte, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{c.rotulo}</div>
          {c.sub && <div style={{ fontSize: letra.legenda, textAlign: "center" }}>{c.sub}</div>}
        </div>
      ))}
      {dica}
    </div>
  );
}

// ── Mostrador (meio círculo) ─────────────────────────────────────────────────
export function Mostrador({ titulo, valor, texto, unidade, media, dp, min, max, estadoTxt, rodape, invertido }: {
  titulo: string;
  valor: number | null;
  texto: string;
  unidade?: string;
  media: number | null;
  dp: number | null;
  min?: number | null;
  max?: number | null;
  /** alto | baixo | normal | insuficiente */
  estadoTxt?: string;
  rodape?: React.ReactNode;
  invertido?: boolean;
}) {
  const W = 150, H = 86, R = 62, cx = W / 2, cy = 76;
  // Escala à volta da época do jogador (não a partir de zero — senão o ponteiro
  // fica sempre colado ao fim e a faixa habitual quase não se vê).
  const largura = dp != null && dp > 0 ? dp : media != null ? Math.abs(media) * 0.15 || 1 : 1;
  const pontos = [min, max, valor, media != null ? media - 2.2 * largura : null, media != null ? media + 2.2 * largura : null].filter((x): x is number => x != null);
  const lo0 = pontos.length ? Math.min(...pontos) : 0, hi0 = pontos.length ? Math.max(...pontos) : 1;
  const folga = (hi0 - lo0 || 1) * 0.08;
  const lo = Math.max(0, lo0 - folga), hi = hi0 + folga;
  const span = hi - lo || 1;
  const ang = (v: number) => Math.PI * (1 - Math.max(0, Math.min(1, (v - lo) / span)));
  const ponto = (v: number, r = R) => [cx + r * Math.cos(ang(v)), cy - r * Math.sin(ang(v))];
  const arco = (a: number, b: number) => {
    const [x1, y1] = ponto(a), [x2, y2] = ponto(b);
    return `M ${x1} ${y1} A ${R} ${R} 0 0 1 ${x2} ${y2}`;
  };
  const corEst = estadoTxt === "alto" ? desvio.acima : estadoTxt === "baixo" ? desvio.abaixo : cores.textoSuave;
  const [nx, ny] = valor != null ? ponto(valor, R - 8) : [cx, cy];
  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: `${espaco.md}px ${espaco.sm}px`, textAlign: "center", minWidth: 0 }}>
      <div style={{ fontSize: letra.pequeno, fontWeight: 600, color: cores.textoSuave }}>{titulo}</div>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ maxWidth: 170, display: "block", margin: "4px auto 0" }} role="img" aria-label={`${titulo}: ${texto}`}>
        <path d={arco(lo, hi)} stroke={cores.superficieHover} strokeWidth={11} fill="none" strokeLinecap="round" />
        {media != null && dp != null && (
          <path d={arco(Math.max(lo, media - dp), Math.min(hi, media + dp))} stroke={`color-mix(in srgb, ${cores.textoSuave} 45%, transparent)`} strokeWidth={11} fill="none" />
        )}
        {media != null && (() => { const [a, b] = ponto(media, R + 8); const [c, d] = ponto(media, R - 8); return <line x1={a} y1={b} x2={c} y2={d} stroke={cores.textoForte} strokeWidth={1.5} opacity={0.6} />; })()}
        {valor != null && <line x1={cx} y1={cy} x2={nx} y2={ny} stroke={invertido ? cores.textoForte : corEst === cores.textoSuave ? cores.textoForte : corEst} strokeWidth={3} strokeLinecap="round" />}
        <circle cx={cx} cy={cy} r={5} fill={cores.textoForte} />
      </svg>
      <div className="font-display" style={{ fontSize: letra.numero, fontWeight: 700, color: cores.textoForte, lineHeight: 1.1 }}>
        {texto}{unidade && <span style={{ fontSize: letra.pequeno, color: cores.textoSuave, fontWeight: 600 }}> {unidade}</span>}
      </div>
      {estadoTxt && estadoTxt !== "insuficiente" && (
        <span style={{ display: "inline-block", marginTop: 4, fontSize: letra.legenda, fontWeight: 700, padding: "1px 8px", borderRadius: 999,
          color: corEst, background: `color-mix(in srgb, ${corEst} 14%, transparent)` }}>
          {estadoTxt === "alto" ? "▲" : estadoTxt === "baixo" ? "▼" : "•"}
        </span>
      )}
      {rodape && <div style={{ fontSize: letra.legenda, color: cores.textoFraco, marginTop: 4 }}>{rodape}</div>}
    </div>
  );
}

// ── Radar de percentis ───────────────────────────────────────────────────────
export function Radar({ eixos, series, tamanho = 380, marcaMeio = "P50", formatar }: {
  eixos: string[];
  series: { nome: string; cor: string; valores: (number | null)[] }[];
  tamanho?: number;
  /** Rótulo do anel do meio (50). */
  marcaMeio?: string;
  /** Texto da dica para um valor (0–100 na escala do radar). */
  formatar?: (v: number, serie: number, eixo: number) => string;
}) {
  const { dica, mostrar, esconder } = useDica();
  const c = tamanho / 2, R = tamanho / 2 - 78;
  const ang = (i: number) => -Math.PI / 2 + (i * 2 * Math.PI) / eixos.length;
  const pt = (i: number, v: number) => [c + (R * v / 100) * Math.cos(ang(i)), c + (R * v / 100) * Math.sin(ang(i))];
  return (
    <div style={{ position: "relative" }} onMouseLeave={esconder}>
      <svg viewBox={`0 0 ${tamanho} ${tamanho}`} width="100%" style={{ maxWidth: tamanho + 60, display: "block", margin: "0 auto", overflow: "visible" }} role="img" aria-label="Radar">
        {[25, 50, 75, 100].map((n) => (
          <polygon key={n} points={eixos.map((_, i) => pt(i, n).join(",")).join(" ")} fill="none" stroke={cores.borda} strokeWidth={1} />
        ))}
        {eixos.map((e, i) => {
          const [x, y] = pt(i, 100), [lx, ly] = pt(i, 122);
          return (
            <g key={e}>
              <line x1={c} y1={c} x2={x} y2={y} stroke={cores.borda} />
              <text x={lx} y={ly} fontSize={10.5} fill={cores.textoSuave} textAnchor={Math.abs(lx - c) < 8 ? "middle" : lx > c ? "start" : "end"} dominantBaseline="middle">{e}</text>
            </g>
          );
        })}
        <text x={c + 3} y={c - R / 2} fontSize={8.5} fill={cores.textoFraco}>{marcaMeio}</text>
        {series.map((s, si) => (
          <g key={s.nome}>
            <polygon points={s.valores.map((v, i) => pt(i, v ?? 0).join(",")).join(" ")} fill={s.cor} fillOpacity={0.12} stroke={s.cor} strokeWidth={2} />
            {s.valores.map((v, i) => {
              const [x, y] = pt(i, v ?? 0);
              return <circle key={i} cx={x} cy={y} r={3.5} fill={s.cor} onMouseMove={(e) => mostrar(e, <><b>{s.nome}</b> · {eixos[i]}<br />{v != null ? (formatar ? formatar(v, si, i) : `P${Math.round(v)}`) : "—"}</>)} />;
            })}
          </g>
        ))}
      </svg>
      {dica}
    </div>
  );
}

/** Botões de escolha (segmented control). */
export function Escolha<T extends string>({ opcoes, valor, onChange, rotulo }: {
  opcoes: { valor: T; texto: string }[]; valor: T; onChange: (v: T) => void; rotulo?: string;
}) {
  return (
    <div role="radiogroup" aria-label={rotulo} style={{ display: "inline-flex", gap: 2, padding: 4, borderRadius: 8, background: cores.superficie, flexWrap: "wrap" }}>
      {opcoes.map((o) => {
        const ativo = o.valor === valor;
        return (
          <button key={o.valor} role="radio" aria-checked={ativo} onClick={() => onChange(o.valor)}
            style={{ border: "none", borderRadius: 8, padding: "6px 12px", fontSize: letra.pequeno, fontWeight: 600, cursor: "pointer",
              background: ativo ? cores.bgCartao : "transparent", color: ativo ? cores.textoForte : cores.textoSuave,
              boxShadow: ativo ? "0 1px 2px rgb(0 0 0 / 0.14)" : "none", whiteSpace: "nowrap" }}>
            {o.texto}
          </button>
        );
      })}
    </div>
  );
}
