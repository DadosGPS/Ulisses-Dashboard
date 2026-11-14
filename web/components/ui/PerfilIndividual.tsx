"use client";

import Link from "next/link";
import { cores, espaco, raio } from "@/lib/theme";
import { useTr } from "@/lib/i18n/cliente";
import { NomeJogador } from "@/components/ui/NomeJogador";
import { Cartao, SecaoTitulo, Vazio } from "@/components/ui/base";

type Zonas = Record<string, number | null> | null;

export interface JogadorPerfil {
  jogador: string;
  posicao: string | null;
  n_sessoes: number;
  vmax_ref: number | null;
  fonte_vmax: "sonra" | "recorde" | null;
  melhor_pct: number | null;
  sessoes_pct: Record<string, number> | null;
  dist_rel: Zonas;
  entradas_rel: Zonas;
  hsr_abs: number | null;
  hsr_rel: number | null;
  acc_zonas: Zonas;
  dcc_zonas: Zonas;
  acc_alta_pct: number | null;
  dcc_alta_pct: number | null;
  acc_max: number | null;
  dcc_max: number | null;
}

/** Espelha GET /api/teams/{team_id}/perfil-individual (perfil_individual_service.py). */
export interface PerfilIndividualResponse {
  tem_dados: boolean;
  tem_sonra: boolean;
  dias: number;
  de: string | null;
  ate: string | null;
  pcts_sessoes: number[];
  zonas_altas: number[];
  jogadores: JogadorPerfil[];
}

const PERIODOS: { dias: number; label: string }[] = [
  { dias: 7, label: "7 dias" },
  { dias: 28, label: "28 dias" },
  { dias: 0, label: "Todos os dados" },
];
const ZONAS = ["1", "2", "3", "4", "5", "6"];

/** Velocidade e acelerações face às capacidades de cada jogador. */
export function PerfilIndividual({ dados }: { dados: PerfilIndividualResponse }) {
  const tr = useTr();
  const data = (d: string | null) => (d ? new Date(`${d}T00:00:00`).toLocaleDateString(tr.loc) : "—");
  const temZonasRel = dados.jogadores.some((j) => j.dist_rel);
  const temAcc = dados.jogadores.some((j) => j.acc_zonas || j.dcc_zonas);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: espaco.xl }}>
      <div style={{ display: "flex", alignItems: "center", gap: espaco.md, flexWrap: "wrap" }}>
        <div role="tablist" style={{ display: "flex", gap: 2, padding: 3, borderRadius: 9, background: cores.superficie }}>
          {PERIODOS.map((p) => {
            const ativo = p.dias === dados.dias;
            return (
              <Link key={p.dias} href={`?dias=${p.dias}`} role="tab" aria-selected={ativo}
                style={{ borderRadius: 7, padding: "5px 14px", fontSize: "0.82rem", fontWeight: 600, textDecoration: "none",
                  background: ativo ? cores.bgCartao : "transparent", color: ativo ? cores.textoForte : cores.textoSuave }}>
                {tr(p.label)}
              </Link>
            );
          })}
        </div>
        {dados.de && <span style={{ fontSize: "0.78rem", color: cores.textoSuave }}>{data(dados.de)} – {data(dados.ate)}</span>}
      </div>

      {!dados.tem_sonra && (
        <div style={nota}>
          {tr("Ainda não há dados do STATSports Sonra. A velocidade abaixo usa o recorde de cada jogador nos dados da app; as zonas relativas e o perfil de acelerações aparecem quando importares o CSV exportado do Sonra (Importar GPS — não é preciso o template Excel).")}
        </div>
      )}

      <section>
        <SecaoTitulo ajuda={tr("Vmáx de referência: a do perfil do jogador no Sonra (a mesma que define as zonas relativas); sem ela, o recorde do jogador nos dados da app.")}>
          {tr("Velocidade face à Vmáx de cada jogador")}</SecaoTitulo>
        {!dados.tem_dados ? <Vazio>{tr("Sem sessões neste período.")}</Vazio> : (
          <Cartao padding={0}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
                <thead>
                  <tr style={{ borderBottom: `1px solid ${cores.borda}` }}>
                    <th style={thEsq}>{tr("Jogador")}</th>
                    <th style={thDir}>{tr("Sessões")}</th>
                    <th style={thDir}>{tr("Vmáx ref.")}</th>
                    <th style={thDir}>{tr("Melhor %")}</th>
                    {dados.pcts_sessoes.map((p) => <th key={p} style={thDir} title={tr("Sessões em que o pico de velocidade chegou a {0}% da Vmáx de referência", [p])}>{tr("Sessões ≥ {0}%", [p])}</th>)}
                    {temZonasRel && dados.zonas_altas.map((z) => <th key={z} style={thDir} title={tr("Metros na zona {0} relativa (entradas na zona)", [z])}>{tr("Z{0} rel.", [z])}</th>)}
                    <th style={thDir}>{tr("HSR abs.")}</th>
                    {temZonasRel && <th style={thDir}>{tr("HSR rel.")}</th>}
                  </tr>
                </thead>
                <tbody>
                  {dados.jogadores.map((j) => (
                    <tr key={j.jogador} style={{ borderBottom: `1px solid ${cores.borda}` }}>
                      <td style={tdEsq}><NomeJogador nome={j.jogador} />{j.posicao && <span style={{ color: cores.textoFraco }}> · {j.posicao}</span>}</td>
                      <td style={tdDir}>{j.n_sessoes}</td>
                      <td style={tdDir} title={j.fonte_vmax === "sonra" ? tr("Perfil do jogador no Sonra") : tr("Recorde nos dados da app")}>
                        {num(j.vmax_ref, tr.loc, 1)}{j.vmax_ref != null && <span style={{ color: cores.textoFraco }}> km/h{j.fonte_vmax === "recorde" ? "*" : ""}</span>}
                      </td>
                      <td style={{ ...tdDir, fontWeight: 600, color: corPct(j.melhor_pct) }}>{j.melhor_pct != null ? `${j.melhor_pct}%` : "—"}</td>
                      {dados.pcts_sessoes.map((p) => <td key={p} style={tdDir}>{j.sessoes_pct?.[String(p)] ?? "—"}</td>)}
                      {temZonasRel && dados.zonas_altas.map((z) => (
                        <td key={z} style={tdDir}>
                          {num(j.dist_rel?.[String(z)], tr.loc)}{j.dist_rel?.[String(z)] != null && " m"}
                          {j.entradas_rel?.[String(z)] != null && <span style={{ color: cores.textoFraco }}> ({j.entradas_rel[String(z)]})</span>}
                        </td>
                      ))}
                      <td style={tdDir}>{num(j.hsr_abs, tr.loc)}{j.hsr_abs != null && " m"}</td>
                      {temZonasRel && <td style={tdDir}>{num(j.hsr_rel, tr.loc)}{j.hsr_rel != null && " m"}</td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Cartao>
        )}
        <p style={legenda}>
          {temZonasRel && <>{tr("Z4–Z6 rel.: metros (e entradas) nas zonas de velocidade relativas do Sonra, ancoradas na Vmáx de cada jogador. Para teres «metros e vezes acima de 85% e de 95%», define no Sonra a zona 5 relativa a partir de 85% e a zona 6 a partir de 95% da Vmáx.")}{" "}</>}
          {tr("* sem Vmáx no perfil do Sonra: usa o recorde do jogador nos dados da app.")}
        </p>
      </section>

      {temAcc && (
        <section>
          <SecaoTitulo ajuda={tr("Número de acelerações e desacelerações em cada zona do Sonra (1 = mais baixa, 6 = mais alta), somado no período. As zonas são as configuradas no Sonra (absolutas ou relativas à aceleração máxima do jogador).")}>
            {tr("Perfil de acelerações e desacelerações")}</SecaoTitulo>
          <Cartao padding={0}>
            <div style={{ display: "flex", gap: espaco.lg, flexWrap: "wrap", padding: `${espaco.sm}px ${espaco.lg}px`, borderBottom: `1px solid ${cores.borda}`, fontSize: "0.72rem", color: cores.textoSuave }}>
              {ZONAS.map((z, i) => (
                <span key={z} style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
                  <span style={{ width: 10, height: 10, borderRadius: 2, background: cores.acc, opacity: opacidade(i) }} />
                  <span style={{ width: 10, height: 10, borderRadius: 2, background: cores.dcc, opacity: opacidade(i), marginLeft: -3 }} />Z{z}
                </span>
              ))}
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem", minWidth: 720 }}>
                <thead>
                  <tr style={{ borderBottom: `1px solid ${cores.borda}` }}>
                    <th style={thEsq}>{tr("Jogador")}</th>
                    <th style={{ ...thEsq, color: cores.acc }}>{tr("Acelerações por zona")}</th>
                    <th style={thDir} title={tr("Parte das acelerações nas zonas 4–6")}>{tr("Z4–6")}</th>
                    <th style={thDir}>{tr("Máx.")}</th>
                    <th style={{ ...thEsq, color: cores.dcc }}>{tr("Desacelerações por zona")}</th>
                    <th style={thDir} title={tr("Parte das desacelerações nas zonas 4–6")}>{tr("Z4–6")}</th>
                    <th style={thDir}>{tr("Máx.")}</th>
                  </tr>
                </thead>
                <tbody>
                  {dados.jogadores.filter((j) => j.acc_zonas || j.dcc_zonas).map((j) => (
                    <tr key={j.jogador} style={{ borderBottom: `1px solid ${cores.borda}` }}>
                      <td style={tdEsq}><NomeJogador nome={j.jogador} /></td>
                      <td style={{ ...tdEsq, width: "28%" }}><Barra zonas={j.acc_zonas} cor={cores.acc} /></td>
                      <td style={tdDir}>{j.acc_alta_pct != null ? `${j.acc_alta_pct}%` : "—"}</td>
                      <td style={tdDir}>{num(j.acc_max, tr.loc, 2)}{j.acc_max != null && <span style={{ color: cores.textoFraco }}> m/s²</span>}</td>
                      <td style={{ ...tdEsq, width: "28%" }}><Barra zonas={j.dcc_zonas} cor={cores.dcc} /></td>
                      <td style={tdDir}>{j.dcc_alta_pct != null ? `${j.dcc_alta_pct}%` : "—"}</td>
                      <td style={tdDir}>{num(j.dcc_max, tr.loc, 2)}{j.dcc_max != null && <span style={{ color: cores.textoFraco }}> m/s²</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Cartao>
          <p style={legenda}>{tr("Comparar a parte em zonas altas entre jogadores só faz sentido se as zonas forem relativas (à aceleração máxima de cada um) — confirma em Sonra › Settings › Calculations › Metric Event Zone.")}</p>
        </section>
      )}
    </div>
  );
}

/** Barra empilhada com o número de ações em cada zona (1 → 6). */
function Barra({ zonas, cor }: { zonas: Zonas; cor: string }) {
  const tr = useTr();
  if (!zonas) return <span style={{ color: cores.textoFraco }}>—</span>;
  const vals = ZONAS.map((z) => zonas[z] ?? 0);
  const total = vals.reduce((a, b) => a + b, 0);
  if (!total) return <span style={{ color: cores.textoFraco }}>—</span>;
  return (
    <div title={ZONAS.map((z, i) => `Z${z}: ${vals[i]}`).join(" · ")} style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ display: "flex", flex: 1, height: 10, borderRadius: 3, overflow: "hidden", background: cores.superficie }}>
        {vals.map((v, i) => v > 0 && <div key={i} style={{ width: `${(v / total) * 100}%`, background: cor, opacity: opacidade(i) }} />)}
      </div>
      <span title={tr("ações no período")} style={{ fontSize: "0.72rem", color: cores.textoSuave, fontVariantNumeric: "tabular-nums", minWidth: 28, textAlign: "right" }}>{total}</span>
    </div>
  );
}

const opacidade = (i: number) => 0.18 + (i / 5) * 0.82;
const num = (v: number | null | undefined, loc: string, casas = 0) =>
  v == null ? "—" : v.toLocaleString(loc, { maximumFractionDigits: casas, minimumFractionDigits: casas });
const corPct = (p: number | null) => (p == null ? cores.textoFraco : p >= 95 ? cores.sucesso : p >= 85 ? cores.texto : cores.atencao);

const nota: React.CSSProperties = { background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md, fontSize: "0.82rem", color: cores.texto, lineHeight: 1.5 };
const legenda: React.CSSProperties = { color: cores.textoSuave, fontSize: "0.74rem", marginTop: espaco.sm, lineHeight: 1.5 };
const thEsq: React.CSSProperties = { textAlign: "left", padding: "9px 12px", fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.03em", color: cores.textoSuave, fontWeight: 600, whiteSpace: "nowrap" };
const thDir: React.CSSProperties = { ...thEsq, textAlign: "right" };
const tdEsq: React.CSSProperties = { textAlign: "left", padding: "8px 12px", whiteSpace: "nowrap" };
const tdDir: React.CSSProperties = { textAlign: "right", padding: "8px 12px", fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" };
