"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/layout/PageHeader";
import { Cartao, estiloBotao } from "@/components/ui/base";
import { Carregando } from "@/components/ui/Esqueleto";
import { pedidoApi } from "@/lib/api-cliente";
import { cores, espaco, estado as corEstado, raio } from "@/lib/theme";
import { LegendaCores } from "@/components/ui/Indicadores";
import { Ajuda } from "@/components/ui/Ajuda";
import { useTr } from "@/lib/i18n/cliente";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";

type Falta = { player_id: string; nome: string; whatsapp: string | null; token: string | null; estado_envio: string | null; pedido: boolean };
type Bloco = { respostas: number; pedidos: number; falta: Falta[] };
type Tarefa = {
  chave: "bem_estar" | "gps" | "pse" | "plano" | "compensacao" | "objetivo";
  estado: "feito" | "pendente" | "aviso" | "na";
  titulo: string;
  detalhe: Record<string, unknown>;
  acao: "pedir" | "lembrar" | "importar" | "ver_alertas" | "planear" | "ver_semana" | null;
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
  acoes: Acao[]; decisoes_disponivel: boolean;
  estado_plantel: { total: number; disponiveis: number; condicionados: string[]; em_rtp: string[]; lesionados: string[]; ausentes: string[] };
  treino: Treino | null;
}
type Decisao = "reduzir" | "ajustar" | "manter" | "ignorar";
interface SinalAcao {
  chave: string; texto: string; acao: string | null; severidade: number;
  detalhe: { valor?: number | string; limite?: number }; decisao_feito: Decisao; decidido: { id: string; decisao: Decisao } | null;
}
interface Acao { jogador: string; player_id: string | null; nivel: "agir" | "vigiar"; sinais: SinalAcao[]; pendentes: number }
interface Treino {
  dia_md: string | null; objetivo: string | null; exercicios: string[]; fonte_alvo: "individual" | "equipa" | null; metricas: string[];
  alvos: ({ jogador: string; posicao: string; situacao: "apto" | "condicionado" | "fora" } & Record<string, number | string>)[];
}
const ROTULO_DECISAO: Record<Decisao, string> = { reduzir: "Reduzir carga", ajustar: "Ajustar plano", manter: "Manter", ignorar: "Ignorar" };
const ROTULO_METRICA: Record<string, string> = { distancia: "Distância", hsr: "HSR", sprint: "Sprint", acc: "Acc", dcc: "Dcc" };

// Linguagem de cor única (theme.ts): feito = verde, por fazer = laranja (vigiar), aviso = vermelho (agir).
// As tarefas de dados/planeamento nunca são «agir» (isso é a lista de jogadores): no máximo, vigiar.
const COR_ESTADO = { feito: corEstado.ok, pendente: corEstado.vigiar, aviso: corEstado.vigiar, na: cores.textoFraco };

function somarDias(iso: string, n: number) {
  const d = new Date(`${iso}T12:00:00`);
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}

/** «Hoje»: as tarefas do dia do PF, com o próximo passo de cada uma. */
export function PainelHoje({ teamId, dataInicial, inicial }: { teamId: string; dataInicial?: string; inicial?: unknown }) {
  const tr = useTr();
  const router = useRouter();
  const { oculto } = usePrivacidade();
  const [data, setData] = useState<string | undefined>(dataInicial);
  const [r, setR] = useState<Resumo | null>((inicial as Resumo | null) ?? null);
  const primeira = useRef(!!inicial);
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
  useEffect(() => {
    if (primeira.current) { primeira.current = false; return; }  // já veio do servidor
    carregar();
  }, [carregar]);

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

  async function decidir(a: Acao, s: SinalAcao, decisao: Decisao) {
    setOcupado(`${a.jogador}|${s.chave}`);
    try {
      await pedidoApi(`/api/teams/${teamId}/decisoes`, "POST", {
        jogador: a.jogador, player_id: a.player_id, data: r!.data, sinal: s.chave, decisao,
        detalhe: { acao: s.acao, valor: s.detalhe.valor ?? null, limite: s.detalhe.limite ?? null, origem: "hoje" },
      });
      await carregar();
    } catch (e) {
      setAviso({ tipo: "erro", texto: e instanceof Error ? e.message : tr("Erro inesperado.") });
    } finally { setOcupado(null); }
  }

  async function desfazer(id: string) {
    setOcupado(id);
    try { await pedidoApi(`/api/teams/${teamId}/decisoes/${id}`, "DELETE"); await carregar(); }
    catch (e) { setAviso({ tipo: "erro", texto: e instanceof Error ? e.message : tr("Erro inesperado.") }); }
    finally { setOcupado(null); }
  }

  async function abrirWhatsapp(f: Falta) {
    if (!f.whatsapp) return;
    window.open(f.whatsapp, "_blank", "noopener");
    if (f.token) {
      try { await pedidoApi(`/api/teams/${teamId}/mensagens/marcar-enviado`, "POST", { token: f.token }); await carregar(); } catch { /* só informativo */ }
    }
  }

  if (erro) return <div style={{ padding: espaco.xxl, color: cores.perigo }}>{erro}</div>;
  if (!r) return (
    <div>
      <PageHeader titulo={tr("Hoje")} subtitulo={tr("A carregar…")} />
      <Carregando cartoes={0} linhas={5} />
    </div>
  );

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
      {r.estado_plantel && <BarraPlantel e={r.estado_plantel} />}
      <div style={{ padding: `${espaco.lg}px ${espaco.xxl}px ${espaco.xxl * 2}px`, display: "grid", gridTemplateColumns: "minmax(0, 1fr) 300px", gap: espaco.xl, alignItems: "start" }} className="hoje-grelha">
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

          <ParaAgir acoes={r.acoes ?? []} disponivel={r.decisoes_disponivel} ocupado={ocupado} decidir={decidir} desfazer={desfazer} />
          {r.treino && <TreinoDeHoje t={r.treino} />}
          {r.tarefas.length > 0 && <h2 style={tituloBloco}>{tr("Dados e tarefas")}</h2>}

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
              {t.chave === "compensacao" && (() => {
                const dd = t.detalhe as { data: string; jogadores: { nome: string; minutos: number; hsr: number | null; sprint: number | null }[] };
                return dd.jogadores.length ? (
                  <>
                    <Linha>{tr("Jogaram pouco no jogo de {0}:", [new Date(`${dd.data}T12:00:00`).toLocaleDateString(tr.loc, { weekday: "short", day: "numeric" })])}</Linha>
                    <div style={{ display: "flex", flexDirection: "column", gap: 3, marginTop: 6 }}>
                      {dd.jogadores.slice(0, 8).map((j) => (
                        <div key={j.nome} style={{ fontSize: "0.82rem", color: cores.texto }}>
                          <strong style={{ color: cores.textoForte }}>{nomeOuOculto(j.nome, oculto)}</strong>
                          <span style={{ color: cores.textoSuave }}> · {j.minutos ? `${Math.round(j.minutos)}'` : tr("não jogou")} · {tr("faltam {0} m HSR · {1} m sprint", [Math.round(j.hsr ?? 0), Math.round(j.sprint ?? 0)])}</span>
                        </div>
                      ))}
                    </div>
                    <div style={{ marginTop: espaco.md }}><Link href="/planeamento/semana" style={{ ...estiloBotao.ligacao, fontSize: "0.82rem" }}>{tr("Ver a compensação completa →")}</Link></div>
                  </>
                ) : <Linha>{tr("Compensação feita.")}</Linha>;
              })()}
              {t.chave === "objetivo" && (() => {
                const dd = t.detalhe as { atras: string[]; restantes: number; microciclo: number };
                return dd.atras.length ? (
                  <>
                    <Linha>{tr("{0} jogador(es) atrás do objetivo do MC {1} · {2} treino(s) por fazer", [dd.atras.length, dd.microciclo, dd.restantes])}</Linha>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
                      {dd.atras.slice(0, 16).map((n) => <span key={n} style={chip}>{nomeOuOculto(n, oculto)}</span>)}
                    </div>
                    <div style={{ marginTop: espaco.md }}><Link href="/planeamento/semana" style={{ ...estiloBotao.ligacao, fontSize: "0.82rem" }}>{tr("Ver quanto falta a cada um →")}</Link></div>
                  </>
                ) : <Linha>{tr("Todos dentro do esperado para esta altura da semana.")}</Linha>;
              })()}
              {t.chave === "plano" && (
                <>
                  <Linha>{tr("Sem plano para: {0}", [(t.detalhe.dias as string[]).map((d) => new Date(`${d}T12:00:00`).toLocaleDateString(tr.loc, { weekday: "short", day: "numeric" })).join(" · ")])}</Linha>
                  <div style={{ marginTop: espaco.md }}><Link href="/planeamento/calendario" style={{ ...estiloBotao.ligacao, fontSize: "0.82rem" }}>{tr("Abrir o Planeamento →")}</Link></div>
                </>
              )}
            </CartaoTarefa>
          ))}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: espaco.md }}>
          {r.plano.dia && (
            <Cartao padding={espaco.lg}>
              <div style={rotulo}>{tr("Plano do dia")}</div>
              <div style={{ fontSize: "0.9rem", color: cores.textoForte, fontWeight: 600 }}>{[r.plano.dia.dia_md, tr(r.plano.dia.tipo)].filter(Boolean).join(" · ")}</div>
              {r.plano.dia.objetivo && <div style={{ fontSize: "0.8rem", color: cores.textoSuave, marginTop: 2 }}>{r.plano.dia.objetivo}</div>}
              {r.plano.dia.exercicios > 0 && <div style={{ fontSize: "0.78rem", color: cores.textoSuave, marginTop: 4 }}>{tr("{0} exercício(s) planeado(s)", [r.plano.dia.exercicios])}</div>}
              <Link href="/planeamento/calendario" style={{ ...estiloBotao.ligacao, fontSize: "0.8rem", marginTop: 8, display: "inline-block" }}>{tr("Abrir no Calendário →")}</Link>
            </Cartao>
          )}
          <Cartao padding={espaco.lg}>
            <div style={rotulo}>{tr("Atalhos")}</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <Link href="/upload" style={atalho}>{tr("Importar GPS do treino")}</Link>
              <Link href="/relatorios/treino" style={atalho}>{tr("Relatório do último treino")}</Link>
              <Link href="/relatorios/jogo" style={atalho}>{tr("Relatório do último jogo")}</Link>
              <Link href="/planeamento/semana" style={atalho}>{tr("Semana por jogador e fecho")}</Link>
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


const tituloBloco: React.CSSProperties = { fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: cores.textoSuave, margin: `${espaco.md}px 0 0` };

/** Estado do plantel numa linha: aptos, condicionados, lesionados, ausentes. */
function BarraPlantel({ e }: { e: Resumo["estado_plantel"] }) {
  const tr = useTr();
  const { oculto } = usePrivacidade();
  const grupos: { rotulo: string; n: number; nomes: string[]; cor: string; ajuda: string }[] = [
    { rotulo: "aptos", n: e.disponiveis, nomes: [], cor: corEstado.ok, ajuda: "Disponíveis e sem sinais para agir hoje." },
    { rotulo: "condicionados", n: e.condicionados.length, nomes: e.condicionados, cor: corEstado.agir,
      ajuda: "Com um sinal «agir» ainda por decidir hoje, ou em regresso ao jogo. Ao registar a decisão saem daqui." },
    { rotulo: "lesionados", n: e.lesionados.length, nomes: e.lesionados, cor: corEstado.vigiar, ajuda: "Estado «lesionado» ou «em recuperação» no plantel." },
    { rotulo: "ausentes", n: e.ausentes.length, nomes: e.ausentes, cor: corEstado.normal, ajuda: "Estado «ausente» no plantel (escola, seleção, doença…)." },
  ];
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: espaco.lg, alignItems: "center", padding: `${espaco.md}px ${espaco.xxl}px`, borderBottom: `1px solid ${cores.borda}`, background: cores.bgElevado }}>
      <span style={{ fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: cores.textoSuave }}>{tr("Plantel")} · {e.total}</span>
      {grupos.map((g) => (
        <span key={g.rotulo} style={{ display: "inline-flex", alignItems: "baseline", gap: 6, fontSize: "0.86rem", color: cores.texto, opacity: g.n ? 1 : 0.55 }}>
          <Link href="/hoje/prontidao" title={[tr("Ver na prontidão do plantel"), g.nomes.map((n) => nomeOuOculto(n, oculto)).join(", ")].filter(Boolean).join(" — ")}
            style={{ display: "inline-flex", alignItems: "baseline", gap: 6, color: cores.texto, textDecoration: "none" }}>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: g.cor, alignSelf: "center" }} />
            <strong style={{ fontSize: "1.15rem", color: cores.textoForte }}>{g.n}</strong>{tr(g.rotulo)}
          </Link>
          <Ajuda largura={260}>{tr(g.ajuda)}</Ajuda>
        </span>
      ))}
      {e.em_rtp.length > 0 && <Link href="/regresso" style={{ fontSize: "0.8rem", color: cores.acento, marginLeft: "auto" }}>{tr("{0} em regresso ao jogo →", [e.em_rtp.length])}</Link>}
    </div>
  );
}

/** «Para agir hoje»: cada sinal com a ação sugerida e o registo da decisão num clique. */
function ParaAgir({ acoes, disponivel, ocupado, decidir, desfazer }: {
  acoes: Acao[]; disponivel: boolean; ocupado: string | null;
  decidir: (a: Acao, s: SinalAcao, d: Decisao) => Promise<void>; desfazer: (id: string) => Promise<void>;
}) {
  const tr = useTr();
  const { oculto } = usePrivacidade();
  const [todos, setTodos] = useState(false);
  const [abertos, setAbertos] = useState<string[]>([]);
  const pendentes = acoes.filter((a) => a.pendentes > 0);
  const decididos = acoes.filter((a) => a.pendentes === 0);
  const MAX = 6;
  const visiveis = todos ? pendentes : pendentes.slice(0, MAX);
  return (
    <Cartao padding={espaco.lg} style={{ borderLeft: `3px solid ${pendentes.length ? corEstado.agir : corEstado.ok}` }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: espaco.sm }}>
        <h2 style={{ margin: 0, fontSize: "1.02rem", fontWeight: 650, color: cores.textoForte, display: "flex", alignItems: "center", gap: 7 }}>
          {tr("Para agir hoje")}
          <Ajuda>{tr("Jogadores com sinais de carga, bem-estar, CMJ ou velocidade (os mesmos do Centro de Controlo), com a ação sugerida. «Feito» regista a decisão (reduzir carga ou ajustar o plano, conforme o sinal); «Ignorar» regista que viste e decidiste não mudar nada. As decisões alimentam o resumo de 14 dias nas Definições.")}</Ajuda>
        </h2>
        <span style={{ fontSize: "0.8rem", color: cores.textoSuave }}>
          {pendentes.length ? tr("{0} jogador(es) por decidir", [pendentes.length]) : acoes.length ? tr("Tudo decidido ✓") : ""}
          {decididos.length > 0 && pendentes.length > 0 ? ` · ${tr("{0} decidido(s)", [decididos.length])}` : ""}
        </span>
        <span style={{ marginLeft: "auto" }}><LegendaCores tr={tr} tipos={["estado"]} /></span>
      </div>
      {!disponivel && acoes.length > 0 && (
        <div style={{ fontSize: "0.78rem", color: cores.atencao, marginBottom: espaco.sm }}>{tr("O registo de decisões precisa da migração 0021 — os botões ficam desligados até lá.")}</div>
      )}
      {acoes.length === 0 ? (
        <div style={{ fontSize: "0.86rem", color: cores.texto }}>
          {tr("Nenhum jogador com sinais hoje.")}{" "}
          <Link href="/hoje/prontidao" style={{ color: cores.acento }}>{tr("Ver prontidão do plantel →")}</Link>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column" }}>
          {[...visiveis, ...(todos ? decididos : [])].map((a) => (
            <div key={a.jogador} style={{ padding: "10px 0", borderTop: `1px solid ${cores.borda}`, opacity: a.pendentes ? 1 : 0.65 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: a.pendentes ? corEstado[a.nivel] : corEstado.ok, flexShrink: 0 }} />
                <Link href={`/jogadores?jogador=${encodeURIComponent(a.jogador)}`} style={{ fontWeight: 650, color: cores.textoForte, textDecoration: "none", fontSize: "0.9rem" }}>{nomeOuOculto(a.jogador, oculto)}</Link>
                <span style={{ fontSize: "0.7rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: a.pendentes ? corEstado[a.nivel] : corEstado.ok }}>
                  {a.pendentes ? tr(a.nivel) : tr("decidido")}</span>
              </div>
              {(abertos.includes(a.jogador) ? a.sinais : a.sinais.slice(0, 2)).map((s) => {
                const chave = `${a.jogador}|${s.chave}`;
                return (
                  <div key={s.chave} style={{ display: "flex", gap: espaco.md, alignItems: "flex-start", flexWrap: "wrap", marginTop: 6, paddingLeft: 16 }}>
                    <div style={{ flex: 1, minWidth: 240 }}>
                      <div style={{ fontSize: "0.84rem", color: cores.texto }}>
                        <strong>{tr(s.texto)}</strong>{s.detalhe.valor != null && <span style={{ color: cores.textoSuave }}> · {String(s.detalhe.valor)}{s.detalhe.limite != null ? ` (${tr("limite")} ${s.detalhe.limite})` : ""}</span>}
                      </div>
                      {s.acao && <div style={{ fontSize: "0.8rem", color: cores.textoSuave, marginTop: 2 }}>→ {tr(s.acao)}</div>}
                    </div>
                    {s.decidido ? (
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: "0.78rem", color: corEstado.ok }}>
                        ✓ {tr(ROTULO_DECISAO[s.decidido.decisao])}
                        <button style={{ ...estiloBotao.ligacao, fontSize: "0.76rem" }} disabled={ocupado === s.decidido.id} onClick={() => desfazer(s.decidido!.id)}>{tr("desfazer")}</button>
                      </span>
                    ) : (
                      <span style={{ display: "inline-flex", gap: 6 }}>
                        <button style={{ ...estiloBotao.primario, padding: "5px 12px", fontSize: "0.78rem" }} disabled={!disponivel || ocupado === chave}
                          title={tr("Regista «{0}»", [tr(ROTULO_DECISAO[s.decisao_feito])])} onClick={() => decidir(a, s, s.decisao_feito)}>{tr("Feito")}</button>
                        <button style={{ ...estiloBotao.secundario, padding: "4px 10px", fontSize: "0.78rem" }} disabled={!disponivel || ocupado === chave}
                          onClick={() => decidir(a, s, "ignorar")}>{tr("Ignorar")}</button>
                      </span>
                    )}
                  </div>
                );
              })}
              {a.sinais.length > 2 && !abertos.includes(a.jogador) && (
                <button style={{ ...estiloBotao.ligacao, fontSize: "0.76rem", marginTop: 4, marginLeft: 16 }} onClick={() => setAbertos([...abertos, a.jogador])}>
                  {tr("+{0} sinal(is)", [a.sinais.length - 2])}</button>
              )}
            </div>
          ))}
          {(pendentes.length > MAX || decididos.length > 0) && (
            <button style={{ ...estiloBotao.ligacao, marginTop: 8, alignSelf: "flex-start", fontSize: "0.8rem" }} onClick={() => setTodos(!todos)}>
              {todos ? tr("Mostrar menos") : tr("Mostrar todos ({0})", [acoes.length])}
            </button>
          )}
        </div>
      )}
    </Cartao>
  );
}

/** O treino de hoje: objetivo, exercícios e o alvo de cada jogador. */
function TreinoDeHoje({ t }: { t: Treino }) {
  const tr = useTr();
  const { oculto } = usePrivacidade();
  const corSit = { apto: cores.texto, condicionado: corEstado.agir, fora: cores.textoFraco };
  return (
    <Cartao padding={espaco.lg}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
        <h2 style={{ margin: 0, fontSize: "1.02rem", fontWeight: 650, color: cores.textoForte, display: "flex", alignItems: "center", gap: 7 }}>
          {tr("Treino de hoje")}{t.dia_md ? ` · ${t.dia_md}` : ""}
          <Ajuda>{tr("Alvo de cada jogador = % do dia no plano × fator semanal do microciclo × a referência de jogo dele (o mesmo cálculo do relatório de treino). Condicionados primeiro; quem está fora aparece no fim.")}</Ajuda>
        </h2>
        {t.objetivo && <span style={{ fontSize: "0.84rem", color: cores.textoSuave }}>{t.objetivo}</span>}
      </div>
      {t.exercicios.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
          {t.exercicios.map((e) => <span key={e} style={chip}>{e}</span>)}
        </div>
      )}
      {t.alvos.length === 0 ? (
        <div style={{ fontSize: "0.84rem", color: cores.textoSuave, marginTop: espaco.md }}>
          {tr("Sem alvos para hoje: planeia o dia em % do objetivo semanal para cada jogador ter o seu alvo.")}{" "}
          <Link href="/planeamento/calendario" style={{ color: cores.acento }}>{tr("Planear no Calendário →")}</Link>
        </div>
      ) : (
        <div style={{ overflowX: "auto", marginTop: espaco.md }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
            <thead><tr>
              <th style={thH}>{tr("Jogador")}</th>
              {t.metricas.map((m) => <th key={m} style={{ ...thH, textAlign: "right" }}>{tr(ROTULO_METRICA[m] ?? m)} {m === "acc" || m === "dcc" ? "" : "(m)"}</th>)}
            </tr></thead>
            <tbody>
              {t.alvos.map((a) => (
                <tr key={a.jogador} style={{ borderTop: `1px solid ${cores.borda}` }}>
                  <td style={{ padding: "6px 8px", color: corSit[a.situacao], fontWeight: a.situacao === "condicionado" ? 650 : 500 }}>
                    {nomeOuOculto(a.jogador, oculto)} <span style={{ color: cores.textoFraco, fontSize: "0.72rem" }}>{a.posicao}</span>
                    {a.situacao !== "apto" && <span style={{ fontSize: "0.7rem", marginLeft: 6, color: corSit[a.situacao] }}>{tr(a.situacao)}</span>}
                  </td>
                  {t.metricas.map((m) => <td key={m} style={{ padding: "6px 8px", textAlign: "right", color: a.situacao === "fora" ? cores.textoFraco : cores.texto, fontVariantNumeric: "tabular-nums" }}>
                    {a.situacao === "fora" ? "—" : a[m] != null ? Number(a[m]).toLocaleString(tr.loc) : "—"}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Cartao>
  );
}

const thH: React.CSSProperties = { textAlign: "left", padding: "6px 8px", fontSize: "0.64rem", letterSpacing: "0.05em", textTransform: "uppercase", color: cores.textoSuave, fontWeight: 600 };
