"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { cores, espaco, raio } from "@/lib/theme";
import { useTr, linguaDoCookie } from "@/lib/i18n/cliente";
import type { Tr } from "@/lib/i18n/core";

// ── Tipos do diagnóstico devolvido por /api/ingest/analisar ──────────────────
interface ColunaInfo {
  raw: string;
  canonica: string | null;
  auto: boolean;
  tipo: "obrigatoria" | "metrica" | "extra";
  exemplos: (string | number | null)[];
}
interface Aviso {
  nivel: "erro" | "aviso" | "info";
  texto: string;
}
interface Analise {
  ok: boolean;
  ficheiro: string;
  n_linhas: number;
  n_colunas: number;
  colunas: ColunaInfo[];
  mapa_sugerido: Record<string, string>;
  opcoes_canonicas: { obrigatorias: string[]; metricas: string[] };
  em_falta: { criticas: string[]; recomendadas: string[] };
  avisos: Aviso[];
  resumo: { jogadores: number; sessoes: number; intervalo_datas: [string, string] | null };
  preview: { colunas: string[]; linhas: (string | number | null)[][] };
  pode_importar: boolean;
}
interface Resultado {
  jogadores?: number;
  sessoes_gravadas?: number;
  exercicios_gravados?: number;
}

const IGNORAR = "__ignorar__";
type Fase = "inicio" | "analisando" | "revisao" | "gravando" | "sucesso";

async function token(): Promise<string | null> {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

// Traduz um código de estado HTTP numa mensagem útil para o utilizador.
function mensagemPorEstado(status: number, tr: Tr): string {
  if (status === 502 || status === 503 || status === 504)
    return tr("O servidor demorou demasiado ou ficou sem recursos ({0}). O ficheiro pode ser grande demais para o plano atual — tenta outra vez ou com menos dados.", [status]);
  if (status === 413)
    return tr("O ficheiro é demasiado grande para ser enviado.");
  if (status === 401 || status === 403)
    return tr("A tua sessão expirou ou não tens acesso a esta equipa — atualiza a página e entra outra vez.");
  if (status >= 500)
    return tr("Ocorreu um erro no servidor ao processar o ficheiro ({0}). Tenta outra vez dentro de momentos.", [status]);
  return tr("Não foi possível concluir o pedido ({0}).", [status]);
}

// Lê a resposta com tolerância a corpos que não são JSON: quando a API cai
// ou faz timeout, a plataforma (Render/proxy) devolve uma página HTML de erro
// 502/504 — fazer res.json() diretamente rebentava e o utilizador via sempre
// "Não foi possível ligar à API", escondendo a causa real. Aqui distinguimos
// erro do servidor (com estado) de falha real de ligação.
async function lerResposta(res: Response, tr: Tr): Promise<{ dados: unknown; erro: string | null }> {
  const texto = await res.text();
  let dados: unknown = null;
  if (texto) {
    try { dados = JSON.parse(texto); } catch { /* corpo não-JSON (página de erro) */ }
  }
  if (res.ok) return { dados, erro: null };
  const detalhe =
    dados && typeof dados === "object" && "detail" in dados && typeof (dados as { detail: unknown }).detail === "string"
      ? (dados as { detail: string }).detail
      : null;
  return { dados, erro: detalhe ?? mensagemPorEstado(res.status, tr) };
}

export function ImportadorRobusto({ teamId }: { teamId: string }) {
  const tr = useTr();
  const [fase, setFase] = useState<Fase>("inicio");
  const [ficheiro, setFicheiro] = useState<File | null>(null);
  const [analise, setAnalise] = useState<Analise | null>(null);
  const [mapa, setMapa] = useState<Record<string, string>>({});
  const [erro, setErro] = useState<string | null>(null);
  const [resultado, setResultado] = useState<Resultado | null>(null);

  const opcoes = useMemo(() => {
    if (!analise) return [] as { grupo: string; itens: string[] }[];
    return [
      { grupo: "Identificação", itens: analise.opcoes_canonicas.obrigatorias },
      { grupo: "Métricas", itens: analise.opcoes_canonicas.metricas },
    ];
  }, [analise]);

  // Deteta canónicos escolhidos em mais do que uma coluna (o último ganha).
  const duplicados = useMemo(() => {
    const contagem: Record<string, number> = {};
    for (const v of Object.values(mapa)) if (v && v !== IGNORAR) contagem[v] = (contagem[v] || 0) + 1;
    return Object.entries(contagem).filter(([, n]) => n > 1).map(([k]) => k);
  }, [mapa]);

  async function analisar() {
    if (!ficheiro) return;
    setFase("analisando");
    setErro(null);
    const tk = await token();
    if (!tk) { setErro(tr("A tua sessão expirou — atualiza a página e entra outra vez.")); setFase("inicio"); return; }

    const fd = new FormData();
    fd.append("team_id", teamId);
    fd.append("file", ficheiro);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/ingest/analisar`, {
        method: "POST", headers: { Authorization: `Bearer ${tk}`, "X-Lingua": linguaDoCookie() }, body: fd,
      });
      const { dados, erro } = await lerResposta(res, tr);
      if (erro) { setErro(erro); setFase("inicio"); return; }
      const a = dados as Analise;
      setAnalise(a);
      setMapa({ ...a.mapa_sugerido });
      setFase("revisao");
    } catch {
      setErro(tr("Não foi possível ligar à API. Confirma que o serviço está a correr."));
      setFase("inicio");
    }
  }

  async function confirmar() {
    if (!ficheiro || !analise) return;
    const confirmou = window.confirm(
      tr("Isto vai APAGAR todos os dados atuais desta equipa (jogadores e sessões) e substituí-los pelo conteúdo deste ficheiro.\n\nQueres continuar?")
    );
    if (!confirmou) return;

    setFase("gravando");
    setErro(null);
    const tk = await token();
    if (!tk) { setErro(tr("A tua sessão expirou — atualiza a página e entra outra vez.")); setFase("revisao"); return; }

    const limpo: Record<string, string> = {};
    for (const [raw, canon] of Object.entries(mapa)) if (canon && canon !== IGNORAR) limpo[raw] = canon;

    const fd = new FormData();
    fd.append("team_id", teamId);
    fd.append("file", ficheiro);
    fd.append("mapa", JSON.stringify(limpo));
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/ingest/confirmar`, {
        method: "POST", headers: { Authorization: `Bearer ${tk}`, "X-Lingua": linguaDoCookie() }, body: fd,
      });
      const { dados, erro } = await lerResposta(res, tr);
      if (erro) { setErro(erro); setFase("revisao"); return; }
      setResultado(dados as Resultado);
      setFase("sucesso");
    } catch {
      setErro(tr("Não foi possível ligar à API. Confirma que o serviço está a correr."));
      setFase("revisao");
    }
  }

  function recomecar() {
    setFase("inicio"); setFicheiro(null); setAnalise(null); setMapa({}); setErro(null); setResultado(null);
  }

  // ── Ecrã: sucesso ──────────────────────────────────────────────────────────
  if (fase === "sucesso" && resultado) {
    return (
      <div style={{ ...cartao, borderColor: "rgba(34,197,94,0.3)", background: "rgba(34,197,94,0.06)" }}>
        <p style={{ color: cores.sucesso, fontWeight: 700, fontSize: "1rem", marginBottom: espaco.sm }}>{tr("Dados importados com sucesso")}</p>
        <p style={{ fontSize: "0.9rem", color: cores.texto }}>
          {resultado.jogadores} {tr("jogadores ·")}{" "}{resultado.sessoes_gravadas} {tr("sessões")}{resultado.exercicios_gravados ? tr(" · {0} exercícios", [resultado.exercicios_gravados]) : ""}
        </p>
        <div style={{ display: "flex", gap: espaco.md, marginTop: espaco.lg }}>
          <Link href="/dashboard" style={botaoLink}>{tr("Ver dashboard →")}</Link>
          <button onClick={recomecar} style={botaoSecundario}>{tr("Importar outro ficheiro")}</button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: espaco.lg }}>
      {/* Passos */}
      <Passos fase={fase} />

      {/* Ecrã: escolha do ficheiro */}
      {(fase === "inicio" || fase === "analisando") && (
        <div style={cartao}>
          <p style={{ fontSize: "0.85rem", color: cores.textoSuave, marginBottom: espaco.md }}>
            {tr("Escolhe um ficheiro Excel (folha")}{" "}<strong>{tr("BD_Carga")}</strong>{tr(") ou CSV. Vamos primeiro")}{" "}<strong>{tr("analisar")}</strong> {tr("as colunas e mostrar-te o que foi detetado — só gravas depois de confirmares.")}</p>
          <input
            type="file" accept=".csv,.xlsx,.xls"
            onChange={(e) => setFicheiro(e.target.files?.[0] ?? null)}
            style={{ color: cores.texto, fontSize: "0.85rem" }}
          />
          <button onClick={analisar} disabled={!ficheiro || fase === "analisando"} style={{ ...botaoPrimario, display: "block", marginTop: espaco.lg, opacity: !ficheiro || fase === "analisando" ? 0.5 : 1 }}>
            {fase === "analisando" ? tr("A analisar…") : tr("Analisar ficheiro")}
          </button>
        </div>
      )}

      {/* Ecrã: revisão do mapeamento */}
      {(fase === "revisao" || fase === "gravando") && analise && (
        <>
          {/* Resumo */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: espaco.md }}>
            <MiniKpi rotulo={tr("Ficheiro")} valor={analise.ficheiro} />
            <MiniKpi rotulo={tr("Jogadores")} valor={String(analise.resumo.jogadores)} />
            <MiniKpi rotulo={tr("Sessões")} valor={String(analise.resumo.sessoes)} />
            <MiniKpi rotulo={tr("Período")} valor={analise.resumo.intervalo_datas ? `${analise.resumo.intervalo_datas[0]} → ${analise.resumo.intervalo_datas[1]}` : "—"} />
          </div>

          {/* Avisos */}
          {analise.avisos.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: espaco.sm }}>
              {analise.avisos.map((a, i) => <AvisoLinha key={i} aviso={a} />)}
            </div>
          )}
          {duplicados.length > 0 && (
            <AvisoLinha aviso={{ nivel: "aviso", texto: tr("Mapeaste mais do que uma coluna para: {0}. Só a última será usada.", [duplicados.join(", ")]) }} />
          )}

          {/* Mapeamento */}
          <div style={cartao}>
            <h3 style={tituloSeccao}>{tr("Mapeamento de colunas")}</h3>
            <p style={{ fontSize: "0.78rem", color: cores.textoSuave, margin: `0 0 ${espaco.md}px` }}>
              {tr("Confirma para que serve cada coluna do teu ficheiro. As reconhecidas automaticamente estão marcadas com ✓.")}</p>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem", minWidth: 560 }}>
                <thead>
                  <tr>
                    <th style={th}>{tr("Coluna do ficheiro")}</th>
                    <th style={th}>{tr("Exemplos")}</th>
                    <th style={th}>{tr("Corresponde a")}</th>
                  </tr>
                </thead>
                <tbody>
                  {analise.colunas.map((c) => {
                    const val = mapa[c.raw] ?? IGNORAR;
                    return (
                      <tr key={c.raw} style={{ borderTop: `1px solid ${cores.borda}` }}>
                        <td style={{ ...td, fontWeight: 600, color: cores.texto }}>
                          {c.auto && <span style={{ color: cores.sucesso, marginRight: 6 }}>✓</span>}{c.raw}
                        </td>
                        <td style={{ ...td, color: cores.textoSuave }}>
                          {c.exemplos.filter((v) => v !== null).slice(0, 3).map((v) => String(v)).join(", ") || "—"}
                        </td>
                        <td style={td}>
                          <select
                            value={val}
                            onChange={(e) => setMapa((m) => ({ ...m, [c.raw]: e.target.value }))}
                            style={select}
                          >
                            <option value={IGNORAR}>{tr("— Ignorar / métrica extra —")}</option>
                            {opcoes.map((g) => (
                              <optgroup key={g.grupo} label={tr(g.grupo)}>
                                {g.itens.map((it) => <option key={it} value={it}>{it}</option>)}
                              </optgroup>
                            ))}
                          </select>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pré-visualização */}
          {analise.preview.linhas.length > 0 && (
            <div style={cartao}>
              <h3 style={tituloSeccao}>{tr("Pré-visualização (primeiras linhas)")}</h3>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.78rem", minWidth: 560 }}>
                  <thead>
                    <tr>{analise.preview.colunas.map((c) => <th key={c} style={th}>{c}</th>)}</tr>
                  </thead>
                  <tbody>
                    {analise.preview.linhas.map((linha, i) => (
                      <tr key={i} style={{ borderTop: `1px solid ${cores.borda}` }}>
                        {linha.map((v, j) => <td key={j} style={{ ...td, color: cores.textoSuave }}>{v === null ? "—" : String(v)}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Ações */}
          <div style={{ display: "flex", alignItems: "center", gap: espaco.md, flexWrap: "wrap" }}>
            <button onClick={confirmar} disabled={!analise.pode_importar || fase === "gravando"} style={{ ...botaoPrimario, opacity: !analise.pode_importar || fase === "gravando" ? 0.5 : 1 }}>
              {fase === "gravando" ? tr("A importar…") : tr("Confirmar e importar")}
            </button>
            <button onClick={recomecar} disabled={fase === "gravando"} style={botaoSecundario}>{tr("Recomeçar")}</button>
            {!analise.pode_importar && (
              <span style={{ fontSize: "0.8rem", color: cores.perigo, fontWeight: 600 }}>
                {tr("Resolve os pontos assinalados a vermelho para poderes importar.")}</span>
            )}
          </div>
        </>
      )}

      {erro && (
        <div style={{ padding: `${espaco.md}px ${espaco.lg}px`, background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: raio.sm, color: cores.perigo, fontSize: "0.85rem" }}>
          {erro}
        </div>
      )}
    </div>
  );
}

// ── Subcomponentes ───────────────────────────────────────────────────────────
function Passos({ fase }: { fase: Fase }) {
  const tr = useTr();
  const passos = ["Escolher ficheiro", "Rever colunas", "Importar"];
  const ativo = fase === "inicio" || fase === "analisando" ? 0 : fase === "revisao" || fase === "gravando" ? 1 : 2;
  return (
    <div style={{ display: "flex", gap: espaco.sm, flexWrap: "wrap" }}>
      {passos.map((p, i) => (
        <div key={p} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.78rem", fontWeight: 600, color: i <= ativo ? cores.texto : cores.textoFraco }}>
          <span style={{ width: 20, height: 20, borderRadius: "50%", display: "grid", placeItems: "center", fontSize: "0.7rem", background: i <= ativo ? cores.destaque : "transparent", border: `1px solid ${i <= ativo ? cores.destaque : cores.borda}`, color: cores.textoForte }}>{i + 1}</span>
          {tr(p)}
          {i < passos.length - 1 && <span style={{ margin: "0 4px", color: cores.textoFraco }}>›</span>}
        </div>
      ))}
    </div>
  );
}

function MiniKpi({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div style={{ ...cartao, padding: espaco.md }}>
      <div style={{ fontSize: "0.62rem", letterSpacing: "0.06em", textTransform: "uppercase", color: cores.textoSuave, fontWeight: 600 }}>{rotulo}</div>
      <div style={{ fontSize: "0.95rem", fontWeight: 700, color: cores.texto, marginTop: 4, wordBreak: "break-word" }}>{valor}</div>
    </div>
  );
}

function AvisoLinha({ aviso }: { aviso: Aviso }) {
  const cor = aviso.nivel === "erro" ? cores.perigo : aviso.nivel === "aviso" ? cores.atencao : cores.info;
    return (
    <div style={{ display: "flex", gap: espaco.sm, alignItems: "flex-start", padding: `9px ${espaco.md}px`, background: `${cor}14`, border: `1px solid ${cor}44`, borderRadius: raio.sm, fontSize: "0.82rem", color: cores.texto }}>
      <span aria-hidden style={{ width: 6, height: 6, borderRadius: "50%", background: cor, marginTop: 6, flexShrink: 0 }} /><span>{aviso.texto}</span>
    </div>
  );
}

// ── Estilos ──────────────────────────────────────────────────────────────────
const cartao: React.CSSProperties = { background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.lg };
const tituloSeccao: React.CSSProperties = { fontSize: "0.9rem", fontWeight: 700, color: cores.texto, margin: `0 0 ${espaco.sm}px` };
const th: React.CSSProperties = { textAlign: "left", padding: "8px 10px", fontSize: "0.66rem", letterSpacing: "0.05em", textTransform: "uppercase", color: cores.textoSuave, fontWeight: 600, whiteSpace: "nowrap" };
const td: React.CSSProperties = { padding: "8px 10px", verticalAlign: "top" };
const select: React.CSSProperties = { width: "100%", maxWidth: 240, background: cores.bg, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: cores.textoForte, fontSize: "0.8rem", padding: "6px 8px" };
const botaoPrimario: React.CSSProperties = { padding: "10px 20px", background: cores.acento, border: "none", borderRadius: raio.sm, color: cores.sobreAcento, fontWeight: 700, fontSize: "0.88rem", cursor: "pointer" };
const botaoSecundario: React.CSSProperties = { padding: "10px 18px", background: "transparent", border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: cores.texto, fontWeight: 600, fontSize: "0.85rem", cursor: "pointer" };
const botaoLink: React.CSSProperties = { display: "inline-flex", alignItems: "center", padding: "10px 18px", background: cores.destaque, borderRadius: raio.sm, color: cores.sobreAcento, fontWeight: 700, fontSize: "0.85rem", textDecoration: "none" };
