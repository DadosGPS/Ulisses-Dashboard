"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { pedidoApi } from "@/lib/api-cliente";
import { cores, espaco, raio } from "@/lib/theme";
import { PageHeader } from "@/components/layout/PageHeader";
import { Cartao, Etiqueta, SecaoTitulo, Vazio, estiloBotao } from "@/components/ui/base";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import type { Comparacao, FichaAtleta, Metrica } from "./tipos";
import { useTr, linguaDoCookie } from "@/lib/i18n/cliente";

/** Carrega a ficha e trata das gravações; a apresentação está em FichaConteudo. */
export function FichaAtletaView({ atletaId }: { atletaId: string }) {
  const tr = useTr();
  const [ficha, setFicha] = useState<FichaAtleta | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  async function carregar() {
    try {
      setFicha(await pedidoApi<FichaAtleta>(`/api/academia/atletas/${atletaId}`));
    } catch (e) {
      setErro(e instanceof Error ? e.message : tr("Erro inesperado."));
    }
  }
  useEffect(() => {
    carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [atletaId]);

  if (erro) return <div style={{ padding: espaco.xxl }}><Vazio>{erro}</Vazio></div>;
  if (!ficha) return <p style={{ padding: espaco.xxl, color: cores.textoSuave }}>{tr("A carregar a ficha…")}</p>;

  return (
    <FichaConteudo
      ficha={ficha}
      guardarAtleta={async (dados) => {
        await pedidoApi(`/api/academia/atletas/${atletaId}`, "PATCH", dados);
        await carregar();
      }}
      registarAvaliacao={async (dados) => {
        await pedidoApi(`/api/academia/atletas/${atletaId}/avaliacoes`, "POST", dados);
        await carregar();
      }}
      apagarAvaliacao={async (id) => {
        await pedidoApi(`/api/academia/avaliacoes/${id}`, "DELETE");
        await carregar();
      }}
    />
  );
}

type Acoes = {
  guardarAtleta: (d: { data_nascimento: string | null; posicao: string | null; pe_dominante: string | null; altura_pai_cm: number | null; altura_mae_cm: number | null; altura_pais_medida: boolean | null }) => Promise<void>;
  registarAvaliacao: (d: { data: string; team_id: string | null; valores: Record<string, string>; notas: string }) => Promise<void>;
  apagarAvaliacao: (id: string) => Promise<void>;
};

export function FichaConteudo({ ficha, ...acoes }: { ficha: FichaAtleta } & Acoes) {
  const tr = useTr();
  const { oculto } = usePrivacidade();
  const a = ficha.atleta;
  const ultimo = ficha.percurso[ficha.percurso.length - 1];
  const mat = ficha.maturacao[ficha.maturacao.length - 1];
  const nasc = a.data_nascimento ? new Date(`${a.data_nascimento}T00:00:00`).toLocaleDateString(tr.loc) : null;

  return (
    <div>
      <PageHeader
        titulo={nomeOuOculto(a.nome, oculto)}
        subtitulo={[
          a.idade != null ? tr("{0} anos", [Math.floor(a.idade)]) : null,
          nasc ? tr("nascido a {0}", [nasc]) : null,
          a.posicao,
          a.pe_dominante ? tr("pé {0}", [tr(a.pe_dominante)]) : null,
          ultimo ? `${ultimo.escalao ?? ultimo.equipa}${ultimo.epoca ? ` · ${ultimo.epoca}` : ""}` : null,
        ].filter(Boolean).join(" · ")}
        acoes={<Link href="/academia" style={{ ...estiloBotao.secundario, textDecoration: "none" }}>{tr("Todos os atletas")}</Link>}
      />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px`, display: "flex", flexDirection: "column", gap: espaco.xl }}>
        {a.consentimento && !a.consentimento.data && (
          <div style={{ fontSize: "0.82rem", color: cores.atencao, border: `1px solid ${cores.atencao}`, borderRadius: raio.sm, padding: `${espaco.sm}px ${espaco.md}px` }}>
            {tr("Falta registar o consentimento para o tratamento dos dados deste atleta — ver “Proteção de dados” no fim da ficha.")}</div>
        )}
        <DadosAtleta ficha={ficha} guardar={acoes.guardarAtleta} />

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 320px), 1fr))", gap: espaco.lg, alignItems: "start" }}>
          <Percurso ficha={ficha} />
          <Maturacao ficha={ficha} mat={mat} historico={ficha.maturacao} />
        </div>

        <EntradaVsUltima linhas={ficha.entrada_vs_ultima} />
        <Evolucao ficha={ficha} />
        <CargaJogo linhas={ficha.carga_jogo} />
        <RegistarAvaliacao ficha={ficha} registar={acoes.registarAvaliacao} apagar={acoes.apagarAvaliacao} />
        {a.consentimento !== undefined && a.consentimento !== null && <ProtecaoDados ficha={ficha} />}
      </div>
    </div>
  );
}

// ── Identificação ────────────────────────────────────────────────────────────
function DadosAtleta({ ficha, guardar }: { ficha: FichaAtleta; guardar: Acoes["guardarAtleta"] }) {
  const tr = useTr();
  const a = ficha.atleta;
  const [aberto, setAberto] = useState(ficha.sem_data_nascimento);
  const [form, setForm] = useState({
    data_nascimento: a.data_nascimento ?? "", posicao: a.posicao ?? "", pe_dominante: a.pe_dominante ?? "",
    altura_pai_cm: a.altura_pai_cm != null ? String(a.altura_pai_cm) : "",
    altura_mae_cm: a.altura_mae_cm != null ? String(a.altura_mae_cm) : "",
    altura_pais_medida: a.altura_pais_medida == null ? "" : a.altura_pais_medida ? "medida" : "declarada",
  });
  const [estado, setEstado] = useState<string | null>(null);
  if (!aberto) {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: -espaco.md }}>
        <button style={estiloBotao.ligacao} onClick={() => setAberto(true)}>{tr("Editar dados do atleta")}</button>
      </div>
    );
  }
  return (
    <Cartao destaque={ficha.sem_data_nascimento ? cores.atencao : undefined}>
      {ficha.sem_data_nascimento && (
        <p style={{ margin: `0 0 ${espaco.md}px`, fontSize: "0.84rem", color: cores.texto }}>
          {tr("Falta a data de nascimento — é ela que permite calcular a idade em cada avaliação, a maturação e os percentis face aos colegas da mesma idade.")}</p>
      )}
      <div style={{ display: "flex", gap: espaco.md, flexWrap: "wrap", alignItems: "flex-end" }}>
        <Campo rotulo={tr("Data de nascimento")}><input type="date" value={form.data_nascimento} onChange={(e) => setForm({ ...form, data_nascimento: e.target.value })} style={campo} /></Campo>
        <Campo rotulo={tr("Posição principal")}><input value={form.posicao} placeholder={tr("ex.: MC")} onChange={(e) => setForm({ ...form, posicao: e.target.value })} style={{ ...campo, width: 110 }} /></Campo>
        <Campo rotulo={tr("Pé dominante")}>
          <select value={form.pe_dominante} onChange={(e) => setForm({ ...form, pe_dominante: e.target.value })} style={campo}>
            <option value="">—</option><option value="direito">{tr("Direito")}</option><option value="esquerdo">{tr("Esquerdo")}</option><option value="ambos">{tr("Ambos")}</option>
          </select>
        </Campo>
        <Campo rotulo={tr("Altura do pai (cm)")}><input inputMode="decimal" value={form.altura_pai_cm} placeholder={tr("ex.: 178")} onChange={(e) => setForm({ ...form, altura_pai_cm: e.target.value.replace(",", ".") })} style={{ ...campo, width: 100 }} /></Campo>
        <Campo rotulo={tr("Altura da mãe (cm)")}><input inputMode="decimal" value={form.altura_mae_cm} placeholder={tr("ex.: 164")} onChange={(e) => setForm({ ...form, altura_mae_cm: e.target.value.replace(",", ".") })} style={{ ...campo, width: 100 }} /></Campo>
        <Campo rotulo={tr("Alturas dos pais")}>
          <select value={form.altura_pais_medida} onChange={(e) => setForm({ ...form, altura_pais_medida: e.target.value })} style={campo}>
            <option value="">—</option><option value="medida">{tr("Medidas")}</option><option value="declarada">{tr("Declaradas")}</option>
          </select>
        </Campo>
        <button style={estiloBotao.primario} onClick={async () => {
          setEstado(tr("A guardar…"));
          try {
            await guardar({
              data_nascimento: form.data_nascimento || null, posicao: form.posicao || null, pe_dominante: form.pe_dominante || null,
              altura_pai_cm: form.altura_pai_cm ? Number(form.altura_pai_cm) : null,
              altura_mae_cm: form.altura_mae_cm ? Number(form.altura_mae_cm) : null,
              altura_pais_medida: form.altura_pais_medida ? form.altura_pais_medida === "medida" : null,
            });
            setEstado(null);
            setAberto(false);
          } catch (e) {
            setEstado(e instanceof Error ? e.message : tr("Erro."));
          }
        }}>{tr("Guardar")}</button>
        {!ficha.sem_data_nascimento && <button style={estiloBotao.secundario} onClick={() => setAberto(false)}>{tr("Cancelar")}</button>}
        <button style={{ ...estiloBotao.ligacao, color: cores.perigo, marginLeft: "auto" }} onClick={async () => {
          if (!confirm(tr("Apagar a ficha de {0}? As avaliações registadas perdem-se; as sessões de GPS ficam nas equipas.", [a.nome]))) return;
          try {
            await pedidoApi(`/api/academia/atletas/${a.atleta_id}`, "DELETE");
            window.location.href = "/academia";
          } catch (e) {
            setEstado(e instanceof Error ? e.message : tr("Erro."));
          }
        }}>{tr("Apagar atleta")}</button>
        {estado && <span style={{ fontSize: "0.8rem", color: cores.textoSuave }}>{estado}</span>}
      </div>
    </Cartao>
  );
}

// ── Percurso ─────────────────────────────────────────────────────────────────
function Percurso({ ficha }: { ficha: FichaAtleta }) {
  const tr = useTr();
  return (
    <section>
      <SecaoTitulo subtitulo={tr("{0} equipa(s) na academia", [ficha.percurso.length])}>{tr("Percurso")}</SecaoTitulo>
      <Cartao padding={0}>
        {ficha.percurso.map((p, i) => (
          <div key={p.player_id} style={{ display: "grid", gridTemplateColumns: "84px minmax(0,1fr) auto", gap: espaco.md, alignItems: "center", padding: `9px ${espaco.lg}px`, borderTop: i ? `1px solid ${cores.borda}` : "none", fontSize: "0.84rem" }}>
            <span style={{ color: cores.textoSuave, fontVariantNumeric: "tabular-nums" }}>{p.epoca ?? "—"}</span>
            <span style={{ color: cores.textoForte, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {p.escalao ?? p.equipa}{p.posicao && <span style={{ color: cores.textoFraco, fontWeight: 400 }}> · {p.posicao}</span>}
            </span>
            <span style={{ color: cores.textoSuave, fontSize: "0.76rem", whiteSpace: "nowrap" }}>
              {p.sessoes} {tr("sessões")}{p.lesoes ? tr(" · {0} lesão(ões)", [p.lesoes]) : ""}
            </span>
          </div>
        ))}
      </Cartao>
    </section>
  );
}

// ── Maturação ────────────────────────────────────────────────────────────────
const COR_MAT: Record<string, string> = {
  "Pré-púbere": cores.info,
  "Início da puberdade": cores.atencao,
  "Meio da puberdade": cores.perigo,
  "Fim da puberdade": cores.sucesso,
};

function Maturacao({ ficha, mat, historico }: { ficha: FichaAtleta; mat?: FichaAtleta["maturacao"][number]; historico: FichaAtleta["maturacao"] }) {
  const tr = useTr();
  const a = ficha.atleta;
  const faltaPais = !a.altura_pai_cm || !a.altura_mae_cm;
  const n = (v: number) => v.toLocaleString(tr.loc, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  return (
    <section>
      <SecaoTitulo subtitulo={tr("Khamis-Roche (1994): estatura adulta prevista a partir da idade, altura, peso e altura dos pais. % da estatura adulta → estado maturacional (Cumming et al. 2017).")}>
        {tr("Maturação biológica")}</SecaoTitulo>
      {!ficha.maturacao_disponivel ? (
        <Vazio>{tr("Aplica a migração 0011 no Supabase para ativar a maturação Khamis-Roche.")}</Vazio>
      ) : !mat ? (
        <Vazio>
          {faltaPais
            ? tr("Preenche a altura do pai e da mãe em “Editar dados do atleta” e regista a altura e o peso no mesmo dia.")
            : tr("Regista a altura e o peso no mesmo dia (com a data de nascimento preenchida, entre os 4 e os 17,5 anos).")}
        </Vazio>
      ) : (
        <Cartao>
          <div style={{ display: "flex", alignItems: "baseline", gap: espaco.md, flexWrap: "wrap" }}>
            <span className="font-display" style={{ fontSize: "1.6rem", fontWeight: 600, color: cores.textoForte, fontVariantNumeric: "tabular-nums" }}>
              {n(mat.pct_estatura_adulta)} %
            </span>
            <span style={{ fontSize: "0.8rem", color: cores.textoSuave }}>{tr("%PAH (da estatura adulta prevista)")}</span>
            <Etiqueta cor={COR_MAT[mat.categoria] ?? cores.textoSuave}>{tr(mat.categoria)}</Etiqueta>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: espaco.md, marginTop: espaco.md }}>
            {[
              ["Altura atual", `${n(mat.altura_cm)} cm`],
              ["PAH (estatura adulta prevista)", `${n(mat.estatura_prevista_cm)} cm`],
              ["Falta crescer", `${n(mat.crescimento_restante_cm)} cm`],
            ].map(([r, v]) => (
              <div key={r}>
                <div style={{ fontSize: "0.68rem", color: cores.textoFraco, textTransform: "uppercase", letterSpacing: "0.04em" }}>{tr(r)}</div>
                <div style={{ fontSize: "0.95rem", color: cores.textoForte, fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>{v}</div>
              </div>
            ))}
          </div>
          <p style={{ fontSize: "0.78rem", color: cores.textoSuave, margin: `${espaco.md}px 0 0`, lineHeight: 1.5 }}>
            {tr("Medido a")}{" "}{new Date(`${mat.data}T00:00:00`).toLocaleDateString(tr.loc)} ({mat.idade.toLocaleString(tr.loc)} {tr("anos). Erro típico da previsão ±2–3 cm.")}{a.altura_pais_medida === false && tr(" Alturas dos pais declaradas (não medidas): costumam vir sobrestimadas.")}
          </p>
          {historico.length > 1 && (
            <div style={{ marginTop: espaco.md, display: "flex", gap: 6, flexWrap: "wrap" }}>
              {historico.map((h) => (
                <span key={h.data} title={h.data} style={{ fontSize: "0.72rem", color: cores.textoSuave, background: cores.superficie, padding: "2px 7px", borderRadius: 6, fontVariantNumeric: "tabular-nums" }}>
                  {h.idade.toLocaleString(tr.loc)} a → {n(h.pct_estatura_adulta)} %
                </span>
              ))}
            </div>
          )}
        </Cartao>
      )}
    </section>
  );
}

// ── Entrada vs última avaliação ──────────────────────────────────────────────
/** Segundos ≥ 60 (ex.: corrida de 1 km) mostram-se como m:ss. */
function fmt(v: number, m: { unidade: string; casas?: number }, loc: string) {
  if (m.unidade === "s" && Math.abs(v) >= 60) {
    const t = Math.round(Math.abs(v));
    return `${v < 0 ? "−" : ""}${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`;
  }
  const c = m.casas ?? 2;
  return `${v.toLocaleString(loc, { minimumFractionDigits: c, maximumFractionDigits: c })}${m.unidade ? ` ${m.unidade}` : ""}`;
}

/** Percentil: verde/vermelho só em métricas de desempenho; na antropometria
 * (neutra) um percentil alto não é "melhor", por isso fica em cinzento. */
function CelulaPct({ p, neutro }: { p: number | null; neutro?: boolean }) {
  if (p == null) return <span style={{ color: cores.textoFraco }}>—</span>;
  const cor = neutro ? cores.textoSuave : p >= 75 ? cores.sucesso : p <= 25 ? cores.perigo : cores.textoSuave;
  return <span style={{ color: cor, fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>P{p}</span>;
}

function EntradaVsUltima({ linhas }: { linhas: Comparacao[] }) {
  const tr = useTr();
  return (
    <section>
      <SecaoTitulo subtitulo={tr("Primeira e última avaliação de cada métrica. P = percentil face aos atletas da academia com a mesma idade (alto = melhor; na antropometria, alto = maior).")}>
        {tr("Como chegou vs como está")}</SecaoTitulo>
      {linhas.length === 0 ? (
        <Vazio>{tr("Ainda não há avaliações. Regista a primeira no fim desta página.")}</Vazio>
      ) : (
        <Cartao padding={0}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 680 }}>
              <thead>
                <tr>
                  <th style={{ ...th, textAlign: "left" }}>{tr("Métrica")}</th>
                  <th style={th}>{tr("Entrada")}</th><th style={th} />
                  <th style={th}>{tr("Última")}</th><th style={th} />
                  <th style={th}>{tr("Variação")}</th>
                </tr>
              </thead>
              <tbody>
                {linhas.map((l, i) => {
                  const grupoNovo = i === 0 || linhas[i - 1].grupo !== l.grupo;
                  const corVar = l.melhorou == null ? cores.textoSuave : l.melhorou ? cores.sucesso : cores.perigo;
                  return [
                    grupoNovo && (
                      <tr key={`g-${l.grupo}`}><td colSpan={6} style={{ padding: `10px ${espaco.lg}px 4px`, fontSize: "0.68rem", color: cores.textoFraco, letterSpacing: "0.04em", textTransform: "uppercase", borderTop: i ? `1px solid ${cores.borda}` : "none" }}>{tr(l.grupo)}</td></tr>
                    ),
                    <tr key={l.metrica}>
                      <td style={{ ...td, color: cores.textoForte, fontWeight: 600 }}>{tr(l.label)}</td>
                      <td style={tdNum}>{fmt(l.entrada.valor, l, tr.loc)}<div style={sub}>{l.entrada.idade != null ? `${l.entrada.idade.toLocaleString(tr.loc)} anos` : l.entrada.data}</div></td>
                      <td style={tdNum}><CelulaPct p={l.entrada.percentil} neutro={l.maior_melhor == null} /></td>
                      <td style={tdNum}>{l.n_avaliacoes > 1 ? fmt(l.ultima.valor, l, tr.loc) : "—"}<div style={sub}>{l.n_avaliacoes > 1 ? (l.ultima.idade != null ? `${l.ultima.idade.toLocaleString(tr.loc)} anos` : l.ultima.data) : tr("uma só avaliação")}</div></td>
                      <td style={tdNum}>{l.n_avaliacoes > 1 ? <CelulaPct p={l.ultima.percentil} neutro={l.maior_melhor == null} /> : null}</td>
                      <td style={{ ...tdNum, color: corVar, fontWeight: 600 }}>
                        {l.n_avaliacoes > 1 ? `${l.variacao > 0 ? "+" : ""}${l.variacao.toLocaleString(tr.loc, { minimumFractionDigits: l.casas, maximumFractionDigits: l.casas })}${l.variacao_pct != null ? ` (${l.variacao_pct > 0 ? "+" : ""}${l.variacao_pct.toLocaleString(tr.loc)}%)` : ""}` : "—"}
                      </td>
                    </tr>,
                  ];
                })}
              </tbody>
            </table>
          </div>
        </Cartao>
      )}
    </section>
  );
}

// ── Evolução de uma métrica ao longo da idade ────────────────────────────────
function Evolucao({ ficha }: { ficha: FichaAtleta }) {
  const tr = useTr();
  const disponiveis = ficha.catalogo.filter((m) => (ficha.series[m.chave]?.length ?? 0) > 0);
  const [chave, setChave] = useState<string | null>(null);
  const m: Metrica | undefined = disponiveis.find((x) => x.chave === chave) ?? disponiveis[0];
  const grafico = useMemo(() => {
    if (!m) return null;
    const pontos = ficha.series[m.chave] ?? [];
    const porIdade = pontos.every((p) => p.idade != null);
    const x = pontos.map((p) => (porIdade ? p.idade : p.data));
    const banda = porIdade ? ficha.bandas[m.chave] ?? [] : [];
    const data: Record<string, unknown>[] = [];
    if (banda.length) {
      const bx = banda.map((b) => b.idade + 0.5);
      data.push({ x: bx, y: banda.map((b) => b.p75), mode: "lines", line: { width: 0 }, hoverinfo: "skip", showlegend: false });
      data.push({ x: bx, y: banda.map((b) => b.p25), mode: "lines", line: { width: 0 }, fill: "tonexty", fillcolor: "rgb(var(--ink) / 0.08)", name: tr("Academia P25–P75"), hoverinfo: "skip" });
      data.push({ x: bx, y: banda.map((b) => b.p50), mode: "lines", line: { color: "rgb(var(--ink) / 0.35)", dash: "dot", width: 1.5 }, name: tr("Mediana da academia") });
    }
    data.push({
      x, y: pontos.map((p) => p.valor), mode: "lines+markers", name: tr("Atleta"),
      line: { color: cores.acento, width: 2.5 }, marker: { size: 7, color: cores.acento },
      hovertemplate: tr("%{y} {0}<extra></extra>", [m.unidade]),
    });
    return {
      data,
      layout: {
        margin: { l: 50, r: 16, t: 10, b: 40 },
        xaxis: { title: { text: porIdade ? tr("Idade (anos)") : tr("Data") }, gridcolor: cores.borda, showgrid: true },
        yaxis: { title: { text: m.unidade }, autorange: m.maior_melhor === false ? "reversed" : true, gridcolor: cores.borda, showgrid: true },
        legend: { orientation: "h", y: -0.25 },
        showlegend: banda.length > 0,
      },
      porIdade,
    };
  }, [ficha, m]);

  if (!m || !grafico) return null;
  return (
    <section>
      <SecaoTitulo
        subtitulo={`${grafico.porIdade ? tr("Pela idade em cada avaliação") : tr("Pela data (sem data de nascimento)")}${m.maior_melhor === false ? " · " + tr("eixo invertido: mais acima = mais rápido") : ""}${Object.keys(ficha.bandas).includes(m.chave) ? " · " + tr("banda = metade central da academia na mesma idade") : ""}`}
        acoes={
          <select value={m.chave} onChange={(e) => setChave(e.target.value)} style={campo}>
            {disponiveis.map((x) => <option key={x.chave} value={x.chave}>{tr(x.label)}</option>)}
          </select>
        }
      >
        {tr("Evolução")}</SecaoTitulo>
      <Cartao>
        <PlotlyChart data={grafico.data as never} layout={grafico.layout as never} altura={300} titulo={tr(m.label)} />
      </Cartao>
    </section>
  );
}

// ── Carga de jogo por época ──────────────────────────────────────────────────
function CargaJogo({ linhas }: { linhas: FichaAtleta["carga_jogo"] }) {
  const tr = useTr();
  const n = (v: number | null, u = "m") => (v == null ? "—" : `${Math.round(v).toLocaleString(tr.loc)}${u ? ` ${u}` : ""}`);
  return (
    <section>
      <SecaoTitulo subtitulo={tr("Média por 90 minutos dos jogos em que jogou pelo menos 60 minutos, em cada época")}>{tr("Exigência de jogo por época")}</SecaoTitulo>
      {linhas.length === 0 ? (
        <Vazio>{tr("Ainda não há jogos registados com GPS.")}</Vazio>
      ) : (
        <Cartao padding={0}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 620 }}>
              <thead>
                <tr>{["Época", "Jogos", "Minutos", "Distância / 90'", "HSR / 90'", "Sprint / 90'", "Vel. máx"].map((h, i) => <th key={h} style={{ ...th, textAlign: i ? "right" : "left" }}>{tr(h)}</th>)}</tr>
              </thead>
              <tbody>
                {linhas.map((l) => (
                  <tr key={l.epoca} style={{ borderTop: `1px solid ${cores.borda}` }}>
                    <td style={{ ...td, color: cores.textoForte, fontWeight: 600 }}>{l.epoca}{l.escalao && <span style={{ color: cores.textoFraco, fontWeight: 400 }}> · {l.escalao}</span>}</td>
                    <td style={tdNum}>{l.jogos}<span style={sub}> ({l.jogos_completos} ≥ 60')</span></td>
                    <td style={tdNum}>{l.minutos != null ? l.minutos.toLocaleString(tr.loc) : "—"}</td>
                    <td style={tdNum}>{n(l.distancia_90)}</td>
                    <td style={tdNum}>{n(l.hsr_90)}</td>
                    <td style={tdNum}>{n(l.sprint_90)}</td>
                    <td style={tdNum}>{l.vmax != null ? tr("{0} km/h", [l.vmax.toLocaleString(tr.loc)]) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Cartao>
      )}
    </section>
  );
}

// ── Registar e gerir avaliações ──────────────────────────────────────────────
function RegistarAvaliacao({ ficha, registar, apagar }: { ficha: FichaAtleta; registar: Acoes["registarAvaliacao"]; apagar: Acoes["apagarAvaliacao"] }) {
  const tr = useTr();
  const ultimoTeam = ficha.percurso[ficha.percurso.length - 1]?.team_id ?? null;
  const [dia, setDia] = useState(new Date().toISOString().slice(0, 10));
  const [teamId, setTeamId] = useState<string | null>(ultimoTeam);
  const [valores, setValores] = useState<Record<string, string>>({});
  const [notas, setNotas] = useState("");
  const [estado, setEstado] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);
  const grupos = [...new Set(ficha.catalogo.map((m) => m.grupo))];
  const registos = ficha.catalogo.flatMap((m) => (ficha.series[m.chave] ?? []).map((p) => ({ ...p, m })))
    .sort((x, y) => y.data.localeCompare(x.data));

  return (
    <section>
      <SecaoTitulo subtitulo={tr("Preenche só o que mediste. Os testes neuromusculares importados com o GPS (CMJ, RSI, potência) já entram sozinhos.")}>
        {tr("Registar avaliação")}</SecaoTitulo>
      <Cartao>
        <div style={{ display: "flex", gap: espaco.md, flexWrap: "wrap", marginBottom: espaco.lg }}>
          <Campo rotulo={tr("Data")}><input type="date" value={dia} onChange={(e) => setDia(e.target.value)} style={campo} /></Campo>
          <Campo rotulo={tr("Equipa na altura")}>
            <select value={teamId ?? ""} onChange={(e) => setTeamId(e.target.value || null)} style={campo}>
              <option value="">—</option>
              {ficha.equipas.map((t) => <option key={t.team_id} value={t.team_id}>{t.rotulo}</option>)}
            </select>
          </Campo>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: espaco.lg }}>
          {grupos.map((g) => (
            <div key={g}>
              <div style={{ fontSize: "0.68rem", color: cores.textoFraco, letterSpacing: "0.04em", textTransform: "uppercase", marginBottom: 6 }}>{tr(g)}</div>
              {ficha.catalogo.filter((m) => m.grupo === g).map((m) => (
                <label key={m.chave} style={{ display: "grid", gridTemplateColumns: "1fr 92px", alignItems: "center", gap: 8, marginBottom: 6, fontSize: "0.82rem", color: cores.texto }}>
                  <span>{tr(m.label)}{m.unidade && <span style={{ color: cores.textoFraco }}> ({m.unidade})</span>}</span>
                  <input inputMode="decimal" placeholder={m.chave === "corrida_1km_s" ? tr("m:ss") : undefined} value={valores[m.chave] ?? ""} onChange={(e) => setValores({ ...valores, [m.chave]: e.target.value.replace(",", ".") })} style={{ ...campo, width: "100%", textAlign: "right" }} />
                </label>
              ))}
            </div>
          ))}
        </div>
        <div style={{ display: "flex", gap: espaco.md, alignItems: "center", flexWrap: "wrap", marginTop: espaco.md }}>
          <input placeholder={tr("Notas (opcional)")} value={notas} onChange={(e) => setNotas(e.target.value)} style={{ ...campo, flex: "1 1 240px" }} />
          <button style={estiloBotao.primario} onClick={async () => {
            setEstado(null);
            try {
              // "3:45" → 225 s
              const convertidos = Object.fromEntries(Object.entries(valores).map(([k, v]) => {
                const mm = /^\s*(\d+):(\d{1,2}(?:\.\d+)?)\s*$/.exec(v);
                return [k, mm ? String(Number(mm[1]) * 60 + Number(mm[2])) : v];
              }));
              await registar({ data: dia, team_id: teamId, valores: convertidos, notas });
              setValores({});
              setNotas("");
              setEstado({ tipo: "ok", texto: tr("Avaliação registada.") });
            } catch (e) {
              setEstado({ tipo: "erro", texto: e instanceof Error ? e.message : tr("Erro.") });
            }
          }}>{tr("Guardar avaliação")}</button>
          {estado && <span style={{ fontSize: "0.82rem", color: estado.tipo === "ok" ? cores.sucesso : cores.perigo }}>{estado.texto}</span>}
        </div>
      </Cartao>

      {registos.length > 0 && (
        <details style={{ marginTop: espaco.md }}>
          <summary style={{ cursor: "pointer", fontSize: "0.82rem", color: cores.textoSuave }}>{tr("Histórico de avaliações (")}{registos.length})</summary>
          <Cartao padding={0} style={{ marginTop: espaco.sm }}>
            {registos.map((r, i) => (
              <div key={r.id} style={{ display: "grid", gridTemplateColumns: "100px minmax(0,1fr) auto auto", gap: espaco.md, alignItems: "center", padding: `7px ${espaco.lg}px`, borderTop: i ? `1px solid ${cores.borda}` : "none", fontSize: "0.82rem" }}>
                <span style={{ color: cores.textoSuave, fontVariantNumeric: "tabular-nums" }}>{new Date(`${r.data}T00:00:00`).toLocaleDateString(tr.loc)}</span>
                <span style={{ color: cores.texto }}>{r.m.label}</span>
                <span style={{ color: cores.textoForte, fontVariantNumeric: "tabular-nums" }}>{fmt(r.valor, r.m, tr.loc)}</span>
                {r.origem === "ficha"
                  ? <button style={{ ...estiloBotao.ligacao, color: cores.perigo }} onClick={() => { if (confirm(tr("Apagar esta avaliação?"))) apagar(r.id); }}>{tr("apagar")}</button>
                  : <span style={{ fontSize: "0.72rem", color: cores.textoFraco }}>{tr("importado")}</span>}
              </div>
            ))}
          </Cartao>
        </details>
      )}
    </section>
  );
}

function Campo({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: "0.72rem", color: cores.textoSuave, fontWeight: 500 }}>
      {rotulo}
      {children}
    </label>
  );
}

const campo: React.CSSProperties = { background: cores.bgCartao, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: cores.textoForte, fontSize: "0.84rem", padding: "6px 8px", height: 34 };
const th: React.CSSProperties = { padding: `9px ${espaco.lg}px`, fontSize: "0.68rem", fontWeight: 500, color: cores.textoFraco, letterSpacing: "0.03em", textAlign: "right" };
const td: React.CSSProperties = { padding: `8px ${espaco.lg}px`, fontSize: "0.84rem", color: cores.texto };
const tdNum: React.CSSProperties = { ...td, textAlign: "right", fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" };
const sub: React.CSSProperties = { fontSize: "0.7rem", color: cores.textoFraco, fontWeight: 400 };


// ── Proteção de dados (RGPD) ─────────────────────────────────────────────────
function ProtecaoDados({ ficha }: { ficha: FichaAtleta }) {
  const tr = useTr();
  const a = ficha.atleta;
  const c = a.consentimento ?? { data: null, por: null, notas: null };
  const [form, setForm] = useState({ data: c.data ?? "", por: c.por ?? ((a.idade ?? 0) < 18 ? "encarregado" : "atleta"), notas: c.notas ?? "" });
  const [msg, setMsg] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);

  async function exportar() {
    setMsg(null);
    try {
      const { createClient } = await import("@/lib/supabase/client");
      const { data: { session } } = await createClient().auth.getSession();
      const r = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/academia/atletas/${a.atleta_id}/exportar`, { headers: { Authorization: `Bearer ${session?.access_token}`, "X-Lingua": linguaDoCookie() } });
      if (!r.ok) throw new Error((await r.json().catch(() => null))?.detail ?? tr("Não foi possível exportar."));
      const url = URL.createObjectURL(await r.blob());
      const l = document.createElement("a");
      l.href = url;
      l.download = `dados_${a.nome.replace(/\s+/g, "_")}.json`;
      l.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setMsg({ tipo: "erro", texto: e instanceof Error ? e.message : tr("Erro.") });
    }
  }

  return (
    <section>
      <SecaoTitulo subtitulo={tr("Atletas menores: o consentimento é dado pelo encarregado de educação. A família pode pedir os dados ou o seu apagamento.")}>
        {tr("Proteção de dados")}</SecaoTitulo>
      <Cartao>
        <div style={{ display: "flex", gap: espaco.md, flexWrap: "wrap", alignItems: "flex-end" }}>
          <Campo rotulo={tr("Consentimento dado em")}><input type="date" value={form.data} max={new Date().toISOString().slice(0, 10)} onChange={(e) => setForm({ ...form, data: e.target.value })} style={campo} /></Campo>
          <Campo rotulo={tr("Dado por")}>
            <select value={form.por} onChange={(e) => setForm({ ...form, por: e.target.value as "atleta" | "encarregado" })} style={campo}>
              <option value="encarregado">{tr("Encarregado de educação")}</option><option value="atleta">{tr("Atleta (maior de idade)")}</option>
            </select>
          </Campo>
          <Campo rotulo={tr("Notas (opcional)")}><input value={form.notas} placeholder={tr("ex.: formulário assinado, arquivado no clube")} onChange={(e) => setForm({ ...form, notas: e.target.value })} style={{ ...campo, width: 280 }} /></Campo>
          <button style={estiloBotao.primario} onClick={async () => {
            setMsg(null);
            try {
              await pedidoApi(`/api/academia/atletas/${a.atleta_id}/consentimento`, "PUT", { data: form.data || null, por: form.por, notas: form.notas });
              setMsg({ tipo: "ok", texto: form.data ? tr("Consentimento registado.") : tr("Consentimento removido.") });
            } catch (e) {
              setMsg({ tipo: "erro", texto: e instanceof Error ? e.message : tr("Erro.") });
            }
          }}>{tr("Guardar")}</button>
        </div>
        <div style={{ display: "flex", gap: espaco.md, flexWrap: "wrap", alignItems: "center", marginTop: espaco.lg, paddingTop: espaco.md, borderTop: `1px solid ${cores.borda}` }}>
          <button style={estiloBotao.secundario} onClick={exportar}>{tr("Exportar todos os dados (JSON)")}</button>
          <button style={{ ...estiloBotao.ligacao, color: cores.perigo }} onClick={async () => {
            const escrito = prompt(tr("Apagar TODOS os dados de {0} (sessões, testes, lesões, jogos, ficha)? Não se pode desfazer.\n\nEscreve o nome do atleta para confirmar:", [a.nome]));
            if (escrito === null) return;
            if (escrito.trim().toLowerCase() !== a.nome.trim().toLowerCase()) { setMsg({ tipo: "erro", texto: tr("O nome não corresponde — nada foi apagado.") }); return; }
            try {
              await pedidoApi(`/api/academia/atletas/${a.atleta_id}?tudo=true`, "DELETE");
              window.location.href = "/academia";
            } catch (e) {
              setMsg({ tipo: "erro", texto: e instanceof Error ? e.message : tr("Erro.") });
            }
          }}>{tr("Apagar todos os dados (direito ao apagamento)")}</button>
          {msg && <span role="status" style={{ fontSize: "0.82rem", color: msg.tipo === "ok" ? cores.sucesso : cores.perigo }}>{msg.texto}</span>}
        </div>
      </Cartao>
    </section>
  );
}
