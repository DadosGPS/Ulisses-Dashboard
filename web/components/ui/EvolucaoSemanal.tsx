"use client";

import { useEffect, useState } from "react";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { Cartao, SecaoTitulo } from "@/components/ui/base";
import { pedidoApi } from "@/lib/api-cliente";
import { cores, desvio, espaco, estado, raio, letra, estiloCampo } from "@/lib/theme";
import { useTr } from "@/lib/i18n/cliente";

type Semana = {
  microciclo: number; sessoes: number; inicio: string | null; fim: string | null;
  vmax: number | null; pct_recorde: number | null;
  [k: string]: number | string | null;
};
type Resposta = {
  tem_dados: boolean; microciclos: number[]; de?: number; ate?: number;
  metricas?: { chave: string; label: string; unidade: string }[];
  semanas: Semana[]; medias?: Record<string, number | null>; recorde_vmax?: number | null;
  vs_normal?: Record<string, number | null>; variacao_2_semanas?: Record<string, number | null>;
  semana_referencia?: number; referencia_incompleta?: boolean; vs_normal_limite?: number;
};

// Faixas de Z-score: muito abaixo → muito acima da média do próprio jogador.
const FAIXAS_Z = [
  { ate: -2, cor: "#7c3aed", rotulo: "< −2" },
  { ate: -1.5, cor: "#334155", rotulo: "−2 … −1.5" },
  { ate: 0, cor: "#eab308", rotulo: "−1.5 … 0" },
  { ate: 1.5, cor: "#16a34a", rotulo: "0 … 1.5" },
  { ate: 2, cor: "#f97316", rotulo: "1.5 … 2" },
  { ate: Infinity, cor: "#dc2626", rotulo: "> 2" },
];
const corZ = (z: number | null) => (z == null ? cores.textoFraco : FAIXAS_Z.find((f) => z < f.ate)!.cor);
const CURTO: Record<string, string> = { distancia: "TD", hsr: "HSR", sprint: "SD", acc: "ACC", dcc: "DEC" };

function corDelta(d: number | null) {
  if (d == null) return cores.textoFraco;
  const a = Math.abs(d);
  return a > 25 ? cores.perigo : a > 20 ? cores.atencao : cores.sucesso;
}

/** Evolução semanal do jogador: carga por microciclo colorida pelo Z-score,
 * Vmáx vs % do recorde, semana vs o normal do jogador por métrica e variação das últimas 2 semanas. */
export function EvolucaoSemanal({ teamId, jogador }: { teamId: string; jogador: string }) {
  const tr = useTr();
  const [de, setDe] = useState<number | null>(null);
  const [ate, setAte] = useState<number | null>(null);
  const [dados, setDados] = useState<Resposta | null>(null);
  const [erro, setErro] = useState(false);

  useEffect(() => { setDe(null); setAte(null); }, [jogador]);
  useEffect(() => {
    const q = new URLSearchParams({ nome: jogador });
    if (de != null) q.set("de", String(de));
    if (ate != null) q.set("ate", String(ate));
    let vivo = true;
    pedidoApi<Resposta>(`/api/teams/${teamId}/jogador/semanas?${q}`)
      .then((d) => { if (vivo) { setDados(d); setErro(false); } })
      .catch(() => vivo && setErro(true));
    return () => { vivo = false; };
  }, [teamId, jogador, de, ate]);

  if (erro) return null;
  if (!dados) return <p style={{ color: cores.textoSuave, fontSize: letra.texto }}>{tr("A carregar…")}</p>;
  if (!dados.tem_dados || !dados.metricas) return null;

  const x = dados.semanas.map((s) => `MC ${s.microciclo}`);
  const limNormal = dados.vs_normal_limite ?? 30;
  const fmt = (v: number | null | undefined, casas = 0) =>
    v == null ? "—" : v.toLocaleString(tr.loc, { maximumFractionDigits: casas, minimumFractionDigits: casas });
  const sel = (valor: number | undefined, mudar: (n: number) => void, rotulo: string, filtro: (m: number) => boolean) => (
    <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: letra.pequeno, color: cores.textoSuave }}>
      {rotulo}
      <select value={valor ?? ""} onChange={(e) => mudar(Number(e.target.value))} style={campo}>
        {dados.microciclos.filter(filtro).map((m) => <option key={m} value={m}>MC {m}</option>)}
      </select>
    </label>
  );

  return (
    <div style={{ marginBottom: espaco.xxl }}>
      <SecaoTitulo
        subtitulo={tr("Totais de cada microciclo. A cor da barra diz quão longe a semana está da média do jogador no intervalo (Z-score); a linha a tracejado é essa média.")}
        ajuda={<>
          <p style={{ margin: "0 0 6px" }}>{tr("Z-score = (valor da semana − média) ÷ desvio-padrão das semanas escolhidas, só deste jogador. Precisa de pelo menos 3 semanas.")}</p>
          <p style={{ margin: "0 0 6px" }}>{tr("Semana vs normal = última semana face à média das 4–6 semanas anteriores deste jogador (todas as sessões). Uma mudança grande é motivo para conversar, não uma previsão de lesão.")}</p>
          <p style={{ margin: 0 }}>{tr("Δ 2 semanas = variação da última semana face à anterior.")}</p>
        </>}
        acoes={<>
          {sel(dados.de, (n) => { setDe(n); if (dados.ate != null && n > dados.ate) setAte(n); }, tr("De"), () => true)}
          {sel(dados.ate, (n) => { setAte(n); if (dados.de != null && n < dados.de) setDe(n); }, tr("até"), () => true)}
        </>}
      >{tr("Evolução semanal")}</SecaoTitulo>

      <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 16px", fontSize: letra.pequeno, color: cores.textoSuave, marginBottom: espaco.md }}>
        <span style={{ fontWeight: 600 }}>Z-score</span>
        {FAIXAS_Z.map((f) => (
          <span key={f.rotulo} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: f.cor }} />{f.rotulo}
          </span>
        ))}
      </div>

      <div className="grelha-semanal" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: espaco.md, marginBottom: espaco.lg }}>
        {dados.metricas.map((m) => {
          const media = dados.medias?.[m.chave];
          const ys = dados.semanas.map((s) => s[m.chave] as number | null);
          const label = tr(m.label);
          return (
            <Cartao key={m.chave} padding={espaco.md}>
              <div style={{ fontSize: letra.texto, fontWeight: 600, color: cores.textoForte, marginBottom: 2 }}>
                {label}{m.unidade === "m" ? " (m)" : ""}
                {media != null && <span style={{ fontWeight: 400, color: cores.textoSuave }}> · {tr("média")} {fmt(media)}</span>}
              </div>
              <PlotlyChart altura={210} titulo={label}
                data={[
                  {
                    type: "bar", x, y: ys,
                    marker: { color: dados.semanas.map((s) => corZ(s[`z_${m.chave}`] as number | null)) },
                    text: ys.map((v) => fmt(v)), textposition: "outside", cliponaxis: false,
                    customdata: dados.semanas.map((s) => [s[`z_${m.chave}`] ?? "—", s.sessoes]),
                    hovertemplate: `%{x}<br>${label}: %{y:,.0f}<br>Z: %{customdata[0]}<br>${tr("Sessões")}: %{customdata[1]}<extra></extra>`,
                    showlegend: false,
                  },
                  ...(media != null ? [{
                    type: "scatter" as const, mode: "lines" as const, x, y: x.map(() => media),
                    line: { color: cores.textoSuave, dash: "dash" as const, width: 1.5 }, hoverinfo: "skip" as const, showlegend: false,
                  }] : []),
                ]}
                layout={{ margin: { t: 18, r: 8, b: 30, l: 44 }, yaxis: { rangemode: "tozero" }, bargap: 0.35 }}
              />
            </Cartao>
          );
        })}
        <Cartao padding={espaco.md}>
          <div style={{ fontSize: letra.texto, fontWeight: 600, color: cores.textoForte, marginBottom: 2 }}>
            {tr("Vel. máx vs % do recorde")}
            {dados.recorde_vmax != null && <span style={{ fontWeight: 400, color: cores.textoSuave }}> · {tr("recorde")} {fmt(dados.recorde_vmax, 1)} km/h</span>}
          </div>
          <PlotlyChart altura={210} titulo={tr("Vel. máx vs % do recorde")}
            data={[
              {
                type: "bar", x, y: dados.semanas.map((s) => s.vmax), name: tr("Vel. máx (km/h)"),
                marker: { color: cores.velMax }, text: dados.semanas.map((s) => fmt(s.vmax, 1)), textposition: "inside",
                insidetextanchor: "start", textangle: 0, textfont: { color: "#fff", size: 11 },
                hovertemplate: `%{x}<br>%{y:.1f} km/h<extra></extra>`,
              },
              {
                type: "scatter", mode: "lines+markers", x, y: dados.semanas.map((s) => s.pct_recorde), yaxis: "y2",
                name: tr("% do recorde"), line: { color: cores.textoForte, width: 2 }, marker: { size: 6 },
                hovertemplate: `%{x}<br>%{y}%<extra></extra>`,
              },
            ]}
            layout={{
              margin: { t: 18, r: 40, b: 30, l: 44 }, bargap: 0.35,
              yaxis: { rangemode: "tozero" },
              yaxis2: { overlaying: "y", side: "right", range: [0, 105], ticksuffix: "%", showgrid: false },
              legend: { orientation: "h", y: -0.2, x: 0, font: { size: 10 } },
            }}
          />
        </Cartao>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: espaco.md }}>
        <Tabela
          titulo={tr("Semana vs normal dele · MC {0}", [dados.semana_referencia ?? ""])}
          nota={tr("±{0} % = dentro do normal · precisa de 4 semanas", [limNormal])}
          linhas={dados.metricas.map((m) => {
            const v = dados.vs_normal?.[m.chave] ?? null;
            const fora = v != null && Math.abs(v) > limNormal;
            return { chave: m.chave, valor: v == null ? "—" : `${v > 0 ? "+" : ""}${v}%`, marca: v == null ? "—" : fora ? "!" : "", cor: v == null ? cores.textoFraco : fora ? (v > 0 ? estado.vigiar : desvio.abaixo) : cores.texto };
          })}
        />
        <Tabela
          titulo={tr("Δ últimas 2 semanas (%)")}
          nota={tr("±20 % ok · 20–25 atenção · > 25 alerta")}
          linhas={dados.metricas.map((m) => {
            const d = dados.variacao_2_semanas?.[m.chave] ?? null;
            return { chave: m.chave, valor: d == null ? "—" : `${d > 0 ? "+" : ""}${fmt(d, 1)}%`, marca: "", cor: corDelta(d) };
          })}
        />
      </div>
      {dados.referencia_incompleta && (
        <p style={{ fontSize: letra.pequeno, color: cores.atencao, margin: `${espaco.sm}px 0 0` }}>
          {tr("O MC {0} parece ainda estar a decorrer (menos sessões do que o habitual): a semana vs normal e a Δ vão subir à medida que a semana fecha. Para comparar semanas completas, escolhe «até» o microciclo anterior.", [dados.semana_referencia ?? ""])}
        </p>
      )}
    </div>
  );
}

function Tabela({ titulo, nota, linhas }: {
  titulo: string; nota: string;
  linhas: { chave: string; valor: string; marca: string; cor: string }[];
}) {
  return (
    <Cartao padding={espaco.md}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: espaco.sm, gap: 8 }}>
        <span style={{ fontSize: letra.texto, fontWeight: 600, color: cores.textoForte }}>{titulo}</span>
        <span style={{ fontSize: letra.legenda, color: cores.textoSuave }}>{nota}</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: `repeat(${linhas.length}, 1fr)`, gap: 6 }}>
        {linhas.map((l) => (
          <div key={l.chave} style={{ textAlign: "center", borderRadius: raio.sm, padding: "8px 4px", background: `color-mix(in srgb, ${l.cor} 12%, transparent)`, border: `1px solid color-mix(in srgb, ${l.cor} 35%, transparent)` }}>
            <div style={{ fontSize: letra.legenda, color: cores.textoSuave, fontWeight: 600, letterSpacing: "0.04em" }}>{CURTO[l.chave] ?? l.chave}</div>
            <div style={{ fontSize: letra.realce, fontWeight: 700, color: l.cor, fontVariantNumeric: "tabular-nums" }}>{l.valor}</div>
            {l.marca && <div style={{ fontSize: letra.texto, color: l.cor, fontWeight: 700 }}>{l.marca}</div>}
          </div>
        ))}
      </div>
    </Cartao>
  );
}

const campo: React.CSSProperties = { ...estiloCampo };
