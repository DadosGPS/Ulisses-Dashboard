"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { cores, espaco, raio } from "@/lib/theme";
import { NomeJogador } from "@/components/ui/NomeJogador";
import { useTr, linguaDoCookie } from "@/lib/i18n/cliente";

interface Contacto {
  player_id: string;
  nome: string;
  posicao: string | null;
  estado: string;
  telefone: string | null;
  consentimento_em: string | null;
  pode_receber: boolean;
  motivo: string | null;
}

interface PedidoDia {
  nome: string;
  token: string;
  whatsapp: string | null;
  estado_envio: "pendente" | "enviado" | "simulado" | "manual" | "erro";
  erro: string | null;
  respondido: boolean;
  expirado: boolean;
  link: string;
}

export interface MensagensResponse {
  disponivel: boolean;
  motivo: string | null;
  data?: string;
  twilio?: { configurado: boolean; modelo_wellness: boolean; modelo_pse: boolean; agendador: boolean };
  config?: { wellness_auto: boolean; wellness_hora: string; wellness_dias: number[] };
  contactos?: Contacto[];
  dia?: Record<"wellness" | "pse", { pedidos: PedidoDia[]; respondidos: number; total: number }>;
}

interface Resumo {
  enviados: number;
  simulados: number;
  erros: number;
  ja_enviados: number;
  ignorados: { nome: string; motivo: string }[];
  modo: "whatsapp" | "simulacao";
}

const ESTADOS: Record<string, string> = { lesionado: "lesionado", em_recuperacao: "em recuperação", ausente: "ausente" };

const DIAS = [
  { n: 1, l: "Seg" }, { n: 2, l: "Ter" }, { n: 3, l: "Qua" }, { n: 4, l: "Qui" }, { n: 5, l: "Sex" }, { n: 6, l: "Sáb" }, { n: 7, l: "Dom" },
];

export function GestaoMensagens({ teamId, dadosIniciais }: { teamId: string; dadosIniciais: MensagensResponse }) {
  const tr = useTr();
  const [dados, setDados] = useState(dadosIniciais);
  const [aviso, setAviso] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);
  const [aGravar, setAGravar] = useState(false);
  const [config, setConfig] = useState(dadosIniciais.config ?? { wellness_auto: false, wellness_hora: "08:00", wellness_dias: [1, 2, 3, 4, 5] });
  const [duracao, setDuracao] = useState<string>("90");
  const [selecionados, setSelecionados] = useState<Set<string>>(
    () => new Set((dadosIniciais.contactos ?? []).filter((c) => c.pode_receber && c.estado === "apto").map((c) => c.player_id)),
  );
  const [contactos, setContactos] = useState<Record<string, { telefone: string; consentimento: boolean }>>(() =>
    Object.fromEntries((dadosIniciais.contactos ?? []).map((c) => [c.player_id, { telefone: c.telefone ?? "", consentimento: !!c.consentimento_em }])),
  );
  const base = `${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/mensagens`;

  async function pedido(url: string, metodo: string, corpo?: unknown) {
    const { data: { session } } = await createClient().auth.getSession();
    if (!session) throw new Error(tr("Sessão expirada. Volta a entrar."));
    const res = await fetch(url, {
      method: metodo,
      headers: { Authorization: `Bearer ${session.access_token}`, "X-Lingua": linguaDoCookie(), "Content-Type": "application/json" },
      body: corpo ? JSON.stringify(corpo) : undefined,
    });
    const j = await res.json().catch(() => null);
    if (!res.ok) throw new Error(j?.detail ?? tr("Não foi possível concluir."));
    return j;
  }

  async function executar(acao: () => Promise<string>) {
    setAviso(null);
    setAGravar(true);
    try {
      const texto = await acao();
      setDados(await pedido(base, "GET"));
      setAviso({ tipo: "ok", texto });
    } catch (e) {
      setAviso({ tipo: "erro", texto: e instanceof Error ? e.message : tr("Erro inesperado.") });
    } finally {
      setAGravar(false);
    }
  }

  const resumoTexto = (r: Resumo, oQue: string) => {
    const partes = [];
    if (r.enviados) partes.push(tr("{0} enviado(s) por WhatsApp", [r.enviados]));
    if (r.simulados) partes.push(tr("{0} mensagem(ns) preparada(s) — envia-as em «Hoje» com o botão WhatsApp", [r.simulados]));
    if (r.ja_enviados) partes.push(tr("{0} já tinham recebido hoje", [r.ja_enviados]));
    if (r.erros) partes.push(tr("{0} com erro", [r.erros]));
    if (r.ignorados.length) partes.push(tr("{0} sem telefone ou consentimento", [r.ignorados.length]));
    return `${oQue}: ${partes.join(" · ") || tr("ninguém para enviar")}.`;
  };

  // Envio manual gratuito: abre o WhatsApp com a mensagem escrita e regista
  // o pedido como enviado (o jogador continua a aparecer até responder).
  async function abrirWhatsapp(p: PedidoDia) {
    if (!p.whatsapp) return;
    window.open(p.whatsapp, "_blank", "noopener");
    setDados((d) => ({
      ...d,
      dia: d.dia && (Object.fromEntries(
        Object.entries(d.dia).map(([t, v]) => [t, { ...v, pedidos: v.pedidos.map((x) => (x.token === p.token ? { ...x, estado_envio: "manual" as const } : x)) }]),
      ) as MensagensResponse["dia"]),
    }));
    try {
      await pedido(`${base}/marcar-enviado`, "POST", { token: p.token });
    } catch {
      /* o envio já foi aberto; a marcação é só informativa */
    }
  }

  if (!dados.disponivel) {
    return <Caixa cor={cores.atencao}>{dados.motivo}</Caixa>;
  }

  const tw = dados.twilio!;
  const lista = dados.contactos ?? [];
  const aptos = lista.filter((c) => c.pode_receber);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: espaco.xl, maxWidth: 1000 }}>
      {aviso && <Caixa cor={aviso.tipo === "ok" ? cores.sucesso : cores.perigo}>{aviso.texto}</Caixa>}

      {!tw.configurado ? (
        <Caixa cor={cores.info}>
          <strong>{tr("WhatsApp com 1 toque (gratuito).")}</strong> {tr("«Preparar» cria o link pessoal de cada jogador. Depois, em «Hoje», o botão")}{" "}<strong>{tr("WhatsApp")}</strong> {tr("abre a conversa com o jogador já com a mensagem escrita — só tens de carregar em enviar. Funciona no telemóvel (abre a app) e no computador (WhatsApp Web).")}</Caixa>
      ) : (!tw.modelo_wellness || !tw.modelo_pse) && (
        <Caixa cor={cores.atencao}>
          {tr("WhatsApp ligado, mas falta")}{" "}{!tw.modelo_wellness && !tw.modelo_pse ? tr("os modelos de mensagem") : !tw.modelo_wellness ? tr("o modelo do bem-estar") : tr("o modelo da PSE")} {tr("aprovado(s) pela Meta. Sem modelo, a mensagem só chega a quem tiver falado com o número da equipa nas últimas 24 horas.")}</Caixa>
      )}

      {/* ── Ações de hoje ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: espaco.md }}>
        <div style={cartao}>
          <h3 style={titulo}>{tr("Bem-estar da manhã")}</h3>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.85rem", marginBottom: espaco.sm }}>
            <input type="checkbox" checked={config.wellness_auto} onChange={(e) => setConfig({ ...config, wellness_auto: e.target.checked })} />
            {tw.configurado ? tr("Enviar automaticamente") : tr("Preparar automaticamente as mensagens")}
          </label>
          <div style={{ display: "flex", gap: espaco.sm, alignItems: "center", flexWrap: "wrap", marginBottom: espaco.sm, opacity: config.wellness_auto ? 1 : 0.5 }}>
            <span style={suave}>{tr("às")}</span>
            <input type="time" value={config.wellness_hora} onChange={(e) => setConfig({ ...config, wellness_hora: e.target.value })} style={campo} />
            {DIAS.map((d) => {
              const on = config.wellness_dias.includes(d.n);
              return (
                <button key={d.n} onClick={() => setConfig({ ...config, wellness_dias: on ? config.wellness_dias.filter((x) => x !== d.n) : [...config.wellness_dias, d.n] })}
                  style={{ ...chip, background: on ? "rgba(59,130,246,0.2)" : "transparent", borderColor: on ? cores.info : cores.bordaForte, color: on ? cores.textoForte : cores.textoSuave }}>
                  {tr(d.l)}
                </button>
              );
            })}
          </div>
          {!tw.configurado && config.wellness_auto && (
            <p style={{ ...suave, margin: `0 0 ${espaco.sm}px` }}>{tr("À hora escolhida as mensagens ficam prontas em «Hoje»; o envio continua a ser teu (1 toque por jogador).")}</p>
          )}
          {config.wellness_auto && !tw.agendador && (
            <p style={{ ...suave, color: cores.atencao, margin: `0 0 ${espaco.sm}px` }}>{tr("O agendador ainda não está configurado (CRON_SECRET) — até lá o envio automático não corre.")}</p>
          )}
          <div style={{ display: "flex", gap: espaco.sm, flexWrap: "wrap" }}>
            <button style={btnSecundario} disabled={aGravar}
              onClick={() => executar(async () => { await pedido(`${base}/config`, "PUT", config); return tr("Envio automático guardado."); })}>
              {tr("Guardar")}</button>
            <button style={btnPrimario} disabled={aGravar || aptos.length === 0}
              onClick={() => executar(async () => resumoTexto(await pedido(`${base}/wellness`, "POST", {}), tr("Bem-estar")))}>
              {tw.configurado ? tr("Enviar agora") : tr("Preparar agora")}
            </button>
          </div>
        </div>

        <div style={cartao}>
          <h3 style={titulo}>{tr("PSE do treino de hoje")}</h3>
          <p style={{ ...suave, margin: `0 0 ${espaco.sm}px` }}>{tr("Carrega quando o treino acabar. A duração serve para calcular a carga interna (PSE × minutos) logo que o jogador responde.")}</p>
          <div style={{ display: "flex", gap: espaco.sm, alignItems: "center", marginBottom: espaco.sm }}>
            <span style={suave}>{tr("Duração")}</span>
            <input type="number" min={1} max={240} value={duracao} onChange={(e) => setDuracao(e.target.value)} style={{ ...campo, width: 80 }} />
            <span style={suave}>{tr("min ·")}{" "}{selecionados.size} {tr("jogador(es)")}</span>
          </div>
          <button style={btnPrimario} disabled={aGravar || selecionados.size === 0}
            onClick={() => executar(async () => resumoTexto(await pedido(`${base}/pse`, "POST", { duracao_min: Number(duracao) || null, player_ids: [...selecionados] }), "PSE"))}>
            {tw.configurado ? tr("Pedir PSE") : tr("Preparar PSE")}
          </button>
          <p style={{ ...suave, fontSize: "0.72rem", marginTop: 6 }}>{tr("Escolhe quem treinou na lista de jogadores, em baixo.")}</p>
        </div>
      </div>

      {/* ── Hoje ── */}
      <div style={cartao}>
        <h3 style={titulo}>{tr("Hoje")}</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: espaco.lg }}>
          {(["wellness", "pse"] as const).map((tipo) => {
            const d = dados.dia?.[tipo];
            const porEnviar = (d?.pedidos ?? []).filter((p) => p.whatsapp && !p.respondido && !p.expirado && (p.estado_envio === "simulado" || p.estado_envio === "pendente"));
            return (
              <div key={tipo}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, marginBottom: 6, flexWrap: "wrap" }}>
                  <div style={{ fontSize: "0.82rem", fontWeight: 700 }}>
                    {tipo === "wellness" ? tr("Bem-estar") : "PSE"}{" "}
                    <span style={{ color: cores.textoSuave, fontWeight: 400 }}>· {d?.respondidos ?? 0} {tr("de")}{" "}{d?.total ?? 0} {tr("responderam")}</span>
                  </div>
                  {porEnviar.length > 0 && (
                    <button style={btnWhatsapp} onClick={() => abrirWhatsapp(porEnviar[0])}>
                      {tr("Enviar ao seguinte ·")}{" "}{porEnviar.length} {tr("por enviar")}</button>
                  )}
                </div>
                {!d?.total && <p style={suave}>{tr("Ainda nada enviado hoje.")}</p>}
                {d?.pedidos.map((p) => (
                  <div key={p.link} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, padding: "4px 0", borderTop: `1px solid ${cores.borda}`, fontSize: "0.8rem" }}>
                    <span><NomeJogador nome={p.nome} /></span>
                    <span style={{ display: "flex", gap: 10, alignItems: "center" }}>
                      <Estado p={p} />
                      {!p.respondido && !p.expirado && p.whatsapp && (
                        <button style={{ ...linkBtn, color: VERDE_WA }} onClick={() => abrirWhatsapp(p)}>{tr("WhatsApp")}</button>
                      )}
                      {!p.respondido && !p.expirado && (
                        <button style={linkBtn} title={p.link} onClick={() => navigator.clipboard?.writeText(p.link)}>{tr("copiar link")}</button>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Jogadores ── */}
      <div style={cartao}>
        <h3 style={titulo}>{tr("Jogadores")}</h3>
        <Caixa cor={cores.atencao}>
          {tr("Nos escalões de formação os jogadores são menores: só marques «Consentimento» depois de teres autorização escrita do encarregado de educação (e do clube) para enviar mensagens ao jogador e recolher estes dados. Sem consentimento, a app não envia nada.")}</Caixa>
        <div style={{ overflowX: "auto", marginTop: espaco.md }}>
          <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 620 }}>
            <thead>
              <tr>{["PSE", "Jogador", "Telefone (WhatsApp)", "Consentimento", "", "Estado"].map((h, i) => <th key={i} style={th}>{tr(h)}</th>)}</tr>
            </thead>
            <tbody>
              {lista.map((c) => {
                const ed = contactos[c.player_id] ?? { telefone: "", consentimento: false };
                const mudou = ed.telefone !== (c.telefone ?? "") || ed.consentimento !== !!c.consentimento_em;
                return (
                  <tr key={c.player_id} style={{ borderTop: `1px solid ${cores.borda}` }}>
                    <td style={td}>
                      <input type="checkbox" disabled={!c.pode_receber} checked={selecionados.has(c.player_id)}
                        onChange={(e) => { const s = new Set(selecionados); if (e.target.checked) s.add(c.player_id); else s.delete(c.player_id); setSelecionados(s); }} />
                    </td>
                    <td style={td}><NomeJogador nome={c.nome} />{c.estado !== "apto" && <span style={{ color: cores.textoSuave }}> · {tr(ESTADOS[c.estado] ?? c.estado)}</span>}</td>
                    <td style={td}>
                      <input value={ed.telefone} placeholder="+351 912 345 678" inputMode="tel"
                        onChange={(e) => setContactos({ ...contactos, [c.player_id]: { ...ed, telefone: e.target.value } })} style={{ ...campo, width: 170 }} />
                    </td>
                    <td style={td}>
                      <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.78rem" }}>
                        <input type="checkbox" checked={ed.consentimento} onChange={(e) => setContactos({ ...contactos, [c.player_id]: { ...ed, consentimento: e.target.checked } })} />
                        {c.consentimento_em ? `desde ${new Date(`${c.consentimento_em}T00:00:00`).toLocaleDateString(tr.loc)}` : "autorizado"}
                      </label>
                    </td>
                    <td style={td}>
                      {mudou && (
                        <button style={btnSecundario} disabled={aGravar}
                          onClick={() => executar(async () => { await pedido(`${base}/contactos/${c.player_id}`, "PATCH", ed); return tr("Contacto de {0} guardado.", [c.nome]); })}>
                          {tr("Guardar")}</button>
                      )}
                    </td>
                    <td style={{ ...td, color: c.pode_receber ? cores.sucesso : cores.textoSuave, fontSize: "0.75rem" }}>{c.pode_receber ? tr("recebe mensagens") : tr(c.motivo ?? "")}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Estado({ p }: { p: PedidoDia }) {
  const tr = useTr();
  if (p.respondido) return <span style={{ color: cores.sucesso, fontWeight: 700 }}>{tr("respondeu")}</span>;
  if (p.estado_envio === "erro") return <span style={{ color: cores.perigo }} title={p.erro ?? ""}>{tr("erro no envio")}</span>;
  if (p.expirado) return <span style={{ color: cores.textoFraco }}>{tr("expirou")}</span>;
  if (p.estado_envio === "simulado" || p.estado_envio === "pendente") return <span style={{ color: cores.atencao }}>{tr("por enviar")}</span>;
  return <span style={{ color: cores.textoSuave }}>{tr("enviado · à espera")}</span>;
}

function Caixa({ cor, children }: { cor: string; children: React.ReactNode }) {
  return (
    <div style={{ background: `color-mix(in srgb, ${cor} 10%, transparent)`, border: `1px solid color-mix(in srgb, ${cor} 35%, transparent)`, borderRadius: raio.md, padding: espaco.md, fontSize: "0.82rem", color: cores.texto, lineHeight: 1.45 }}>
      {children}
    </div>
  );
}

const cartao: React.CSSProperties = { background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.lg };
const titulo: React.CSSProperties = { fontSize: "0.95rem", fontWeight: 700, color: cores.textoForte, margin: `0 0 ${espaco.md}px` };
const suave: React.CSSProperties = { fontSize: "0.78rem", color: cores.textoSuave, margin: 0 };
const campo: React.CSSProperties = { background: cores.bg, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: cores.textoForte, fontSize: "0.84rem", padding: "6px 8px" };
const chip: React.CSSProperties = { border: "1px solid", borderRadius: 999, padding: "3px 9px", fontSize: "0.74rem", cursor: "pointer" };
const btnPrimario: React.CSSProperties = { background: cores.sucesso, color: "white", border: "none", borderRadius: raio.sm, padding: "8px 14px", fontSize: "0.84rem", fontWeight: 700, cursor: "pointer" };
const btnSecundario: React.CSSProperties = { background: "rgb(var(--ink) / 0.04)", color: cores.texto, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, padding: "6px 12px", fontSize: "0.8rem", fontWeight: 600, cursor: "pointer" };
const VERDE_WA = "#25d366";
const btnWhatsapp: React.CSSProperties = { background: VERDE_WA, color: "#06210f", border: "none", borderRadius: 999, padding: "5px 12px", fontSize: "0.78rem", fontWeight: 800, cursor: "pointer" };
const linkBtn: React.CSSProperties = { background: "none", border: "none", color: cores.info, cursor: "pointer", fontSize: "0.78rem", fontWeight: 600, padding: 0 };
const th: React.CSSProperties = { textAlign: "left", padding: "6px 8px", fontSize: "0.62rem", letterSpacing: "0.06em", textTransform: "uppercase", color: cores.textoSuave, fontWeight: 600 };
const td: React.CSSProperties = { padding: "6px 8px", fontSize: "0.82rem", color: cores.texto };
