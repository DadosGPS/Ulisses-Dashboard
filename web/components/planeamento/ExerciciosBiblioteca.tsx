"use client";

import { useEffect, useMemo, useState } from "react";
import { pedidoApi } from "@/lib/api-cliente";
import { cores, espaco, raio } from "@/lib/theme";
import { Cartao, Etiqueta, SecaoTitulo, Vazio, estiloBotao } from "@/components/ui/base";
import { useTr } from "@/lib/i18n/cliente";

type Metrica = { chave: string; label: string; unidade: string };
type Exercicio = {
  id: string | null; nome: string; categoria: string | null; descricao: string | null; formato: string | null; espaco: string | null;
  duracao_min: number | null; manual: Record<string, number>;
  gps: { n: number; ultima?: string | null; duracao_min?: number; por_min?: Record<string, number>; pse?: number | null };
  por_min: Record<string, number>; fonte: "gps" | "manual" | null; guardado: boolean;
};
interface Lista { disponivel: boolean; motivo?: string; categorias: string[]; metricas: Metrica[]; exercicios: Exercicio[] }
type Form = { id: string | null; nome: string; categoria: string; descricao: string; formato: string; espaco: string; duracao_min: string; manual: Record<string, string> };

const CURTO: Record<string, string> = { distancia: "Dist", acc: "Acc", dcc: "Dcc" };
const COR_CAT: Record<string, string> = {
  Aquecimento: "#64748b", Rondo: "#0ea5e9", Posse: "#2563eb", "Jogo reduzido": "#d97706", "Jogo condicionado": "#ea580c",
  "Finalização": "#dc2626", "Transições": "#db2777", "Bolas paradas": "#7c3aed", "Físico / velocidade": "#16a34a",
  "Prevenção": "#0d9488", "Recuperação": "#14b8a6", Outro: "#78716c",
};

/** Biblioteca de exercícios: carga típica por minuto (do GPS ou escrita à mão). */
export function ExerciciosBiblioteca({ teamId }: { teamId: string | null }) {
  const tr = useTr();
  const [dados, setDados] = useState<Lista | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [busca, setBusca] = useState("");
  const [cat, setCat] = useState("");
  const [soEquipa, setSoEquipa] = useState(false);
  const [form, setForm] = useState<Form | null>(null);
  const [aviso, setAviso] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);

  async function carregar() {
    try {
      setDados(await pedidoApi<Lista>(`/api/academia/exercicios${soEquipa && teamId ? `?team_id=${teamId}` : ""}`));
    } catch (e) {
      setErro(e instanceof Error ? e.message : tr("Erro."));
    }
  }
  useEffect(() => { carregar(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [soEquipa, teamId]);

  const lista = useMemo(() => (dados?.exercicios ?? []).filter((e) =>
    (!busca || e.nome.toLowerCase().includes(busca.toLowerCase())) && (!cat || e.categoria === cat)), [dados, busca, cat]);

  if (erro) return <Vazio>{erro}</Vazio>;
  if (!dados) return <p style={{ color: cores.textoSuave, fontSize: "0.88rem" }}>{tr("A carregar…")}</p>;
  if (!dados.disponivel) return <Vazio>{dados.motivo}</Vazio>;

  const abrir = (e?: Exercicio) => {
    setAviso(null);
    setForm({
      id: e?.id ?? null, nome: e?.nome ?? "", categoria: e?.categoria ?? "", descricao: e?.descricao ?? "", formato: e?.formato ?? "",
      espaco: e?.espaco ?? "", duracao_min: String(e?.duracao_min ?? (e?.gps.duracao_min ? Math.round(e.gps.duracao_min) : "") ?? ""),
      manual: Object.fromEntries(dados.metricas.map((m) => [m.chave, e?.manual?.[m.chave] != null ? String(e.manual[m.chave]) : ""])),
    });
  };

  async function guardar() {
    if (!form) return;
    setAviso(null);
    const corpo = { ...form, duracao_min: form.duracao_min ? Number(form.duracao_min) : null,
      manual: Object.fromEntries(Object.entries(form.manual).filter(([, v]) => v.trim() !== "").map(([k, v]) => [k, Number(v.replace(",", "."))])) };
    try {
      if (form.id) await pedidoApi(`/api/academia/exercicios/${form.id}`, "PUT", corpo);
      else await pedidoApi("/api/academia/exercicios", "POST", corpo);
      setForm(null);
      setAviso({ tipo: "ok", texto: tr("Exercício guardado.") });
      await carregar();
    } catch (e) {
      setAviso({ tipo: "erro", texto: e instanceof Error ? e.message : tr("Erro.") });
    }
  }

  async function apagar(e: Exercicio) {
    if (!e.id || !window.confirm(tr("Tirar «{0}» da biblioteca? Os registos do GPS ficam.", [e.nome]))) return;
    try {
      await pedidoApi(`/api/academia/exercicios/${e.id}`, "DELETE");
      await carregar();
    } catch (err) {
      setAviso({ tipo: "erro", texto: err instanceof Error ? err.message : tr("Erro.") });
    }
  }

  const n = (v: number | undefined, casas = 1) => (v == null ? "—" : v.toLocaleString(tr.loc, { maximumFractionDigits: casas }));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: espaco.lg }}>
      <div style={{ display: "flex", gap: espaco.sm, flexWrap: "wrap", alignItems: "center" }}>
        <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder={tr("Procurar exercício")} aria-label={tr("Procurar exercício")} style={{ ...campo, width: 220 }} />
        <select value={cat} onChange={(e) => setCat(e.target.value)} style={campo} aria-label={tr("Categoria")}>
          <option value="">{tr("Todas as categorias")}</option>
          {dados.categorias.map((c) => <option key={c} value={c}>{tr(c)}</option>)}
        </select>
        {teamId && (
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.8rem", color: cores.texto }}>
            <input type="checkbox" checked={soEquipa} onChange={(e) => setSoEquipa(e.target.checked)} />
            {tr("Carga só desta equipa")}</label>
        )}
        <button style={{ ...estiloBotao.primario, marginLeft: "auto" }} onClick={() => abrir()}>{tr("+ Novo exercício")}</button>
      </div>

      {aviso && <div role="status" style={{ fontSize: "0.82rem", color: aviso.tipo === "ok" ? cores.sucesso : cores.perigo }}>{aviso.texto}</div>}

      {form && (
        <Cartao>
          <SecaoTitulo ajuda={tr("Os valores por minuto só são usados enquanto o exercício não tiver registos no GPS com o mesmo nome. Com GPS, a previsão usa a mediana dos registos.")}>
            {form.id ? tr("Editar exercício") : tr("Novo exercício")}</SecaoTitulo>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: espaco.md }}>
            <Campo rotulo={tr("Nome")}><input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} placeholder={tr("ex.: Jogo reduzido 4v4")} style={campo} /></Campo>
            <Campo rotulo={tr("Categoria")}>
              <select value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })} style={campo}>
                <option value="">—</option>
                {dados.categorias.map((c) => <option key={c} value={c}>{tr(c)}</option>)}
              </select>
            </Campo>
            <Campo rotulo={tr("Formato")}><input value={form.formato} onChange={(e) => setForm({ ...form, formato: e.target.value })} placeholder={tr("ex.: 4v4+2")} style={campo} /></Campo>
            <Campo rotulo={tr("Espaço")}><input value={form.espaco} onChange={(e) => setForm({ ...form, espaco: e.target.value })} placeholder={tr("ex.: 30×20 m")} style={campo} /></Campo>
            <Campo rotulo={tr("Duração típica (min)")}><input inputMode="numeric" value={form.duracao_min} onChange={(e) => setForm({ ...form, duracao_min: e.target.value.replace(/\D/g, "") })} style={campo} /></Campo>
          </div>
          <Campo rotulo={tr("Descrição / regras")}>
            <textarea value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })} rows={2} style={{ ...campo, height: "auto", resize: "vertical", fontFamily: "inherit" }} />
          </Campo>
          <div style={{ fontSize: "0.74rem", color: cores.textoSuave, fontWeight: 600, margin: `${espaco.md}px 0 6px` }}>{tr("Carga por minuto, por jogador (sem GPS)")}</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: espaco.sm }}>
            {dados.metricas.map((m) => (
              <Campo key={m.chave} rotulo={`${tr(m.label)} (${m.unidade}/min)`}>
                <input inputMode="decimal" value={form.manual[m.chave] ?? ""} onChange={(e) => setForm({ ...form, manual: { ...form.manual, [m.chave]: e.target.value } })} style={{ ...campo, textAlign: "right" }} />
              </Campo>
            ))}
          </div>
          <div style={{ display: "flex", gap: espaco.sm, marginTop: espaco.md }}>
            <button style={estiloBotao.primario} disabled={!form.nome.trim()} onClick={guardar}>{tr("Guardar")}</button>
            <button style={estiloBotao.secundario} onClick={() => setForm(null)}>{tr("Cancelar")}</button>
          </div>
        </Cartao>
      )}

      <section>
        <SecaoTitulo
          subtitulo={tr("{0} exercício(s) · {1} com carga do GPS", [lista.length, lista.filter((e) => e.fonte === "gps").length])}
          ajuda={tr("Carga típica por minuto e por jogador: a mediana de todas as vezes em que o exercício foi registado no GPS (folha de exercícios do ficheiro importado), ligado pelo nome. Os exercícios que só existem no GPS aparecem a cinzento — guarda-os para lhes juntar categoria, formato e regras. No calendário, ao planear um treino, juntas exercícios e minutos e a app prevê a carga da sessão.")}
        >{tr("Biblioteca de exercícios")}</SecaoTitulo>
        {lista.length === 0 ? (
          <Vazio>{dados.exercicios.length ? tr("Nenhum exercício corresponde à pesquisa.") : tr("Ainda não há exercícios. Cria o primeiro, ou importa um ficheiro de GPS com a folha de exercícios.")}</Vazio>
        ) : (
          <Cartao padding={0}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem", minWidth: 900 }}>
                <thead>
                  <tr>
                    <th style={th}>{tr("Exercício")}</th>
                    <th style={th}>{tr("Categoria")}</th>
                    <th style={th}>{tr("Formato · espaço")}</th>
                    <th style={{ ...th, textAlign: "right" }}>{tr("Duração")}</th>
                    {dados.metricas.map((m) => <th key={m.chave} style={{ ...th, textAlign: "right" }} title={tr(m.label)}>{tr(CURTO[m.chave] ?? m.label)}<span style={{ fontWeight: 400 }}> /min</span></th>)}
                    <th style={{ ...th, textAlign: "right" }}>{tr("PSE")}</th>
                    <th style={th}>{tr("Origem")}</th>
                    <th style={th} />
                  </tr>
                </thead>
                <tbody>
                  {lista.map((e) => (
                    <tr key={e.id ?? `gps:${e.nome}`} style={{ borderTop: `1px solid ${cores.borda}`, color: e.guardado ? cores.texto : cores.textoSuave }}>
                      <td style={{ ...td, fontWeight: 600, whiteSpace: "nowrap", color: e.guardado ? cores.textoForte : cores.textoSuave }} title={e.descricao ?? undefined}>{e.nome}</td>
                      <td style={td}>{e.categoria ? <Etiqueta cor={COR_CAT[e.categoria] ?? cores.textoSuave}>{tr(e.categoria)}</Etiqueta> : "—"}</td>
                      <td style={{ ...td, whiteSpace: "nowrap" }}>{[e.formato, e.espaco].filter(Boolean).join(" · ") || "—"}</td>
                      <td style={tdN}>{e.duracao_min ?? (e.gps.duracao_min ? Math.round(e.gps.duracao_min) : null) ?? "—"}{(e.duracao_min || e.gps.duracao_min) ? " min" : ""}</td>
                      {dados.metricas.map((m) => <td key={m.chave} style={tdN}>{n(e.por_min[m.chave], m.chave === "distancia" ? 0 : 1)}</td>)}
                      <td style={tdN}>{n(e.gps.pse ?? undefined)}</td>
                      <td style={{ ...td, fontSize: "0.72rem", whiteSpace: "nowrap" }}>
                        {e.fonte === "gps" ? tr("GPS · {0} reg.", [e.gps.n]) : e.fonte === "manual" ? tr("manual") : tr("sem carga")}
                      </td>
                      <td style={{ ...td, textAlign: "right", whiteSpace: "nowrap" }}>
                        <button style={{ ...estiloBotao.ligacao, fontSize: "0.76rem" }} onClick={() => abrir(e)}>{e.guardado ? tr("Editar") : tr("Guardar na biblioteca")}</button>
                        {e.guardado && <button style={{ ...estiloBotao.ligacao, fontSize: "0.76rem", color: cores.perigo, marginLeft: 10 }} onClick={() => apagar(e)}>{tr("Tirar")}</button>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Cartao>
        )}
      </section>
    </div>
  );
}

function Campo({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: "0.74rem", color: cores.textoSuave, fontWeight: 600 }}>
      {rotulo}{children}
    </label>
  );
}

const campo: React.CSSProperties = { background: cores.bgCartao, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: cores.textoForte, fontSize: "0.84rem", padding: "6px 9px", height: 34, boxSizing: "border-box" };
const th: React.CSSProperties = { padding: `9px ${espaco.sm}px`, fontSize: "0.66rem", fontWeight: 600, color: cores.textoSuave, textAlign: "left", whiteSpace: "nowrap" };
const td: React.CSSProperties = { padding: `8px ${espaco.sm}px` };
const tdN: React.CSSProperties = { ...td, textAlign: "right", fontVariantNumeric: "tabular-nums" };
