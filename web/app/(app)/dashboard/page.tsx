"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useLoadUser } from "@/lib/use-load-user";
import { createClient } from "@/lib/supabase/client";
import { cores, espaco, raio } from "@/lib/theme";
import { StatusBadge, StatusIndicator } from "@/components/ui/StatusIndicator";
import { KpiCargaCard, type KpiCarga } from "@/components/ui/KpiCargaCard";
import { PageHeader } from "@/components/layout/PageHeader";
import { NomeJogador } from "@/components/ui/NomeJogador";

interface SquadStatus {
  normal: number;
  attention: number;
  highAttention: number;
  total: number;
}

interface Alert {
  player_id: string;
  player_name: string;
  status: "normal" | "attention" | "high-attention";
  primary_reason: string;
  reason_text: string;
  metric_value: string;
}

interface JogadorExposicao {
  jogador: string;
  posicao: string;
  ratio: number;
  zona: "baixo" | "ok" | "alto";
  n_treinos?: number;
  acumulado?: number;
  referencia?: number;
  fonte_referencia?: "media_90" | "posicao" | "equipa" | "pico";
  em_falta?: number;
}

interface MetricaPlaneada {
  chave: string;
  label: string;
  unidade: string;
  planeado: number | null;
  real: number | null;
  desvio_pct: number | null;
  estado: "ok" | "atencao" | "fora" | "sem_plano";
}

interface PlaneadoRealizado {
  tem_dados: boolean;
  motivo: string | null;
  data?: string;
  dia_md?: string | null;
  microciclo?: number | null;
  tem_plano?: boolean;
  n_jogadores?: number;
  limites?: { ok: number; atencao: number };
  metricas?: MetricaPlaneada[];
  jogadores_fora?: { jogador: string; real: number; desvio_pct: number }[];
}

interface PosicaoExposicao {
  posicao: string;
  n_jogadores: number;
  ratio: number;
  zona: "baixo" | "ok" | "alto";
}

interface MetricaExposicao {
  chave: string;
  label: string;
  ref: [number, number];
  ratio_equipa: number;
  zona_equipa: "baixo" | "ok" | "alto";
  posicoes: PosicaoExposicao[];
  jogadores: JogadorExposicao[];
}

interface ExposicaoSemana {
  tem_dados: boolean;
  motivo: string | null;
  microciclo: number | null;
  microciclos_disponiveis?: number[];
  metricas: MetricaExposicao[];
}

const COR_ZONA: Record<string, string> = {
  baixo: cores.perigo,
  ok: cores.sucesso,
  alto: cores.atencao,
};
const LABEL_ZONA: Record<string, string> = {
  baixo: "Exposição baixa",
  ok: "Referência",
  alto: "Exposição elevada",
};

export default function DashboardPage() {
  const router = useRouter();
  const user = useLoadUser();
  const [loading, setLoading] = useState(true);
  const [squadStatus, setSquadStatus] = useState<SquadStatus | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [kpis, setKpis] = useState<KpiCarga[]>([]);
  const [sessaoRecente, setSessaoRecente] = useState<string | null>(null);
  const [exposicao, setExposicao] = useState<ExposicaoSemana | null>(null);
  const [aCarregarExposicao, setACarregarExposicao] = useState(false);
  const [planeado, setPlaneado] = useState<PlaneadoRealizado | null>(null);

  // Troca só o painel de exposição para outro microciclo, sem recarregar o resto.
  async function escolherMicrociclo(mc: number) {
    if (!user.teamId) return;
    setACarregarExposicao(true);
    try {
      const { data: { session } } = await createClient().auth.getSession();
      if (!session) return;
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/teams/${user.teamId}/dashboard/exposicao-semana?microciclo=${mc}`,
        { headers: { Authorization: `Bearer ${session.access_token}` } },
      );
      if (res.ok) setExposicao(await res.json());
    } finally {
      setACarregarExposicao(false);
    }
  }

  useEffect(() => {
    if (user.isLoading) return;
    if (!user.teamId) {
      router.push("/login");
      return;
    }
    fetchDashboardData();
  }, [user.teamId, user.isLoading]);

  async function fetchDashboardData() {
    try {
      setLoading(true);
      const teamId = user.teamId;

      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) {
        router.push("/login");
        return;
      }

      const apiBase = `${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}`;
      const opcoes = { headers: { Authorization: `Bearer ${token}` } };

      const [statusRes, alertsRes, cargaRes, exposicaoRes, planeadoRes] = await Promise.all([
        fetch(`${apiBase}/dashboard/squad-status`, opcoes),
        fetch(`${apiBase}/dashboard/attention-required`, opcoes),
        fetch(`${apiBase}/carga-externa`, opcoes),
        fetch(`${apiBase}/dashboard/exposicao-semana`, opcoes),
        fetch(`${apiBase}/dashboard/planeado-vs-realizado`, opcoes),
      ]);

      if (statusRes.ok) setSquadStatus(await statusRes.json());
      if (alertsRes.ok) setAlerts(await alertsRes.json());
      if (cargaRes.ok) {
        const carga = await cargaRes.json();
        setKpis(carga.kpis ?? []);
        setSessaoRecente(carga.sessao_recente ?? null);
      }
      if (exposicaoRes.ok) setExposicao(await exposicaoRes.json());
      if (planeadoRes.ok) setPlaneado(await planeadoRes.json());
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div style={{ padding: espaco.xl, display: "flex", alignItems: "center", justifyContent: "center", minHeight: "60vh", color: cores.textoSuave }}>
        A carregar o estado da equipa…
      </div>
    );
  }

  const dataLegivel = sessaoRecente
    ? new Date(sessaoRecente).toLocaleDateString("pt-PT", { day: "2-digit", month: "long" })
    : null;

  const semDados = !squadStatus && kpis.length === 0 && alerts.length === 0;

  return (
    <div>
      <PageHeader titulo="Dashboard" subtitulo="O estado da equipa num relance" />

      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {semDados ? (
          <EstadoVazio />
        ) : (
          <>
            {/* ── Semáforo da equipa ─────────────────────────── */}
            {squadStatus && (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                  gap: espaco.md,
                  marginBottom: espaco.xxl,
                }}
              >
                <StatusBadge status="normal" count={squadStatus.normal} />
                <StatusBadge status="attention" count={squadStatus.attention} />
                <StatusBadge status="high-attention" count={squadStatus.highAttention} />
              </div>
            )}

            {/* ── Carga externa da equipa (protagonista) ─────── */}
            {kpis.length > 0 && (
              <div style={{ marginBottom: espaco.xxl }}>
                <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: espaco.md }}>
                  <SecaoTitulo>Carga externa da equipa {dataLegivel && <span style={{ color: cores.textoSuave, fontWeight: 400 }}>· {dataLegivel}</span>}</SecaoTitulo>
                  <button onClick={() => router.push("/carga-externa")} style={linkBtn}>Ver detalhe →</button>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: espaco.md }}>
                  {kpis.map((k) => (
                    <KpiCargaCard key={k.chave} kpi={k} compacto />
                  ))}
                </div>
              </div>
            )}

            {/* ── Planeado vs realizado (última sessão de treino) ── */}
            {planeado?.tem_dados && <PlaneadoRealizadoCard dados={planeado} onPlanear={() => router.push("/planeamento")} />}

            {/* ── Exposição da semana (HSR/Sprint vs jogo) ───── */}
            {exposicao && (
              <div style={{ marginBottom: espaco.xxl }}>
                <div style={{ display: "flex", alignItems: "center", gap: espaco.md, flexWrap: "wrap" }}>
                  <SecaoTitulo>Exposição da semana vs jogo</SecaoTitulo>
                  {(exposicao.microciclos_disponiveis?.length ?? 0) > 0 && (
                    <select
                      aria-label="Microciclo"
                      value={exposicao.microciclo ?? ""}
                      onChange={(e) => escolherMicrociclo(Number(e.target.value))}
                      disabled={aCarregarExposicao}
                      style={{ background: cores.bgCartao, color: cores.texto, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, padding: "4px 8px", fontSize: "0.82rem", cursor: "pointer" }}
                    >
                      {[...(exposicao.microciclos_disponiveis ?? [])].reverse().map((m) => (
                        <option key={m} value={m}>Microciclo {m}</option>
                      ))}
                    </select>
                  )}
                  {aCarregarExposicao && <span style={{ fontSize: "0.75rem", color: cores.textoSuave }}>A calcular…</span>}
                </div>
                <p style={{ fontSize: "0.78rem", color: cores.textoSuave, margin: `4px 0 ${espaco.md}px` }}>
                  Soma dos treinos do microciclo (jogos excluídos) a dividir pela referência de jogo do jogador: média por 90 minutos dos últimos 5 jogos em que fez pelo menos 60 minutos. Zona de referência a verde; fora dela gera aviso. «Faltam» = metros para chegar à zona.
                </p>
                {exposicao.tem_dados ? (
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: espaco.md }}>
                    {exposicao.metricas.map((m) => (
                      <MetricaExposicaoCard key={m.chave} metrica={m} />
                    ))}
                  </div>
                ) : (
                  <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.lg, color: cores.textoSuave, fontSize: "0.85rem" }}>
                    {exposicao.motivo ?? "Sem dados de exposição."}
                  </div>
                )}
              </div>
            )}

            {/* ── Atenção requerida ──────────────────────────── */}
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: espaco.md }}>
              <SecaoTitulo>Atenção requerida</SecaoTitulo>
              {alerts.length > 6 && <span style={{ fontSize: "0.75rem", color: cores.textoSuave }}>{alerts.length} atletas</span>}
            </div>
            {alerts.length === 0 ? (
              <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.lg, color: cores.textoSuave, fontSize: "0.9rem", marginBottom: espaco.xxl }}>
                Ninguém precisa de atenção especial neste momento.
              </div>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: espaco.md, marginBottom: espaco.xxl }}>
                {alerts.slice(0, 6).map((alert) => (
                  <div
                    key={alert.player_id}
                    onClick={() => router.push(`/jogadores?nome=${encodeURIComponent(alert.player_name)}`)}
                    style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md, cursor: "pointer" }}
                    onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.borderColor = cores.bordaForte)}
                    onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.borderColor = cores.borda)}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: espaco.sm }}>
                      <span style={{ fontSize: "0.95rem", fontWeight: 700, color: cores.textoForte }}>{alert.player_name}</span>
                      <StatusIndicator status={alert.status} size="sm" showLabel={false} />
                    </div>
                    <div style={{ fontSize: "0.82rem", fontWeight: 600, color: cores.textoForte }}>{alert.reason_text}</div>
                    <div style={{ fontSize: "0.8rem", color: cores.textoSuave, marginTop: 2 }}>{alert.metric_value}</div>
                    <div style={{ marginTop: espaco.md, paddingTop: espaco.sm, borderTop: `1px solid ${cores.borda}`, fontSize: "0.72rem", color: cores.destaque, fontWeight: 600 }}>
                      Ver perfil →
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* ── Ações rápidas ──────────────────────────────── */}
            <SecaoTitulo>Ações rápidas</SecaoTitulo>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: espaco.md }}>
              <AcaoBtn label="Importar GPS" cor={cores.sucesso} onClick={() => router.push("/upload")} />
              <AcaoBtn label="Ver sessões" cor={cores.info} onClick={() => router.push("/sessoes/lista")} />
              <AcaoBtn label="Comparar jogadores" cor={cores.destaque} onClick={() => router.push("/analise/comparacao")} />
              <AcaoBtn label="Match benchmark" cor={cores.cargaInterna} onClick={() => router.push("/match-benchmark")} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

const linkBtn: React.CSSProperties = {
  background: "transparent",
  border: "none",
  color: cores.destaque,
  fontSize: "0.78rem",
  fontWeight: 600,
  cursor: "pointer",
};

function AcaoBtn({ label, cor, onClick }: { label: string; cor: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: `color-mix(in srgb, ${cor} 14%, transparent)`,
        border: `1px solid ${cor}`,
        borderRadius: raio.md,
        padding: `${espaco.md}px ${espaco.lg}px`,
        color: cores.textoForte,
        fontSize: "0.9rem",
        fontWeight: 700,
        cursor: "pointer",
        transition: "opacity 0.15s",
      }}
      onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.opacity = "0.85")}
      onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.opacity = "1")}
    >
      {label}
    </button>
  );
}

function MetricaExposicaoCard({ metrica }: { metrica: MetricaExposicao }) {
  const corEquipa = COR_ZONA[metrica.zona_equipa] ?? cores.textoSuave;
  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderLeft: `3px solid ${corEquipa}`, borderRadius: raio.md, padding: espaco.lg }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: espaco.sm }}>
        <span style={{ fontSize: "0.9rem", fontWeight: 700, color: cores.textoForte }}>{metrica.label}</span>
        <span style={{ fontSize: "0.72rem", color: cores.textoSuave }}>ref {metrica.ref[0].toFixed(2)}–{metrica.ref[1].toFixed(2)}×</span>
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: espaco.sm, marginBottom: espaco.md }}>
        <span className="font-display" style={{ fontSize: "1.7rem", fontWeight: 800, color: corEquipa, lineHeight: 1, fontVariantNumeric: "tabular-nums" }}>
          {metrica.ratio_equipa.toFixed(2)}×
        </span>
        <span style={{ fontSize: "0.72rem", fontWeight: 700, color: corEquipa, background: `color-mix(in srgb, ${corEquipa} 16%, transparent)`, padding: "2px 8px", borderRadius: 999 }}>
          {LABEL_ZONA[metrica.zona_equipa]}
        </span>
        <span style={{ fontSize: "0.72rem", color: cores.textoSuave }}>equipa</span>
      </div>
      {metrica.posicoes && metrica.posicoes.length > 1 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: espaco.md }}>
          {metrica.posicoes.map((p) => {
            const cor = COR_ZONA[p.zona] ?? cores.textoSuave;
            return (
              <span key={p.posicao} title={`${p.n_jogadores} jogador(es)`} style={{ fontSize: "0.72rem", fontWeight: 600, color: cor, background: `color-mix(in srgb, ${cor} 14%, transparent)`, border: `1px solid color-mix(in srgb, ${cor} 35%, transparent)`, padding: "2px 8px", borderRadius: 999 }}>
                {p.posicao} {p.ratio.toFixed(2)}×
              </span>
            );
          })}
        </div>
      )}
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {metrica.jogadores.map((j) => {
          const cor = COR_ZONA[j.zona] ?? cores.textoSuave;
          // Barra proporcional: o topo da escala é o limite superior da zona (ou o próprio valor, se maior).
          const escala = Math.max(metrica.ref[1] * 1.4, j.ratio);
          const pct = escala > 0 ? Math.min(100, (j.ratio / escala) * 100) : 0;
          return (
            <div key={j.jogador} title={dicaJogador(j, metrica.label)} style={{ display: "grid", gridTemplateColumns: "1fr 2fr auto auto", alignItems: "center", gap: espaco.sm }}>
              <span style={{ fontSize: "0.78rem", color: "rgb(var(--ink) / 0.85)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                <NomeJogador nome={j.jogador} />{j.posicao && j.posicao !== "—" && <span style={{ color: cores.textoSuave }}> · {j.posicao}</span>}
              </span>
              <div style={{ position: "relative", height: 8, background: "rgb(var(--ink) / 0.06)", borderRadius: 4 }}>
                <div style={{ position: "absolute", inset: 0, width: `${pct}%`, background: cor, borderRadius: 4 }} />
              </div>
              <span style={{ fontSize: "0.72rem", color: cores.textoSuave, fontVariantNumeric: "tabular-nums", minWidth: 78, textAlign: "right", whiteSpace: "nowrap" }}>
                {j.em_falta ? `faltam ${Math.round(j.em_falta)} m` : ""}
              </span>
              <span style={{ fontSize: "0.78rem", fontWeight: 700, color: cor, fontVariantNumeric: "tabular-nums", minWidth: 40, textAlign: "right" }}>{j.ratio.toFixed(2)}×</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const FONTE_LABEL: Record<string, string> = {
  media_90: "média por 90' dos últimos jogos completos",
  posicao: "sem jogos de 60' — mediana da posição",
  equipa: "sem jogos de 60' — mediana da equipa",
  pico: "pico em jogo (jogos sem minutos registados)",
};

function dicaJogador(j: JogadorExposicao, label: string): string | undefined {
  const partes: string[] = [];
  if (j.acumulado != null && j.referencia != null) partes.push(`${label}: ${Math.round(j.acumulado)} m acumulados ÷ ${Math.round(j.referencia)} m de referência`);
  if (j.fonte_referencia) partes.push(`Referência: ${FONTE_LABEL[j.fonte_referencia] ?? j.fonte_referencia}`);
  if (j.n_treinos != null) partes.push(`${j.n_treinos} treino(s) somados`);
  return partes.length ? partes.join("\n") : undefined;
}

const COR_PLANO: Record<string, string> = {
  ok: cores.sucesso,
  atencao: cores.atencao,
  fora: cores.perigo,
  sem_plano: cores.textoFraco,
};
const LABEL_PLANO: Record<string, string> = {
  ok: "Dentro do plano",
  atencao: "Desvio a vigiar",
  fora: "Fora do plano",
  sem_plano: "Sem plano",
};

function fmtValor(v: number | null, unidade: string): string {
  if (v == null) return "—";
  const n = unidade === "" ? v.toLocaleString("pt-PT", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) : Math.round(v).toLocaleString("pt-PT");
  return unidade ? `${n} ${unidade}` : n;
}

function PlaneadoRealizadoCard({ dados, onPlanear }: { dados: PlaneadoRealizado; onPlanear: () => void }) {
  const data = dados.data ? new Date(`${dados.data}T00:00:00`).toLocaleDateString("pt-PT", { weekday: "short", day: "numeric", month: "short" }) : "";
  const metricas = dados.metricas ?? [];
  return (
    <div style={{ marginBottom: espaco.xxl }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: espaco.md, gap: espaco.md, flexWrap: "wrap" }}>
        <SecaoTitulo>
          Planeado vs realizado{" "}
          <span style={{ color: cores.textoSuave, fontWeight: 400 }}>
            · {[data, dados.dia_md, dados.microciclo != null ? `Microciclo ${dados.microciclo}` : null, dados.n_jogadores ? `${dados.n_jogadores} jogadores` : null].filter(Boolean).join(" · ")}
          </span>
        </SecaoTitulo>
        <button onClick={onPlanear} style={linkBtn}>{dados.tem_plano ? "Ver planeamento →" : "Planear esta sessão →"}</button>
      </div>
      {!dados.tem_plano && (
        <p style={{ fontSize: "0.78rem", color: cores.textoSuave, margin: `0 0 ${espaco.md}px` }}>
          Ainda não há valores planeados para este dia. Define a PSE e a carga externa planeadas no Planeamento para veres o desvio aqui.
        </p>
      )}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: espaco.md }}>
        {metricas.map((m) => {
          const cor = COR_PLANO[m.estado];
          return (
            <div key={m.chave} style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderTop: `3px solid ${cor}`, borderRadius: raio.md, padding: espaco.md }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 6 }}>
                <span style={{ fontSize: "0.8rem", fontWeight: 700, color: cores.textoForte }}>{m.label}</span>
                <span style={{ fontSize: "0.68rem", fontWeight: 700, color: cor }}>{LABEL_PLANO[m.estado]}</span>
              </div>
              <div className="font-display" style={{ fontSize: "1.35rem", fontWeight: 800, color: cores.textoForte, fontVariantNumeric: "tabular-nums" }}>
                {fmtValor(m.real, m.unidade)}
              </div>
              <div style={{ fontSize: "0.74rem", color: cores.textoSuave, marginTop: 2, fontVariantNumeric: "tabular-nums" }}>
                Planeado {fmtValor(m.planeado, m.unidade)}
                {m.desvio_pct != null && (
                  <span style={{ color: cor, fontWeight: 700 }}> · {m.desvio_pct > 0 ? "+" : ""}{m.desvio_pct}%</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
      {(dados.jogadores_fora?.length ?? 0) > 0 && (
        <div style={{ marginTop: espaco.md, fontSize: "0.78rem", color: cores.textoSuave }}>
          HSR mais afastado do plano (&gt; {dados.limites?.atencao ?? 20}%):{" "}
          {dados.jogadores_fora!.map((j, i) => (
            <span key={j.jogador}>
              {i > 0 && ", "}
              <NomeJogador nome={j.jogador} /> <span style={{ color: j.desvio_pct > 0 ? cores.atencao : cores.perigo, fontWeight: 700 }}>{j.desvio_pct > 0 ? "+" : ""}{j.desvio_pct}%</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function SecaoTitulo({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="font-display" style={{ fontSize: "1rem", fontWeight: 600, color: cores.textoForte, margin: 0 }}>
      {children}
    </h2>
  );
}

function EstadoVazio() {
  const router = useRouter();
  return (
    <div style={{ maxWidth: 600, margin: "60px auto", padding: "0 24px", textAlign: "center" }}>
      <p style={{ color: cores.textoSuave, fontSize: "0.95rem", marginBottom: espaco.lg }}>
        Ainda não há dados carregados para esta equipa. Importa dados de GPS para veres o estado da equipa.
      </p>
      <button
        onClick={() => router.push("/upload")}
        style={{ background: cores.sucesso, border: "none", borderRadius: raio.md, padding: `${espaco.md}px ${espaco.xl}px`, color: "white", fontWeight: 700, cursor: "pointer" }}
      >
        Importar GPS
      </button>
    </div>
  );
}
