"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { cores, espaco, raio } from "@/lib/theme";

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

export function ImportadorRobusto({ teamId }: { teamId: string }) {
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
    if (!tk) { setErro("A tua sessão expirou — atualiza a página e entra outra vez."); setFase("inicio"); return; }

    const fd = new FormData();
    fd.append("team_id", teamId);
    fd.append("file", ficheiro);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/ingest/analisar`, {
        method: "POST", headers: { Authorization: `Bearer ${tk}` }, body: fd,
      });
      const dados = await res.json();
      if (!res.ok) { setErro(dados.detail || "Não foi possível analisar o ficheiro."); setFase("inicio"); return; }
      const a = dados as Analise;
      setAnalise(a);
      setMapa({ ...a.mapa_sugerido });
      setFase("revisao");
    } catch {
      setErro("Não foi possível ligar à API. Confirma que o serviço está a correr.");
      setFase("inicio");
    }
  }

  async function confirmar() {
    if (!ficheiro || !analise) return;
    const confirmou = window.confirm(
      "Isto vai APAGAR todos os dados atuais desta equipa (jogadores e sessões) e substituí-los pelo conteúdo deste ficheiro.\n\nQueres continuar?"
    );
    if (!confirmou) return;

    setFase("gravando");
    setErro(null);
    const tk = await token();
    if (!tk) { setErro("A tua sessão expirou — atualiza a página e entra outra vez."); setFase("revisao"); return; }

    const limpo: Record<string, string> = {};
    for (const [raw, canon] of Object.entries(mapa)) if (canon && canon !== IGNORAR) limpo[raw] = canon;

    const fd = new FormData();
    fd.append("team_id", teamId);
    fd.append("file", ficheiro);
    fd.append("mapa", JSON.stringify(limpo));
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/ingest/confirmar`, {
        method: "POST", headers: { Authorization: `Bearer ${tk}` }, body: fd,
      });
      const dados = await res.json();
      if (!res.ok) { setErro(dados.detail || "Não foi possível gravar."); setFase("revisao"); return; }
      setResultado(dados);
      setFase("sucesso");
    } catch {
      setErro("Não foi possível ligar à API.");
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
        <p style={{ color: cores.sucesso, fontWeight: 700, fontSize: "1rem", marginBottom: espaco.sm }}>✅ Dados importados com sucesso</p>
        <p style={{ fontSize: "0.9rem", color: cores.texto }}>
          {resultado.jogadores} jogadores · {resultado.sessoes_gravadas} sessões
          {resultado.exercicios_gravados ? ` · ${resultado.exercicios_gravados} exercícios` : ""}
        </p>
        <div style={{ display: "flex", gap: espaco.md, marginTop: espaco.lg }}>
          <Link href="/dashboard" style={botaoLink}>Ver dashboard →</Link>
          <button onClick={recomecar} style={botaoSecundario}>Importar outro ficheiro</button>
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
            Escolhe um ficheiro Excel (folha <strong>BD_Carga</strong>) ou CSV. Vamos primeiro <strong>analisar</strong> as
            colunas e mostrar-te o que foi detetado — só gravas depois de confirmares.
          </p>
          <input
            type="file" accept=".csv,.xlsx,.xls"
            onChange={(e) => setFicheiro(e.target.files?.[0] ?? null)}
            style={{ color: cores.texto, fontSize: "0.85rem" }}
          />
          <button onClick={analisar} disabled={!ficheiro || fase === "analisando"} style={{ ...botaoPrimario, display: "block", marginTop: espaco.lg, opacity: !ficheiro || fase === "analisando" ? 0.5 : 1 }}>
            {fase === "analisando" ? "A analisar…" : "Analisar ficheiro"}
          </button>
        </div>
      )}

      {/* Ecrã: revisão do mapeamento */}
      {(fase === "revisao" || fase === "gravando") && analise && (
        <>
          {/* Resumo */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: espaco.md }}>
            <MiniKpi rotulo="Ficheiro" valor={analise.ficheiro} />
            <MiniKpi rotulo="Jogadores" valor={String(analise.resumo.jogadores)} />
            <MiniKpi rotulo="Sessões" valor={String(analise.resumo.sessoes)} />
            <MiniKpi rotulo="Período" valor={analise.resumo.intervalo_datas ? `${analise.resumo.intervalo_datas[0]} → ${analise.resumo.intervalo_datas[1]}` : "—"} />
          </div>

          {/* Avisos */}
          {analise.avisos.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: espaco.sm }}>
              {analise.avisos.map((a, i) => <AvisoLinha key={i} aviso={a} />)}
            </div>
          )}
          {duplicados.length > 0 && (
            <AvisoLinha aviso={{ nivel: "aviso", texto: `Mapeaste mais do que uma coluna para: ${duplicados.join(", ")}. Só a última será usada.` }} />
          )}

          {/* Mapeamento */}
          <div style={cartao}>
            <h3 style={tituloSeccao}>Mapeamento de colunas</h3>
            <p style={{ fontSize: "0.78rem", color: cores.textoSuave, margin: `0 0 ${espaco.md}px` }}>
              Confirma para que serve cada coluna do teu ficheiro. As reconhecidas automaticamente estão marcadas com ✓.
            </p>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem", minWidth: 560 }}>
                <thead>
                  <tr>
                    <th style={th}>Coluna do ficheiro</th>
                    <th style={th}>Exemplos</th>
                    <th style={th}>Corresponde a</th>
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
                            <option value={IGNORAR}>— Ignorar / métrica extra —</option>
                            {opcoes.map((g) => (
                              <optgroup key={g.grupo} label={g.grupo}>
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
              <h3 style={tituloSeccao}>Pré-visualização (primeiras linhas)</h3>
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
              {fase === "gravando" ? "A importar…" : "Confirmar e importar"}
            </button>
            <button onClick={recomecar} disabled={fase === "gravando"} style={botaoSecundario}>Recomeçar</button>
            {!analise.pode_importar && (
              <span style={{ fontSize: "0.8rem", color: cores.perigo, fontWeight: 600 }}>
                Resolve os pontos assinalados a vermelho para poderes importar.
              </span>
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
  const passos = ["Escolher ficheiro", "Rever colunas", "Importar"];
  const ativo = fase === "inicio" || fase === "analisando" ? 0 : fase === "revisao" || fase === "gravando" ? 1 : 2;
  return (
    <div style={{ display: "flex", gap: espaco.sm, flexWrap: "wrap" }}>
      {passos.map((p, i) => (
        <div key={p} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.78rem", fontWeight: 600, color: i <= ativo ? cores.texto : cores.textoFraco }}>
          <span style={{ width: 20, height: 20, borderRadius: "50%", display: "grid", placeItems: "center", fontSize: "0.7rem", background: i <= ativo ? cores.destaque : "transparent", border: `1px solid ${i <= ativo ? cores.destaque : cores.borda}`, color: "white" }}>{i + 1}</span>
          {p}
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
  const icone = aviso.nivel === "erro" ? "⛔" : aviso.nivel === "aviso" ? "⚠️" : "ℹ️";
  return (
    <div style={{ display: "flex", gap: espaco.sm, alignItems: "flex-start", padding: `9px ${espaco.md}px`, background: `${cor}14`, border: `1px solid ${cor}44`, borderRadius: raio.sm, fontSize: "0.82rem", color: cores.texto }}>
      <span>{icone}</span><span>{aviso.texto}</span>
    </div>
  );
}

// ── Estilos ──────────────────────────────────────────────────────────────────
const cartao: React.CSSProperties = { background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.lg };
const tituloSeccao: React.CSSProperties = { fontSize: "0.9rem", fontWeight: 700, color: cores.texto, margin: `0 0 ${espaco.sm}px` };
const th: React.CSSProperties = { textAlign: "left", padding: "8px 10px", fontSize: "0.66rem", letterSpacing: "0.05em", textTransform: "uppercase", color: cores.textoSuave, fontWeight: 600, whiteSpace: "nowrap" };
const td: React.CSSProperties = { padding: "8px 10px", verticalAlign: "top" };
const select: React.CSSProperties = { width: "100%", maxWidth: 240, background: cores.bg, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: "white", fontSize: "0.8rem", padding: "6px 8px" };
const botaoPrimario: React.CSSProperties = { padding: "10px 20px", background: cores.cargaInterna, border: "none", borderRadius: raio.sm, color: "white", fontWeight: 700, fontSize: "0.88rem", cursor: "pointer" };
const botaoSecundario: React.CSSProperties = { padding: "10px 18px", background: "transparent", border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: cores.texto, fontWeight: 600, fontSize: "0.85rem", cursor: "pointer" };
const botaoLink: React.CSSProperties = { display: "inline-flex", alignItems: "center", padding: "10px 18px", background: cores.destaque, borderRadius: raio.sm, color: "white", fontWeight: 700, fontSize: "0.85rem", textDecoration: "none" };
