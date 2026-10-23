"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/layout/PageHeader";
import { Cartao, estiloBotao } from "@/components/ui/base";
import { pedidoApi } from "@/lib/api-cliente";
import { cores, espaco, raio } from "@/lib/theme";
import { useTr } from "@/lib/i18n/cliente";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";

type Falta = { player_id: string; nome: string; whatsapp: string | null; token: string | null; estado_envio: string | null; pedido: boolean };
type Bloco = { respostas: number; pedidos: number; falta: Falta[] };
type Tarefa = {
  chave: "bem_estar" | "gps" | "pse" | "alertas" | "plano";
  estado: "feito" | "pendente" | "aviso" | "na";
  titulo: string;
  detalhe: Record<string, unknown>;
  acao: "pedir" | "lembrar" | "importar" | "ver_alertas" | "planear" | null;
};
interface Resumo {
  data: string; hoje: string; e_passado: boolean;
  sessao: { tipo: string; origem: string } | null;
  plano: { microciclo: { numero: number; nome: string | null; fase: string | null } | null; dia: { tipo: string; dia_md: string | null; objetivo: string | null; exercicios: number } | null; proximos_sem_plano: string[] };
  plantel: { total: number; disponiveis: number; ausentes: { nome: string; estado: string; motivo: string | null }[] };
  gps: { jogadores: number; ultimo_dia: string | null };
  bem_estar: Bloco; pse: Bloco;
  alertas: { n: number; jogadores: { nome: string; status: string; motivo: string; valor: string }[] };
  mensagens: { disponivel: boolean; whatsapp: boolean; config: { wellness_auto: boolean; pse_auto?: boolean; lembrete_auto?: boolean } | null };
  tarefas: Tarefa[]; feitas: number;
}

const COR_ESTADO = { feito: cores.sucesso, pendente: cores.atencao, aviso: cores.perigo, na: cores.textoFraco };
const ESTADO_PLANTEL: Record<string, string> = { lesionado: "lesionado", em_recuperacao: "em recuperação", ausente: "ausente" };

function somarDias(iso: string, n: number) {
  const d = new Date(`${iso}T12:00:00`);
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}

/** «Hoje»: as tarefas do dia do PF, com o próximo passo de cada uma. */
export function PainelHoje({ teamId, dataInicial }: { teamId: string; dataInicial?: string }) {
  const tr = useTr();
  const router = useRouter();
  const { oculto } = usePrivacidade();
  const [data, setData] = useState<string | undefined>(dataInicial);
  const [r, setR] = useState<Resumo | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);
  const [ocupado, setOcupado] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    try {
      setR(await pedidoApi<Resumo>(`/api/teams/${teamId}/hoje${data ? `?data=${data}` : ""}`));
      setErro(null);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro inesperado.");
    }
  }, [teamId, data]);
  useEffect(() => { carregar(); }, [carregar]);

  function irPara(nova: string) {
    setData(nova);
    router.replace(nova === r?.hoje ? "/hoje" : `/hoje?data=${nova}`, { scroll: false });
  }

  async function enviar(tipo: "wellness" | "pse", lembrar: boolean, falta: Falta[]) {
    setOcupado(tipo);
    setAviso(null);
    try {
      const res = await pedidoApi<{ enviados: number; simulados: number; ja_enviados: number; ignorados: { nome: string; motivo: string }[]; modo: string }>(
        `/api/teams/${teamId}/mensagens/${tipo}`, "POST",
        { data: r!.data, player_ids: falta.map((f) => f.player_id), reenviar: lembrar },
      );
      const n = res.enviados + res.simulados;
      setAviso({
        tipo: "ok",
        texto: res.modo === "whatsapp"
          ? tr("{0} mensagem(ns) enviada(s) por WhatsApp.", [n])
          : tr("{0} link(s) pronto(s) — carrega no botão WhatsApp de cada jogador para enviar.", [n]),
      });
      if (res.ignorados.length) {
        setAviso({ tipo: "erro", texto: tr("{0} sem telefone ou consentimento: {1}. Completa em Mensagens.", [res.ignorados.length, res.ignorados.map((i) => i.nome).join(", ")]) });
      }
      await carregar();
    } catch (e) {
      setAviso({ tipo: "erro", texto: e instanceof Error ? e.message : tr("Erro inesperado.") });
    } finally {
      setOcupado(null);
    }
  }

  async function abrirWhatsapp(f: Falta) {
    if (!f.whatsapp) return;
    window.open(f.whatsapp, "_blank", "noopener");
    if (f.token) {
      try { await pedidoApi(`/api/teams/${teamId}/mensagens/marcar-enviado`, "POST", { token: f.token }); await carregar(); } catch { /* só informativo */ }
    }
  }

  if (erro) return <div style={{ padding: espaco.xxl, color: cores.perigo }}>{erro}</div>;
  if (!r) return <div style={{ padding: espaco.xxl, color: cores.textoSuave }}>{tr("A carregar…")}</div>;

  const dataTxt = new Date(`${r.data}T12:00:00`).toLocaleDateString(tr.loc, { weekday: "long", day: "numeric", month: "long" });
  const partes = [
    r.plano.microciclo ? `MC ${r.plano.microciclo.numero}${r.plano.microciclo.fase ? ` · ${r.plano.microciclo.fase}` : ""}` : null,
    r.plano.dia ? [r.plano.dia.dia_md, tr(r.plano.dia.tipo)].filter(Boolean).join(" · ") : r.sessao ? tr("sessão com GPS") : tr("sem sessão planeada"),
    r.plano.dia?.objetivo || null,
  ].filter(Boolean);
  const total = r.tarefas.length;

  return (
    <div>
      <PageHeader titulo={r.data === r.hoje ? tr("Hoje") : dataTxt.charAt(0).toUpperCase() + dataTxt.slice(1)} subtitulo={[r.data === r.hoje ? dataTxt : null, ...partes].filter(Boolean).join(" · ")} />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px`, display: "grid", gridTemplateColumns: "minmax(0, 1fr) 300px", gap: espaco.xl, alignItems: "start" }} className="hoje-grelha">
        <div style={{ display: "flex", flexDirection: "column", gap: espaco.md }}>
          <div style={{ display: "flex", alignItems: "center", gap: espaco.md, flexWrap: "wrap" }}>
            <div style={{ display: "flex", gap: 4 }}>
              <button style={estiloBotao.secundario} onClick={() => irPara(somarDias(r.data, -1))} aria-label={tr("Dia anterior")}>‹</button>
              <button style={estiloBotao.secundario} disabled={r.data === r.hoje} onClick={() => irPara(r.hoje)}>{tr("Hoje")}</button>
              <button style={estiloBotao.secundario} onClick={() => irPara(somarDias(r.data, 1))} aria-label={tr("Dia seguinte")}>›</button>
            </div>
            <Progresso feitas={r.feitas} total={total} />
          </div>

          {aviso && <div role="status" style={{ fontSize: "0.84rem", color: aviso.tipo === "ok" ? cores.sucesso : cores.atencao }}>{aviso.texto}</div>}

          {r.tarefas.map((t) => (
            <CartaoTarefa key={t.chave} t={t}>
              {(t.chave === "bem_estar" || t.chave === "pse") && (() => {
                const b = t.chave === "bem_estar" ? r.bem_estar : r.pse;
                const tipo = t.chave === "bem_estar" ? "wellness" : "pse";
                const d = t.detalhe as { respostas: number; total: number };
                const comLink = b.falta.filter((f) => f.whatsapp);
                return (
                  <>
                    <Linha>{tr("{0} de {1} responderam", [d.respostas, d.total])}
                      {t.chave === "pse" && r.mensagens.config?.pse_auto && <span style={{ color: cores.textoFraco }}> · {tr("pedido automático ligado")}</span>}
                      {t.chave === "bem_estar" && r.mensagens.config?.wellness_auto && <span style={{ color: cores.textoFraco }}> · {tr("envio automático ligado")}</span>}
                    </Linha>
                    {b.falta.length > 0 && t.estado !== "feito" && (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
                        {b.falta.slice(0, 24).map((f) => (
                          f.whatsapp && !r.mensagens.whatsapp ? (
                            <button key={f.player_id} onClick={() => abrirWhatsapp(f)} title={tr("Abrir WhatsApp com a mensagem pronta")}
                              style={{ ...chip, cursor: "pointer", borderColor: f.estado_envio === "manual" ? cores.borda : "#25d36688", color: cores.texto }}>
                              <span style={{ color: "#25d366" }}>●</span> {nomeOuOculto(f.nome, oculto)}{f.estado_envio === "manual" ? " ✓" : ""}
                            </button>
                          ) : (
                            <span key={f.player_id} style={chip}>{nomeOuOculto(f.nome, oculto)}</span>
                          )
                        ))}
                        {b.falta.length > 24 && <span style={{ ...chip, color: cores.textoFraco }}>+{b.falta.length - 24}</span>}
                      </div>
                    )}
                    {r.mensagens.disponivel && t.acao && (
                      <div style={{ display: "flex", gap: espaco.sm, marginTop: espaco.md, flexWrap: "wrap", alignItems: "center" }}>
                        <button style={estiloBotao.primario} disabled={ocupado === tipo} onClick={() => enviar(tipo, t.acao === "lembrar", b.falta)}>
                          {ocupado === tipo ? tr("A enviar…")
                            : t.acao === "lembrar" ? (r.mensagens.whatsapp ? tr("Lembrar quem falta ({0})", [b.falta.length]) : tr("Preparar lembrete ({0})", [b.falta.length]))
                            : r.mensagens.whatsapp ? tr("Pedir agora") : tr("Preparar links")}
                        </button>
                        {!r.mensagens.whatsapp && comLink.length > 0 && <span style={{ fontSize: "0.74rem", color: cores.textoSuave }}>{tr("Carrega no nome de cada jogador (●) para abrir o WhatsApp com a mensagem pronta.")}</span>}
                      </div>
                    )}
                    {!r.mensagens.disponivel && <Linha suave>{tr("As mensagens aos jogadores ainda não estão configuradas.")} <Link href="/mensagens" style={{ color: cores.acento }}>{tr("Configurar")}</Link></Linha>}
                  </>
                );
              })()}
              {t.chave === "gps" && (
                <>
                  <Linha>{r.gps.jogadores ? tr("{0} jogadores com dados de hoje", [r.gps.jogadores]) : tr("Ainda sem dados desta sessão.")}
                    {r.gps.ultimo_dia && !r.gps.jogadores && <span style={{ color: cores.textoFraco }}> · {tr("último GPS: {0}", [new Date(`${r.gps.ultimo_dia}T12:00:00`).toLocaleDateString(tr.loc)])}</span>}</Linha>
                  {t.acao === "importar" && <div style={{ marginTop: espaco.md }}><Link href="/upload" style={botaoLink}>{tr("Importar GPS")}</Link></div>}
                </>
              )}
              {t.chave === "alertas" && (
                r.alertas.n ? (
                  <>
                    <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 4 }}>
                      {r.alertas.jogadores.slice(0, 6).map((a) => (
                        <div key={a.nome} style={{ fontSize: "0.82rem", color: cores.texto }}>
                          <span style={{ color: a.status === "high-attention" ? cores.perigo : cores.atencao }}>●</span>{" "}
                          <Link href={`/jogadores?jogador=${encodeURIComponent(a.nome)}`} style={{ color: cores.textoForte, fontWeight: 600, textDecoration: "none" }}>{nomeOuOculto(a.nome, oculto)}</Link>
                          <span style={{ color: cores.textoSuave }}> · {tr(a.motivo)}{a.valor ? ` (${a.valor})` : ""}</span>
                        </div>
                      ))}
                    </div>
                    <div style={{ marginTop: espaco.md }}><Link href="/dashboard" style={{ ...estiloBotao.ligacao, fontSize: "0.82rem" }}>{tr("Ver no Centro de Controlo →")}</Link></div>
                  </>
                ) : <Linha>{tr("Nenhum jogador com sinais de carga.")}</Linha>
              )}
              {t.chave === "plano" && (
                <>
                  <Linha>{tr("Sem plano para: {0}", [(t.detalhe.dias as string[]).map((d) => new Date(`${d}T12:00:00`).toLocaleDateString(tr.loc, { weekday: "short", day: "numeric" })).join(" · ")])}</Linha>
                  <div style={{ marginTop: espaco.md }}><Link href="/planeamento" style={{ ...estiloBotao.ligacao, fontSize: "0.82rem" }}>{tr("Abrir o Planeamento →")}</Link></div>
                </>
              )}
            </CartaoTarefa>
          ))}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: espaco.md }}>
          <Cartao padding={espaco.lg}>
            <div style={rotulo}>{tr("Plantel")}</div>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: cores.textoForte }}>{r.plantel.disponiveis}<span style={{ fontSize: "0.85rem", color: cores.textoSuave, fontWeight: 500 }}> / {r.plantel.total} {tr("disponíveis")}</span></div>
            {r.plantel.ausentes.length > 0 && (
              <div style={{ marginTop: espaco.sm, display: "flex", flexDirection: "column", gap: 3 }}>
                {r.plantel.ausentes.map((a) => (
                  <div key={a.nome} style={{ fontSize: "0.8rem", color: cores.texto }}>{nomeOuOculto(a.nome, oculto)} <span style={{ color: cores.textoSuave }}>· {tr(ESTADO_PLANTEL[a.estado] ?? a.estado)}{a.motivo ? ` (${a.motivo})` : ""}</span></div>
                ))}
              </div>
            )}
          </Cartao>
          {r.plano.dia && (
            <Cartao padding={espaco.lg}>
              <div style={rotulo}>{tr("Plano do dia")}</div>
              <div style={{ fontSize: "0.9rem", color: cores.textoForte, fontWeight: 600 }}>{[r.plano.dia.dia_md, tr(r.plano.dia.tipo)].filter(Boolean).join(" · ")}</div>
              {r.plano.dia.objetivo && <div style={{ fontSize: "0.8rem", color: cores.textoSuave, marginTop: 2 }}>{r.plano.dia.objetivo}</div>}
              {r.plano.dia.exercicios > 0 && <div style={{ fontSize: "0.78rem", color: cores.textoSuave, marginTop: 4 }}>{tr("{0} exercício(s) planeado(s)", [r.plano.dia.exercicios])}</div>}
              <Link href="/calendario" style={{ ...estiloBotao.ligacao, fontSize: "0.8rem", marginTop: 8, display: "inline-block" }}>{tr("Abrir no Calendário →")}</Link>
            </Cartao>
          )}
          <Cartao padding={espaco.lg}>
            <div style={rotulo}>{tr("Atalhos")}</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <Link href="/prontidao" style={atalho}>{tr("Prontidão do plantel")}</Link>
              <Link href="/mensagens" style={atalho}>{tr("Mensagens e envio automático")}</Link>
              <Link href="/analise" style={atalho}>{tr("Análise da semana")}</Link>
            </div>
            <div style={{ fontSize: "0.72rem", color: cores.textoFraco, marginTop: espaco.md }}>{tr("Dica: Ctrl+K para procurar um jogador ou página.")}</div>
          </Cartao>
        </div>
      </div>
      <style>{`@media (max-width: 900px) { .hoje-grelha { grid-template-columns: 1fr !important; } }`}</style>
    </div>
  );
}

function Progresso({ feitas, total }: { feitas: number; total: number }) {
  const tr = useTr();
  const pct = total ? (feitas / total) * 100 : 0;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: "0.82rem", color: cores.textoSuave }}>
      <div style={{ width: 140, height: 6, borderRadius: 3, background: cores.superficie, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: feitas === total ? cores.sucesso : cores.acento }} />
      </div>
      {feitas === total && total ? tr("Tudo feito ✓") : tr("{0} de {1} feitas", [feitas, total])}
    </div>
  );
}

function CartaoTarefa({ t, children }: { t: Tarefa; children: React.ReactNode }) {
  const tr = useTr();
  const cor = COR_ESTADO[t.estado];
  return (
    <Cartao padding={espaco.lg} style={{ borderLeft: `3px solid ${cor}` }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
        <span aria-hidden style={{ width: 22, height: 22, borderRadius: "50%", display: "grid", placeItems: "center", fontSize: "0.75rem", fontWeight: 800,
          background: `color-mix(in srgb, ${cor} 18%, transparent)`, color: cor }}>{t.estado === "feito" ? "✓" : t.estado === "aviso" ? "!" : "•"}</span>
        <h2 style={{ margin: 0, fontSize: "0.98rem", fontWeight: 650, color: cores.textoForte }}>{tr(t.titulo)}</h2>
        <span style={{ marginLeft: "auto", fontSize: "0.72rem", fontWeight: 600, color: cor }}>
          {t.estado === "feito" ? tr("feito") : t.estado === "aviso" ? tr("ver") : tr("por fazer")}</span>
      </div>
      <div style={{ paddingLeft: 32 }}>{children}</div>
    </Cartao>
  );
}

function Linha({ children, suave }: { children: React.ReactNode; suave?: boolean }) {
  return <div style={{ fontSize: "0.85rem", color: suave ? cores.textoSuave : cores.texto }}>{children}</div>;
}

const chip: React.CSSProperties = { display: "inline-flex", alignItems: "center", gap: 4, border: `1px solid ${cores.bordaForte}`, borderRadius: 999, padding: "2px 10px", fontSize: "0.76rem", color: cores.textoSuave, background: "transparent", whiteSpace: "nowrap" };
const rotulo: React.CSSProperties = { fontSize: "0.68rem", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", color: cores.textoSuave, marginBottom: 6 };
const atalho: React.CSSProperties = { fontSize: "0.84rem", color: cores.texto, textDecoration: "none" };
const botaoLink: React.CSSProperties = { ...estiloBotao.primario, display: "inline-flex", alignItems: "center", textDecoration: "none" };
