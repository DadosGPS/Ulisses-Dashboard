"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { definirEquipaAtiva } from "@/lib/equipa-ativa";
import { useStore } from "@/lib/store";
import { cores, espaco, raio } from "@/lib/theme";
import { Cartao, SecaoTitulo, Vazio, estiloBotao } from "@/components/ui/base";
import { useTr, linguaDoCookie } from "@/lib/i18n/cliente";

interface Equipa {
  team_id: string;
  nome: string;
  rotulo: string;
  academia_id: string | null;
  escalao: string | null;
  epoca: string | null;
  n_jogadores: number | null;
  ultima_sessao: string | null;
}

interface Estrutura {
  disponivel: boolean;
  motivo?: string;
  epoca_atual: string;
  escaloes: string[];
  academias: { academia_id: string; nome: string; papel: "head" | "staff"; equipas: Equipa[] }[];
  equipas: Equipa[];
}

function seguinte(epoca: string) {
  const m = epoca.match(/^(\d{4})\/\d{2}$/);
  if (!m) return epoca;
  const a = Number(m[1]) + 1;
  return `${a}/${String(a + 1).slice(-2)}`;
}

export function GestaoAcademia() {
  const tr = useTr();
  const teamId = useStore((s) => s.user.teamId);
  const setUser = useStore((s) => s.setUser);
  const [dados, setDados] = useState<Estrutura | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [aGravar, setAGravar] = useState(false);
  const [edicao, setEdicao] = useState<Record<string, { escalao: string; epoca: string }>>({});
  const [nova, setNova] = useState({ escalao: "Sub-15", epoca: "", copiar_de: "" });
  const api = process.env.NEXT_PUBLIC_API_URL;

  async function pedido(url: string, metodo = "GET", corpo?: unknown) {
    const { data: { session } } = await createClient().auth.getSession();
    if (!session) throw new Error(tr("Sessão expirada. Volta a entrar."));
    const r = await fetch(`${api}${url}`, {
      method: metodo,
      headers: { Authorization: `Bearer ${session.access_token}`, "X-Lingua": linguaDoCookie(), "Content-Type": "application/json" },
      body: corpo ? JSON.stringify(corpo) : undefined,
    });
    const j = await r.json().catch(() => null);
    if (!r.ok) throw new Error(j?.detail ?? tr("Não foi possível concluir."));
    return j;
  }

  async function carregar() {
    try {
      const d: Estrutura = await pedido("/api/academia");
      setDados(d);
      setNova((n) => ({ ...n, epoca: n.epoca || d.epoca_atual }));
    } catch (e) {
      setErro(e instanceof Error ? e.message : tr("Erro inesperado."));
    }
  }

  useEffect(() => {
    carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function executar(acao: () => Promise<string>) {
    setErro(null);
    setOk(null);
    setAGravar(true);
    try {
      setOk(await acao());
      await carregar();
    } catch (e) {
      setErro(e instanceof Error ? e.message : tr("Erro inesperado."));
    } finally {
      setAGravar(false);
    }
  }

  function ativar(id: string) {
    definirEquipaAtiva(id);
    setUser({ teamId: id });
    window.location.href = "/dashboard";
  }

  if (!dados) return <p style={{ color: cores.textoSuave, fontSize: "0.88rem" }}>{erro ?? tr("A carregar…")}</p>;
  if (!dados.disponivel) return <Vazio>{dados.motivo}</Vazio>;

  const academia = dados.academias[0];
  if (!academia) return <Vazio>{tr("Ainda não pertences a nenhuma academia.")}</Vazio>;
  const equipas = academia.equipas;
  const semArrumacao = equipas.filter((e) => !e.escalao || !e.epoca);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: espaco.xl }}>
      {erro && <Aviso cor={cores.perigo}>{erro}</Aviso>}
      {ok && <Aviso cor={cores.sucesso}>{ok}</Aviso>}

      {semArrumacao.length > 0 && (
        <section>
          <SecaoTitulo subtitulo={tr("Indica o escalão e a época destas equipas — passam a aparecer arrumadas e prontas para a ficha de cada atleta.")}>
            {tr("Equipas por arrumar")}</SecaoTitulo>
          <Cartao padding={0}>
            {semArrumacao.map((e, i) => {
              const ed = edicao[e.team_id] ?? { escalao: e.escalao ?? "Sub-15", epoca: e.epoca ?? dados.epoca_atual };
              return (
                <div key={e.team_id} style={{ display: "flex", alignItems: "center", gap: espaco.md, flexWrap: "wrap", padding: `${espaco.md}px ${espaco.lg}px`, borderTop: i ? `1px solid ${cores.borda}` : "none" }}>
                  <span style={{ flex: "1 1 180px", fontWeight: 600, color: cores.textoForte, fontSize: "0.88rem" }}>{e.nome}</span>
                  <SelectEscalao valor={ed.escalao} escaloes={dados.escaloes} onChange={(v) => setEdicao({ ...edicao, [e.team_id]: { ...ed, escalao: v } })} />
                  <input value={ed.epoca} onChange={(ev) => setEdicao({ ...edicao, [e.team_id]: { ...ed, epoca: ev.target.value } })} placeholder="2026/27" style={{ ...campo, width: 96 }} />
                  <button style={estiloBotao.primario} disabled={aGravar}
                    onClick={() => executar(async () => { await pedido(`/api/academia/equipas/${e.team_id}`, "PATCH", ed); return tr("{0} passou a {1} · {2}.", [e.nome, ed.escalao, ed.epoca]); })}>
                    {tr("Guardar")}</button>
                </div>
              );
            })}
          </Cartao>
        </section>
      )}

      <section>
        <SecaoTitulo subtitulo={tr("{0} · {1} equipa(s)", [academia.nome, equipas.length])}>{tr("Equipas da academia")}</SecaoTitulo>
        <Cartao padding={0}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>{["Equipa", "Jogadores", "Última sessão", ""].map((h, i) => <th key={i} style={{ ...th, textAlign: i === 1 ? "right" : "left" }}>{tr(h)}</th>)}</tr>
            </thead>
            <tbody>
              {equipas.map((e) => {
                const ativa = e.team_id === teamId;
                return (
                  <tr key={e.team_id} style={{ borderTop: `1px solid ${cores.borda}` }}>
                    <td style={{ ...td, fontWeight: 600, color: cores.textoForte }}>{e.rotulo}</td>
                    <td style={{ ...td, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{e.n_jogadores ?? "—"}</td>
                    <td style={{ ...td, color: cores.textoSuave }}>{e.ultima_sessao ? new Date(`${e.ultima_sessao}T00:00:00`).toLocaleDateString(tr.loc) : tr("sem sessões")}</td>
                    <td style={{ ...td, textAlign: "right" }}>
                      {ativa ? <span style={{ fontSize: "0.76rem", color: cores.textoSuave }}>{tr("equipa ativa")}</span>
                        : <button style={estiloBotao.ligacao} onClick={() => ativar(e.team_id)}>{tr("Abrir")}</button>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Cartao>
      </section>

      <section>
        <SecaoTitulo subtitulo={tr("Cria a equipa de um escalão numa época. Ao copiar o plantel, os jogadores mantêm a sua ficha de atleta — o histórico de épocas anteriores fica ligado.")}>
          {tr("Nova equipa / nova época")}</SecaoTitulo>
        <Cartao>
          <div style={{ display: "flex", gap: espaco.md, flexWrap: "wrap", alignItems: "flex-end" }}>
            <Rotulo texto={tr("Escalão")}><SelectEscalao valor={nova.escalao} escaloes={dados.escaloes} onChange={(v) => setNova({ ...nova, escalao: v })} /></Rotulo>
            <Rotulo texto={tr("Época")}>
              <div style={{ display: "flex", gap: 6 }}>
                <input value={nova.epoca} onChange={(e) => setNova({ ...nova, epoca: e.target.value })} placeholder="2026/27" style={{ ...campo, width: 96 }} />
                <button style={estiloBotao.secundario} onClick={() => setNova({ ...nova, epoca: seguinte(nova.epoca || dados.epoca_atual) })} title={tr("Época seguinte")}>+1</button>
              </div>
            </Rotulo>
            <Rotulo texto={tr("Copiar plantel de")}>
              <select value={nova.copiar_de} onChange={(e) => setNova({ ...nova, copiar_de: e.target.value })} style={{ ...campo, minWidth: 200 }}>
                <option value="">{tr("Não copiar (plantel vazio)")}</option>
                {equipas.map((e) => <option key={e.team_id} value={e.team_id}>{e.rotulo}</option>)}
              </select>
            </Rotulo>
            <button style={estiloBotao.primario} disabled={aGravar || !nova.escalao || !nova.epoca}
              onClick={() => executar(async () => {
                const r = await pedido(`/api/academia/${academia.academia_id}/equipas`, "POST", { ...nova, copiar_de: nova.copiar_de || null });
                return tr("Criada a equipa {0}{1}. Abre-a na lista acima ou no seletor da barra lateral.", [r.rotulo, r.jogadores_copiados ? " " + tr("com {0} jogadores", [r.jogadores_copiados]) : ""]);
              })}>
              {aGravar ? tr("A criar…") : tr("Criar equipa")}
            </button>
          </div>
        </Cartao>
      </section>
    </div>
  );
}

function SelectEscalao({ valor, escaloes, onChange }: { valor: string; escaloes: string[]; onChange: (v: string) => void }) {
  return (
    <select value={valor} onChange={(e) => onChange(e.target.value)} style={campo}>
      {[...new Set([...escaloes, valor])].map((e) => <option key={e} value={e}>{e}</option>)}
    </select>
  );
}

function Rotulo({ texto, children }: { texto: string; children: React.ReactNode }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: "0.72rem", color: cores.textoSuave, fontWeight: 500 }}>
      {texto}
      {children}
    </label>
  );
}

function Aviso({ cor, children }: { cor: string; children: React.ReactNode }) {
  return (
    <div style={{ background: `color-mix(in srgb, ${cor} 10%, transparent)`, border: `1px solid color-mix(in srgb, ${cor} 30%, transparent)`, borderRadius: raio.md, padding: `${espaco.sm}px ${espaco.md}px`, fontSize: "0.84rem", color: cores.texto }}>
      {children}
    </div>
  );
}

const campo: React.CSSProperties = { background: cores.bgCartao, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: cores.textoForte, fontSize: "0.84rem", padding: "6px 8px", height: 34 };
const th: React.CSSProperties = { padding: `9px ${espaco.lg}px`, fontSize: "0.68rem", fontWeight: 500, color: cores.textoFraco, letterSpacing: "0.03em" };
const td: React.CSSProperties = { padding: `10px ${espaco.lg}px`, fontSize: "0.85rem", color: cores.texto };
