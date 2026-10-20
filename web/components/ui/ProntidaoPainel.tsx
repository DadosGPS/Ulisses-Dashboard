"use client";

import { cores, espaco, raio } from "@/lib/theme";
import { NomeJogador } from "@/components/ui/NomeJogador";

type Estado = "reduzir" | "vigiar" | "pronto" | "indisponivel";

interface Sinal {
  componente: "cmj" | "hooper" | "acwr";
  severidade: number;
  texto: string;
}

interface JogadorProntidao {
  jogador: string;
  posicao: string;
  estado: Estado;
  estado_jogador: string;
  pontuacao: number;
  sinais: Sinal[];
  cmj: { ultimo: number; data: string; media_base: number | null; variacao_pct: number | null; dias_desde: number; valido: boolean } | null;
  hooper: { ultimo: number; data: string; media_base: number | null; diferenca: number | null; dias_desde: number; valido: boolean } | null;
  acwr: { atual: number; ha_7_dias: number | null; tendencia: "a_subir" | "a_descer" | "estavel" | null; serie: number[] } | null;
}

export interface ProntidaoResponse {
  tem_dados: boolean;
  motivo: string | null;
  data_referencia?: string;
  cobertura?: { cmj: number; hooper: number; total: number };
  limites?: Record<string, number>;
  resumo?: Record<Estado, number>;
  jogadores: JogadorProntidao[];
}

const COR: Record<Estado, string> = {
  reduzir: cores.perigo,
  vigiar: cores.atencao,
  pronto: cores.sucesso,
  indisponivel: cores.textoFraco,
};
const LABEL: Record<Estado, string> = {
  reduzir: "Reduzir carga",
  vigiar: "Vigiar",
  pronto: "Pronto",
  indisponivel: "Indisponível",
};
const ESTADO_JOGADOR: Record<string, string> = {
  lesionado: "lesionado",
  em_recuperacao: "em recuperação",
  ausente: "ausente",
};

export function ProntidaoPainel({ dados }: { dados: ProntidaoResponse }) {
  const resumo = dados.resumo ?? { reduzir: 0, vigiar: 0, pronto: 0, indisponivel: 0 };
  const cob = dados.cobertura;
  const lim = dados.limites ?? {};
  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, boxShadow: "var(--shadow-card)", marginBottom: espaco.lg }}>
        {(["reduzir", "vigiar", "pronto", "indisponivel"] as Estado[]).map((e, i) => (
          <div key={e} style={{ padding: `${espaco.md}px ${espaco.lg}px`, borderLeft: i ? `1px solid ${cores.borda}` : "none" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 7, fontSize: "0.76rem", color: cores.textoSuave }}>
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: COR[e] }} />
              {LABEL[e]}
            </div>
            <div className="font-display" style={{ fontSize: "1.6rem", fontWeight: 600, lineHeight: 1.2, marginTop: 2, color: (resumo[e] ?? 0) && e !== "pronto" && e !== "indisponivel" ? COR[e] : cores.textoForte }}>{resumo[e] ?? 0}</div>
          </div>
        ))}
      </div>

      {cob && (
        <p style={{ fontSize: "0.78rem", color: cores.textoSuave, margin: `0 0 ${espaco.md}px` }}>
          CMJ recente (≤ 21 dias) em {cob.cmj} de {cob.total} jogadores · Hooper recente (≤ 3 dias) em {cob.hooper} de {cob.total}.
          {" "}Sinais: queda do CMJ ≥ {lim.cmj_queda_alto ?? 5}% / {lim.cmj_queda_muito_alto ?? 10}%, subida do Hooper ≥ {lim.hooper_subida_alto ?? 3} / {lim.hooper_subida_muito_alto ?? 5} pontos, ACWR ≥ {lim.acwr_alto ?? 1.3} / {lim.acwr_muito_alto ?? 1.5}. Ajustáveis em Definições · Limites.
        </p>
      )}

      <div style={{ overflowX: "auto", background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md }}>
        <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 820 }}>
          <thead>
            <tr style={{ background: "rgb(var(--ink) / 0.04)" }}>
              {["Jogador", "Estado", "CMJ vs média", "Hooper vs média", "ACWR · 28 dias", "Porquê"].map((h) => (
                <th key={h} style={th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dados.jogadores.map((j) => (
              <tr key={j.jogador} style={{ borderTop: `1px solid ${cores.borda}`, opacity: j.estado === "indisponivel" ? 0.6 : 1 }}>
                <td style={td}>
                  <span style={{ fontWeight: 600, color: cores.textoForte }}><NomeJogador nome={j.jogador} /></span>
                  {j.posicao !== "—" && <span style={{ color: cores.textoSuave }}> · {j.posicao}</span>}
                </td>
                <td style={td}>
                  <span style={{ fontSize: "0.72rem", fontWeight: 700, color: COR[j.estado], background: `color-mix(in srgb, ${COR[j.estado]} 15%, transparent)`, padding: "3px 9px", borderRadius: 999, whiteSpace: "nowrap" }}>
                    {LABEL[j.estado]}
                  </span>
                  {j.estado === "indisponivel" && <div style={{ fontSize: "0.7rem", color: cores.textoSuave, marginTop: 3 }}>{ESTADO_JOGADOR[j.estado_jogador] ?? j.estado_jogador}</div>}
                </td>
                <td style={td}><CelulaCmj c={j.cmj} lim={lim} /></td>
                <td style={td}><CelulaHooper h={j.hooper} lim={lim} /></td>
                <td style={td}><CelulaAcwr a={j.acwr} alto={lim.acwr_alto ?? 1.3} /></td>
                <td style={{ ...td, color: cores.textoSuave, fontSize: "0.75rem" }}>
                  {j.sinais.length ? j.sinais.map((s) => s.texto).join(" · ") : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** Cor da variação: laranja só a partir do limiar de atenção, vermelho a partir do de atenção alta. */
function corVar(v: number | null, alto: number, muito: number, pior: "baixo" | "alto"): string {
  if (v == null) return cores.textoSuave;
  const mau = pior === "baixo" ? -v : v;
  if (mau >= muito) return cores.perigo;
  if (mau >= alto) return cores.atencao;
  return cores.textoSuave;
}

function CelulaCmj({ c, lim }: { c: JogadorProntidao["cmj"]; lim: Record<string, number> }) {
  if (!c) return <span style={{ color: cores.textoFraco }}>sem testes</span>;
  return (
    <div style={{ opacity: c.valido ? 1 : 0.55 }} title={`Último teste ${c.data}${c.media_base != null ? ` · média anterior ${c.media_base} cm` : ""}`}>
      <span style={{ fontWeight: 700, color: cores.textoForte, fontVariantNumeric: "tabular-nums" }}>{c.ultimo.toLocaleString("pt-PT")} cm</span>
      {c.variacao_pct != null && (
        <span style={{ marginLeft: 6, fontWeight: 700, color: corVar(c.variacao_pct, lim.cmj_queda_alto ?? 5, lim.cmj_queda_muito_alto ?? 10, "baixo"), fontVariantNumeric: "tabular-nums" }}>
          {c.variacao_pct > 0 ? "+" : ""}{c.variacao_pct.toLocaleString("pt-PT")}%
        </span>
      )}
      <div style={{ fontSize: "0.7rem", color: cores.textoSuave }}>{c.valido ? `há ${c.dias_desde} d` : `há ${c.dias_desde} d · não conta`}</div>
    </div>
  );
}

function CelulaHooper({ h, lim }: { h: JogadorProntidao["hooper"]; lim: Record<string, number> }) {
  if (!h) return <span style={{ color: cores.textoFraco }}>sem respostas</span>;
  return (
    <div style={{ opacity: h.valido ? 1 : 0.55 }}>
      <span style={{ fontWeight: 700, color: cores.textoForte, fontVariantNumeric: "tabular-nums" }}>{h.ultimo.toLocaleString("pt-PT")}</span>
      <span style={{ color: cores.textoSuave }}> /16</span>
      {h.diferenca != null && (
        <span style={{ marginLeft: 6, fontWeight: 700, color: corVar(h.diferenca, lim.hooper_subida_alto ?? 3, lim.hooper_subida_muito_alto ?? 5, "alto"), fontVariantNumeric: "tabular-nums" }}>
          {h.diferenca > 0 ? "+" : ""}{h.diferenca.toLocaleString("pt-PT")}
        </span>
      )}
      <div style={{ fontSize: "0.7rem", color: cores.textoSuave }}>{h.valido ? `há ${h.dias_desde} d` : `há ${h.dias_desde} d · não conta`}</div>
    </div>
  );
}

const SETA: Record<string, string> = { a_subir: "↗", a_descer: "↘", estavel: "→" };

function CelulaAcwr({ a, alto }: { a: JogadorProntidao["acwr"]; alto: number }) {
  if (!a) return <span style={{ color: cores.textoFraco }}>sem carga interna</span>;
  const cor = a.atual >= alto ? cores.atencao : a.atual < 0.8 ? cores.info : cores.sucesso;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <Sparkline valores={a.serie} limite={alto} cor={cor} />
      <div style={{ whiteSpace: "nowrap" }}>
        <span style={{ fontWeight: 700, color: cor, fontVariantNumeric: "tabular-nums" }}>{a.atual.toLocaleString("pt-PT", { minimumFractionDigits: 2 })}</span>
        {a.tendencia && <span style={{ marginLeft: 4, color: cores.textoSuave }} title={a.ha_7_dias != null ? `Há 7 dias: ${a.ha_7_dias}` : undefined}>{SETA[a.tendencia]}</span>}
      </div>
    </div>
  );
}

function Sparkline({ valores, limite, cor }: { valores: number[]; limite: number; cor: string }) {
  const w = 84, h = 26;
  if (valores.length < 2) return <svg width={w} height={h} />;
  const max = Math.max(limite * 1.15, ...valores);
  const min = Math.min(0.5, ...valores);
  const x = (i: number) => (i / (valores.length - 1)) * w;
  const y = (v: number) => h - ((v - min) / (max - min || 1)) * h;
  const pontos = valores.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  return (
    <svg width={w} height={h} aria-hidden>
      <line x1={0} x2={w} y1={y(limite)} y2={y(limite)} stroke={cores.atencao} strokeOpacity={0.4} strokeDasharray="3 3" />
      <polyline points={pontos} fill="none" stroke={cor} strokeWidth={1.6} strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={x(valores.length - 1)} cy={y(valores[valores.length - 1])} r={2.4} fill={cor} />
    </svg>
  );
}

const th: React.CSSProperties = { textAlign: "left", padding: "9px 12px", fontSize: "0.62rem", letterSpacing: "0.06em", textTransform: "uppercase", color: cores.textoSuave, fontWeight: 600 };
const td: React.CSSProperties = { padding: "9px 12px", fontSize: "0.82rem", color: cores.texto, verticalAlign: "middle" };
