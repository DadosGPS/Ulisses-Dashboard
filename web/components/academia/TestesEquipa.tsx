"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { pedidoApi } from "@/lib/api-cliente";
import { cores, espaco, raio, letra, estiloTh, estiloTd, estiloCampo, PAD_DENSO } from "@/lib/theme";
import { PageHeader } from "@/components/layout/PageHeader";
import { Cartao, Etiqueta, Vazio, estiloBotao } from "@/components/ui/base";
import { NomeJogador } from "@/components/ui/NomeJogador";
import type { Metrica } from "./tipos";
import { NavEquipa } from "./NavEquipa";
import { idadeEm, khamisRoche } from "@/lib/khamis-roche";
import { useTr } from "@/lib/i18n/cliente";
import { Carregando } from "@/components/ui/Esqueleto";

type Ultimo = { valor: number; data: string; anterior: number | null; data_anterior: string | null };
interface AtletaTestes {
  atleta_id: string;
  nome: string;
  data_nascimento: string | null;
  idade: number | null;
  altura_pai_cm: number | null;
  altura_mae_cm: number | null;
  ultimos: Record<string, Ultimo>;
  maturacao: { data: string; altura_cm: number; estatura_prevista_cm: number; pct_estatura_adulta: number; crescimento_restante_cm: number; categoria: string } | null;
}
interface Resposta {
  team_id: string;
  rotulo: string;
  atletas: AtletaTestes[];
  catalogo: Record<string, Metrica>;
  baterias: Record<string, { titulo: string; metricas: string[] }>;
  maturacao_disponivel: boolean;
}

const COR_MAT: Record<string, string> = {
  "Pré-púbere": cores.info, "Início da puberdade": cores.atencao, "Meio da puberdade": cores.perigo, "Fim da puberdade": cores.sucesso,
};

/** T1 jul–set · T2 out–dez · T3 jan–mar · T4 abr–jun (sugestão; pode mudar-se). */
function momentoPorData(iso: string) {
  const m = Number(iso.slice(5, 7));
  return m >= 7 && m <= 9 ? 1 : m >= 10 ? 2 : m <= 3 ? 3 : 4;
}

function hojeIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** "3:45" → 225; "1,92" → 1.92. */
function paraNumero(v: string): number | null {
  const t = v.trim().replace(",", ".");
  if (!t) return null;
  const mm = /^(\d+):(\d{1,2}(?:\.\d+)?)$/.exec(t);
  if (mm) return Number(mm[1]) * 60 + Number(mm[2]);
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
}

function fmt(v: number | null | undefined, m: Metrica, loc: string) {
  if (v == null) return "—";
  if (m.unidade === "s" && v >= 60) {
    const t = Math.round(v);
    return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`;
  }
  return v.toLocaleString(loc, { minimumFractionDigits: m.casas, maximumFractionDigits: m.casas });
}

/** Separador de uma equipa: baterias de testes para o plantel inteiro. */
export function TestesEquipa({ teamId }: { teamId: string }) {
  const tr = useTr();
  const [dados, setDados] = useState<Resposta | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [bateria, setBateria] = useState("velocidade");
  const [dia, setDia] = useState(hojeIso());
  const [momento, setMomento] = useState(() => momentoPorData(hojeIso()));
  const [novos, setNovos] = useState<Record<string, Record<string, string>>>({});
  const [aviso, setAviso] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);
  const [aGravar, setAGravar] = useState(false);

  async function carregar() {
    try {
      const d = await pedidoApi<Resposta>(`/api/academia/equipas/${teamId}/testes`);
      setDados(d);
      // Alturas dos pais já guardadas aparecem preenchidas.
      setNovos(Object.fromEntries(d.atletas.map((a) => [a.atleta_id, {
        altura_pai_cm: a.altura_pai_cm != null ? String(a.altura_pai_cm) : "",
        altura_mae_cm: a.altura_mae_cm != null ? String(a.altura_mae_cm) : "",
      }])));
    } catch (e) {
      setErro(e instanceof Error ? e.message : tr("Erro inesperado."));
    }
  }
  useEffect(() => {
    carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [teamId]);

  const bat = dados?.baterias[bateria];
  const metricas = useMemo(() => (bat?.metricas ?? []).map((k) => dados!.catalogo[k]), [bat, dados]);

  if (erro) return <div style={{ padding: espaco.xxl }}><Vazio>{erro}</Vazio></div>;
  if (!dados) return <Carregando cartoes={0} linhas={10} />;

  const set = (aid: string, k: string, v: string) => setNovos((n) => ({ ...n, [aid]: { ...n[aid], [k]: v } }));
  const maturacao = bateria === "maturacao";
  const saltos = bateria === "saltos";

  // Média da equipa do último valor de cada métrica.
  const media = (k: string) => {
    const v = dados.atletas.map((a) => a.ultimos[k]?.valor).filter((x): x is number => x != null);
    return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
  };

  async function guardar() {
    setAviso(null);
    const linhas = dados!.atletas.map((a) => {
      const n = novos[a.atleta_id] ?? {};
      const valores: Record<string, number> = {};
      for (const k of bat!.metricas) {
        if (k === "assimetria_cmj_pct") continue; // calculada ao guardar
        const v = paraNumero(n[k] ?? "");
        if (v != null) valores[k] = v;
      }
      const linha: Record<string, unknown> = { atleta_id: a.atleta_id, valores };
      if (maturacao) {
        linha.altura_pai_cm = paraNumero(n.altura_pai_cm ?? "");
        linha.altura_mae_cm = paraNumero(n.altura_mae_cm ?? "");
      }
      return linha;
    }).filter((l) => Object.keys(l.valores as object).length || maturacao);
    if (!linhas.length) {
      setAviso({ tipo: "erro", texto: tr("Não há valores novos para guardar.") });
      return;
    }
    setAGravar(true);
    try {
      const r = await pedidoApi<{ registadas: number }>(`/api/academia/equipas/${teamId}/testes`, "POST", { data: dia, linhas, momento });
      setAviso({ tipo: "ok", texto: tr("Guardado: {0} valor(es) a {1} (T{2}).", [r.registadas, new Date(`${dia}T00:00:00`).toLocaleDateString(tr.loc), momento]) });
      await carregar();
    } catch (e) {
      setAviso({ tipo: "erro", texto: e instanceof Error ? e.message : tr("Erro inesperado.") });
    } finally {
      setAGravar(false);
    }
  }

  return (
    <div>
      <PageHeader titulo={tr("Academia · {0}", [dados.rotulo])} subtitulo={tr("{0} atleta(s) · registar testes — os resultados ficam no separador Resultados", [dados.atletas.length])} />
      <NavEquipa teamId={teamId} />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px`, display: "flex", flexDirection: "column", gap: espaco.lg, maxWidth: 1300 }}>
        {dados.atletas.length === 0 ? (
          <Vazio>{tr("Esta equipa ainda não tem jogadores. Adiciona-os no separador")}{" "}<Link href="/academia" style={{ color: cores.textoForte }}>{tr("Jogadores")}</Link>.</Vazio>
        ) : (
          <>
            <div style={{ display: "flex", gap: espaco.sm, flexWrap: "wrap", alignItems: "center" }}>
              <div role="tablist" style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                {Object.entries(dados.baterias).map(([k, b]) => (
                  <button key={k} role="tab" aria-selected={bateria === k} onClick={() => { setBateria(k); setAviso(null); }}
                    style={bateria === k ? estiloBotao.primario : estiloBotao.secundario}>{tr(b.titulo)}</button>
                ))}
              </div>
              <label style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6, fontSize: letra.texto, color: cores.textoSuave }}>
                {tr("Dia do teste")}<input type="date" value={dia} max={hojeIso()} onChange={(e) => { setDia(e.target.value); if (e.target.value) setMomento(momentoPorData(e.target.value)); }} style={campo} />
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: letra.texto, color: cores.textoSuave }} title={tr("Momento de avaliação da época (4 por época)")}>
                {tr("Momento")}<select value={momento} onChange={(e) => setMomento(Number(e.target.value))} style={campo}>
                  {[1, 2, 3, 4].map((m) => <option key={m} value={m}>T{m}</option>)}
                </select>
              </label>
              <button style={estiloBotao.primario} disabled={aGravar} onClick={guardar}>{aGravar ? tr("A guardar…") : tr("Guardar")}</button>
            </div>
            {aviso && <div style={{ fontSize: letra.texto, color: aviso.tipo === "ok" ? cores.sucesso : cores.perigo }}>{aviso.texto}</div>}
            <Explicacao bateria={bateria} disponivel={dados.maturacao_disponivel} />

            <Cartao padding={0}>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 760 }}>
                  <thead>
                    <tr>
                      <th style={th}>{tr("Atleta")}</th>
                      <th style={{ ...th, textAlign: "right" }}>{tr("Idade")}</th>
                      {metricas.map((m) => <th key={m.chave} style={{ ...th, textAlign: "right" }}>{tr(m.label)}{m.unidade ? ` (${m.unidade === "s" && m.chave === "corrida_1km_s" ? "m:ss" : m.unidade})` : ""}</th>)}
                      {maturacao && <>
                        <th style={{ ...th, textAlign: "right" }}>{tr("Pai (cm)")}</th>
                        <th style={{ ...th, textAlign: "right" }}>{tr("Mãe (cm)")}</th>
                        <th style={{ ...th, textAlign: "right" }} title={tr("Percentagem da estatura adulta prevista")}>{tr("%PAH")}</th>
                        <th style={{ ...th, textAlign: "right" }} title={tr("Estatura adulta prevista (Khamis-Roche)")}>{tr("PAH")}</th>
                        <th style={{ ...th, textAlign: "right" }}>{tr("Falta crescer")}</th>
                        <th style={th}>{tr("Estado")}</th>
                      </>}
                    </tr>
                  </thead>
                  <tbody>
                    {dados.atletas.map((a) => {
                      const n = novos[a.atleta_id] ?? {};
                      const assimNova = saltos ? (() => {
                        const e = paraNumero(n.cmj_esq_cm ?? ""), d = paraNumero(n.cmj_dir_cm ?? "");
                        return e && d ? Math.abs(e - d) / Math.max(e, d) * 100 : null;
                      })() : null;
                      return (
                        <tr key={a.atleta_id} style={{ borderTop: `1px solid ${cores.borda}` }}>
                          <td style={td}>
                            <Link href={`/academia/atleta/${a.atleta_id}`} style={{ color: cores.textoForte, fontWeight: 600, textDecoration: "none" }}>
                              <NomeJogador nome={a.nome} />
                            </Link>
                          </td>
                          <td style={{ ...td, textAlign: "right", color: cores.textoSuave }}>{a.idade != null ? a.idade.toLocaleString(tr.loc, { maximumFractionDigits: 1 }) : "—"}</td>
                          {metricas.map((m) => (
                            <td key={m.chave} style={{ ...td, textAlign: "right" }}>
                              {m.chave === "assimetria_cmj_pct" ? (
                                <div style={{ ...campo, width: 72, marginLeft: "auto", display: "flex", alignItems: "center", justifyContent: "flex-end", background: cores.superficie,
                                  color: assimNova != null && assimNova >= 10 ? cores.atencao : cores.textoSuave, fontWeight: assimNova != null && assimNova >= 10 ? 700 : 400 }}>
                                  {assimNova != null ? `${assimNova.toLocaleString(tr.loc, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} %` : "auto"}
                                </div>
                              ) : (
                                <input inputMode="decimal" value={n[m.chave] ?? ""} placeholder={m.chave === "corrida_1km_s" ? tr("m:ss") : ""}
                                  onChange={(e) => set(a.atleta_id, m.chave, e.target.value)}
                                  style={{ ...campo, width: 72, textAlign: "right" }} />
                              )}
                              <Anterior u={a.ultimos[m.chave]} m={m} />
                            </td>
                          ))}
                          {maturacao && <>
                            {(["altura_pai_cm", "altura_mae_cm"] as const).map((k) => (
                              <td key={k} style={{ ...td, textAlign: "right" }}>
                                <input inputMode="decimal" value={n[k] ?? ""} onChange={(e) => set(a.atleta_id, k, e.target.value)} style={{ ...campo, width: 68, textAlign: "right" }} />
                              </td>
                            ))}
                            <CelulasPah a={a} n={n} dia={dia} />
                          </>}
                        </tr>
                      );
                    })}
                    <tr style={{ borderTop: `1px solid ${cores.bordaForte}`, background: cores.superficie }}>
                      <td style={{ ...td, fontWeight: 600 }}>{tr("Média da equipa")}</td>
                      <td style={td} />
                      {metricas.map((m) => <td key={m.chave} style={{ ...td, textAlign: "right", fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>{fmt(media(m.chave), m, tr.loc)}</td>)}
                      {maturacao && <td colSpan={6} style={td} />}
                    </tr>
                  </tbody>
                </table>
              </div>
            </Cartao>
          </>
        )}
      </div>
    </div>
  );
}

/** %PAH, PAH, falta crescer e estado — calculados em tempo real com o que se
 * está a escrever (ou, se o campo estiver vazio, com o último valor guardado). */
function CelulasPah({ a, n, dia }: { a: AtletaTestes; n: Record<string, string>; dia: string }) {
  const tr = useTr();
  const escrito = (k: string) => paraNumero(n[k] ?? "");
  const altura = escrito("altura_cm") ?? a.ultimos.altura_cm?.valor ?? null;
  const peso = escrito("peso_kg") ?? a.ultimos.peso_kg?.valor ?? null;
  const pai = escrito("altura_pai_cm");
  const mae = escrito("altura_mae_cm");
  const novo = escrito("altura_cm") != null || escrito("peso_kg") != null
    || pai !== a.altura_pai_cm || mae !== a.altura_mae_cm;
  // Valores já guardados contam a idade no dia em que foram medidos.
  const diaRef = escrito("altura_cm") != null || escrito("peso_kg") != null ? dia : a.ultimos.altura_cm?.data ?? dia;
  const r = khamisRoche(idadeEm(a.data_nascimento, diaRef), altura, peso, pai, mae);
  const falta = [!a.data_nascimento && tr("data de nascimento"), !altura && tr("altura"), !peso && tr("peso"), !pai && tr("pai"), !mae && tr("mãe")].filter(Boolean);
  const fmt1 = (v: number) => v.toLocaleString(tr.loc, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  if (!r) {
    return (
      <>
        <td style={{ ...td, textAlign: "right" }}>—</td>
        <td style={{ ...td, textAlign: "right" }}>—</td>
        <td style={{ ...td, textAlign: "right" }}>—</td>
        <td style={{ ...td, color: cores.textoFraco, fontSize: letra.pequeno }}>{falta.length ? tr("falta: {0}", [falta.join(", ")]) : tr("idade fora dos 4–17,5 anos")}</td>
      </>
    );
  }
  return (
    <>
      <td style={{ ...td, textAlign: "right", fontWeight: 700, color: cores.textoForte, fontVariantNumeric: "tabular-nums" }}>{fmt1(r.pct_pah)} %</td>
      <td style={{ ...td, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{fmt1(r.pah_cm)} {tr("cm")}</td>
      <td style={{ ...td, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{fmt1(r.falta_cm)} {tr("cm")}</td>
      <td style={td}>
        <Etiqueta cor={COR_MAT[r.categoria] ?? cores.textoSuave}>{tr(r.categoria)}</Etiqueta>
        {novo && <div style={{ fontSize: letra.legenda, color: cores.atencao, marginTop: 4 }}>{tr("por guardar")}</div>}
      </td>
    </>
  );
}

/** Último valor registado (e a seta face ao anterior: verde = melhorou). */
function Anterior({ u, m }: { u?: Ultimo; m: Metrica }) {
  const tr = useTr();
  if (!u) return <div style={{ minHeight: 15 }} />;
  let seta = "";
  let cor: string = cores.textoFraco;
  if (u.anterior != null && m.maior_melhor != null && u.valor !== u.anterior) {
    const melhorou = m.maior_melhor ? u.valor > u.anterior : u.valor < u.anterior;
    seta = melhorou ? " ▲" : " ▼";
    cor = melhorou ? cores.sucesso : cores.atencao;
  }
  return (
    <div style={{ fontSize: letra.legenda, color: cores.textoSuave, minHeight: 15, whiteSpace: "nowrap" }} title={u.anterior != null ? tr("anterior: {0} ({1})", [fmt(u.anterior, m, tr.loc), u.data_anterior]) : undefined}>
      {tr("último")}{" "}{fmt(u.valor, m, tr.loc)} · {u.data.slice(8, 10)}/{u.data.slice(5, 7)}<span style={{ color: cor }}>{seta}</span>
    </div>
  );
}

function Explicacao({ bateria, disponivel }: { bateria: string; disponivel: boolean }) {
  const tr = useTr();
  const textos: Record<string, string> = {
    velocidade: "Tempos em segundos (ex.: 1,92). Escreve só os que mediste — o resto fica como estava.",
    resistencia: "6 min: distância máxima corrida em 6 minutos, em metros (ex.: 1620) — a MAS é a distância ÷ 360 s. 1 km: tempo em minutos:segundos (ex.: 3:45). Basta um dos dois.",
    forca: "Agachamento: 1RM em kg (ou o estimado de uma série de 3–5 repetições). Nordic e adutores em newtons (dinamómetro ou NordBord/ForceFrame).",
    maturacao: "Khamis-Roche: escreve a altura, o peso e a altura do pai e da mãe — o PAH (estatura adulta prevista) e o %PAH (altura atual ÷ PAH) calculam-se logo, com a idade no dia do teste. Estado (Cumming et al. 2017): %PAH < 85 pré-púbere · 85–90 início · 90–95 meio · ≥ 95 fim da puberdade. Guarda para ficar registado.",
    saltos: "CMJ bilateral e CMJ unilateral (perna esquerda e direita) em cm; RSI tal como o dá o teu sistema de saltos. A assimetria calcula-se sozinha (diferença entre pernas ÷ a melhor) — a laranja a partir de 10 %.",
  };
  return (
    <p style={{ fontSize: letra.pequeno, color: cores.textoSuave, margin: 0, lineHeight: 1.5, background: cores.superficie, borderRadius: raio.sm, padding: `${espaco.sm}px ${espaco.md}px` }}>
      {tr(textos[bateria])}
      {bateria === "maturacao" && !disponivel && <strong style={{ color: cores.atencao }}> {tr("Falta aplicar a migração 0011 para guardar a altura dos pais.")}</strong>}
    </p>
  );
}

const campo: React.CSSProperties = { ...estiloCampo };
const th: React.CSSProperties = { ...estiloTh, padding: PAD_DENSO, textAlign: "left", whiteSpace: "nowrap" };
const td: React.CSSProperties = { ...estiloTd, padding: PAD_DENSO, fontSize: letra.pequeno, verticalAlign: "top" };
