"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { pedidoApi } from "@/lib/api-cliente";
import { cores, espaco, raio } from "@/lib/theme";
import { Cartao, SecaoTitulo, Vazio, estiloBotao } from "@/components/ui/base";
import { NomeJogador } from "@/components/ui/NomeJogador";
import type { AtletaLista } from "./tipos";
import { useTr } from "@/lib/i18n/cliente";

interface EquipaAcad {
  team_id: string;
  rotulo: string;
  escalao: string | null;
  epoca: string | null;
}

interface Estrutura {
  disponivel: boolean;
  epoca_atual: string;
  academias: { academia_id: string; nome: string; papel: "head" | "staff"; equipas: EquipaAcad[] }[];
}

/** Atletas da academia — adicionados um a um pelo PF, numa ou em várias
 * equipas. Um jogador em duas equipas tem os dados visíveis em ambas. */
export function ListaAtletas() {
  const tr = useTr();
  const [dados, setDados] = useState<{ disponivel: boolean; motivo?: string; atletas: AtletaLista[] } | null>(null);
  const [estrutura, setEstrutura] = useState<Estrutura | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);
  const [busca, setBusca] = useState("");
  const [escalao, setEscalao] = useState("");
  const [pendentes, setPendentes] = useState<"" | "consentimento" | "nascimento">("");
  const [aAdicionar, setAAdicionar] = useState(false);

  async function carregar() {
    try {
      const [a, e] = await Promise.all([
        pedidoApi<{ disponivel: boolean; motivo?: string; atletas: AtletaLista[] }>("/api/academia/atletas"),
        pedidoApi<Estrutura>("/api/academia"),
      ]);
      setDados(a);
      setEstrutura(e);
    } catch (e) {
      setErro(e instanceof Error ? e.message : tr("Erro inesperado."));
    }
  }
  useEffect(() => {
    carregar();
  }, []);

  async function executar(acao: () => Promise<unknown>, ok: string) {
    setAviso(null);
    try {
      await acao();
      setAviso({ tipo: "ok", texto: ok });
      await carregar();
      return true;
    } catch (e) {
      setAviso({ tipo: "erro", texto: e instanceof Error ? e.message : tr("Erro inesperado.") });
      return false;
    }
  }

  const academia = estrutura?.academias[0];
  // Equipas onde se pode pôr atletas: as da época atual com escalão (ou, se
  // ainda não houver nenhuma, todas as que têm escalão).
  const equipas = useMemo(() => {
    const comEscalao = (academia?.equipas ?? []).filter((e) => e.escalao);
    const atuais = comEscalao.filter((e) => e.epoca === estrutura?.epoca_atual);
    return atuais.length ? atuais : comEscalao;
  }, [academia, estrutura]);

  const lista = useMemo(() => {
    const q = busca.trim().toLowerCase();
    return (dados?.atletas ?? []).filter((a) =>
      (!q || a.nome.toLowerCase().includes(q)) && (!escalao || a.equipas.some((e) => e.escalao === escalao))
      && (pendentes !== "consentimento" || a.consentimento === false)
      && (pendentes !== "nascimento" || !a.data_nascimento));
  }, [dados, busca, escalao, pendentes]);

  if (erro) return <Vazio>{erro}</Vazio>;
  if (!dados || !estrutura) return <p style={{ color: cores.textoSuave, fontSize: "0.88rem" }}>{tr("A carregar…")}</p>;
  if (!dados.disponivel) return <Vazio>{dados.motivo}</Vazio>;

  const semNascimento = dados.atletas.filter((a) => !a.data_nascimento).length;
  const semConsentimento = dados.atletas.filter((a) => a.consentimento === false).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: espaco.xl }}>
      {aviso && (
        <div style={{ fontSize: "0.84rem", color: aviso.tipo === "ok" ? cores.sucesso : cores.perigo }}>{aviso.texto}</div>
      )}

      {academia && equipas.length === 0 ? (
        <Vazio>
          {tr("Ainda não há equipas de escalão nesta academia. Cria as equipas (Sub-15, Sub-16, Sub-17, Sub-19) em")}{" "}
          <Link href="/configuracoes/academia" style={{ color: cores.textoForte }}>{tr("Definições → Academia")}</Link> {tr("e depois adiciona os jogadores aqui.")}</Vazio>
      ) : academia && (aAdicionar || dados.atletas.length === 0) ? (
        <NovoAtleta equipas={equipas} fechar={dados.atletas.length ? () => setAAdicionar(false) : undefined} adicionar={async (d) => {
          await pedidoApi(`/api/academia/${academia.academia_id}/atletas`, "POST", d);
          await carregar();
        }} />
      ) : null}

      {equipas.length > 0 && dados.atletas.length > 0 && (
        <div style={{ display: "flex", gap: espaco.md, flexWrap: "wrap" }}>
          {equipas.map((e) => {
            const n = dados.atletas.filter((a) => a.equipas.some((x) => x.team_id === e.team_id)).length;
            return (
              <Link key={e.team_id} href={`/academia/equipa/${e.team_id}`} style={{ textDecoration: "none" }}>
                <Cartao padding={espaco.md} style={{ minWidth: 150 }}>
                  <div style={{ fontSize: "0.72rem", color: cores.textoSuave, fontWeight: 600 }}>{e.escalao ?? e.rotulo}</div>
                  <div style={{ fontSize: "1.25rem", fontWeight: 700, color: cores.textoForte, fontVariantNumeric: "tabular-nums" }}>{n}</div>
                  <div style={{ fontSize: "0.7rem", color: cores.acento }}>{tr("ver resultados →")}</div>
                </Cartao>
              </Link>
            );
          })}
        </div>
      )}

      {(semConsentimento > 0 || semNascimento > 0) && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {semConsentimento > 0 && (
            <Pendente cor={cores.atencao} ativo={pendentes === "consentimento"} alternar={() => setPendentes(pendentes === "consentimento" ? "" : "consentimento")}
              texto={tr("{0} jogador(es) sem consentimento de dados registado — regista-o na ficha de cada um.", [semConsentimento])} />
          )}
          {semNascimento > 0 && (
            <Pendente cor={cores.info} ativo={pendentes === "nascimento"} alternar={() => setPendentes(pendentes === "nascimento" ? "" : "nascimento")}
              texto={tr("{0} jogador(es) sem data de nascimento (necessária para idade, maturação e percentis).", [semNascimento])} />
          )}
        </div>
      )}

      <section>
        <SecaoTitulo
          subtitulo={lista.length === dados.atletas.length ? tr("{0} atleta(s) · clica num nome para abrir a ficha", [dados.atletas.length]) : tr("{0} de {1} atleta(s)", [lista.length, dados.atletas.length])}
          acoes={
            <>
              <input placeholder={tr("Procurar atleta")} value={busca} onChange={(e) => setBusca(e.target.value)} style={{ ...campo, width: 200 }} />
              <select value={escalao} onChange={(e) => setEscalao(e.target.value)} style={campo}>
                <option value="">{tr("Todas as equipas")}</option>
                {[...new Set(equipas.map((e) => e.escalao))].map((e) => <option key={e!} value={e!}>{e}</option>)}
              </select>
              {academia && equipas.length > 0 && !aAdicionar && dados.atletas.length > 0 && (
                <button style={estiloBotao.primario} onClick={() => setAAdicionar(true)}>{tr("+ Adicionar jogador")}</button>
              )}
            </>
          }
        >
          {tr("Atletas da academia")}</SecaoTitulo>
        {lista.length === 0 ? (
          <Vazio>{dados.atletas.length ? tr("Nenhum atleta corresponde à pesquisa.") : tr("Ainda não há atletas. Adiciona o primeiro jogador acima.")}</Vazio>
        ) : (
          <Cartao padding={0}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 720 }}>
                <thead>
                  <tr>{["Atleta", "Idade", "Equipas", "Avaliações", "Última avaliação"].map((h, i) => <th key={h} style={{ ...th, textAlign: i === 1 || i === 3 ? "right" : "left" }}>{tr(h)}</th>)}</tr>
                </thead>
                <tbody>
                  {lista.map((a) => (
                    <tr key={a.atleta_id} style={{ borderTop: `1px solid ${cores.borda}` }}>
                      <td style={td}>
                        <Link href={`/academia/atleta/${a.atleta_id}`} style={{ color: cores.textoForte, fontWeight: 600, textDecoration: "none" }}>
                          <NomeJogador nome={a.nome} />
                        </Link>
                        {a.posicao && <span style={{ color: cores.textoFraco }}> · {a.posicao}</span>}
                        {a.consentimento === false && <span title={tr("Sem consentimento de dados registado")} style={{ color: cores.atencao, marginLeft: 6 }}>⚠</span>}
                      </td>
                      <td style={{ ...td, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{a.idade != null ? Math.floor(a.idade) : <span style={{ color: cores.textoFraco }}>—</span>}</td>
                      <td style={td}>
                        <EquipasAtleta
                          atleta={a}
                          equipas={equipas}
                          adicionar={(team_id, rotulo) => executar(
                            () => pedidoApi(`/api/academia/atletas/${a.atleta_id}/equipas`, "POST", { team_id }),
                            tr("{0} também está agora nos {1}. Os dados dele passam a aparecer nas duas equipas.", [a.nome, rotulo]),
                          )}
                          remover={(team_id, rotulo) => {
                            if (!confirm(tr("Tirar {0} do plantel dos {1}? O histórico fica guardado.", [a.nome, rotulo]))) return;
                            executar(() => pedidoApi(`/api/academia/atletas/${a.atleta_id}/equipas/${team_id}`, "DELETE"), tr("{0} saiu dos {1}.", [a.nome, rotulo]));
                          }}
                        />
                      </td>
                      <td style={{ ...td, textAlign: "right" }}>{a.n_avaliacoes}</td>
                      <td style={{ ...td, color: cores.textoSuave }}>{a.ultima_avaliacao ? new Date(`${a.ultima_avaliacao}T00:00:00`).toLocaleDateString(tr.loc) : "—"}</td>
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

function NovoAtleta({ equipas, adicionar, fechar }: {
  equipas: EquipaAcad[];
  fechar?: () => void;
  adicionar: (d: { nome: string; data_nascimento: string; equipas: string[] }) => Promise<void>;
}) {
  const tr = useTr();
  // Com uma só equipa, fica logo escolhida.
  const inicial = equipas.length === 1 ? [equipas[0].team_id] : [];
  const [form, setForm] = useState({ nome: "", data_nascimento: "", equipas: inicial });
  const [aGravar, setAGravar] = useState(false);
  const [msg, setMsg] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);
  const alternar = (id: string) =>
    setForm({ ...form, equipas: form.equipas.includes(id) ? form.equipas.filter((x) => x !== id) : [...form.equipas, id] });

  async function submeter() {
    const falta = [
      form.nome.trim().length < 2 ? tr("o nome") : null,
      !form.data_nascimento ? tr("a data de nascimento") : null,
      form.equipas.length === 0 ? tr("pelo menos uma equipa") : null,
    ].filter(Boolean);
    if (falta.length) {
      setMsg({ tipo: "erro", texto: tr("Falta preencher {0}.", [falta.join(", ")]) });
      return;
    }
    setMsg(null);
    setAGravar(true);
    try {
      await adicionar({ nome: form.nome.trim(), data_nascimento: form.data_nascimento, equipas: form.equipas });
      setMsg({ tipo: "ok", texto: tr("{0} adicionado.", [form.nome.trim()]) });
      setForm({ nome: "", data_nascimento: "", equipas: form.equipas });
    } catch (e) {
      setMsg({ tipo: "erro", texto: e instanceof Error ? e.message : tr("Não foi possível adicionar.") });
    } finally {
      setAGravar(false);
    }
  }

  return (
    <section>
      <SecaoTitulo subtitulo={tr("Nome, data de nascimento e equipa(s). Se treina em mais do que uma equipa, marca todas — os dados que registar numa ficam visíveis na outra.")}
        acoes={fechar && <button type="button" style={estiloBotao.secundario} onClick={fechar}>{tr("Fechar")}</button>}>
        {tr("Adicionar jogador")}</SecaoTitulo>
      <Cartao>
        <form onSubmit={(e) => { e.preventDefault(); submeter(); }}>
          <div style={{ display: "flex", gap: espaco.md, flexWrap: "wrap", alignItems: "flex-end" }}>
            <Rotulo texto={tr("Nome")}><input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} placeholder={tr("Nome e apelido")} style={{ ...campo, width: 240 }} /></Rotulo>
            <Rotulo texto={tr("Data de nascimento")}><input type="date" value={form.data_nascimento} max={new Date().toISOString().slice(0, 10)} onChange={(e) => setForm({ ...form, data_nascimento: e.target.value })} style={campo} /></Rotulo>
          </div>
          <div style={{ marginTop: espaco.md }}>
            <div style={{ fontSize: "0.72rem", color: cores.textoSuave, fontWeight: 500, marginBottom: 6 }}>{tr("Equipa(s) — escolhe uma ou mais")}</div>
            <div style={{ display: "flex", gap: espaco.md, flexWrap: "wrap" }}>
              {equipas.map((e) => (
                <label key={e.team_id} style={{
                  display: "inline-flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: "0.84rem", color: cores.textoForte,
                  border: `1px solid ${form.equipas.includes(e.team_id) ? cores.acento : cores.bordaForte}`, borderRadius: raio.sm, padding: "6px 10px",
                }}>
                  <input type="checkbox" checked={form.equipas.includes(e.team_id)} onChange={() => alternar(e.team_id)} />
                  {e.rotulo}
                </label>
              ))}
            </div>
          </div>
          <div style={{ marginTop: espaco.lg, display: "flex", gap: espaco.md, alignItems: "center", flexWrap: "wrap" }}>
            <button type="submit" style={estiloBotao.primario} disabled={aGravar}>{aGravar ? tr("A adicionar…") : tr("Adicionar jogador")}</button>
            {msg && <span role="status" style={{ fontSize: "0.84rem", color: msg.tipo === "ok" ? cores.sucesso : cores.perigo }}>{msg.texto}</span>}
          </div>
        </form>
      </Cartao>
    </section>
  );
}

function EquipasAtleta({ atleta, equipas, adicionar, remover }: {
  atleta: AtletaLista;
  equipas: EquipaAcad[];
  adicionar: (team_id: string, rotulo: string) => void;
  remover: (team_id: string, rotulo: string) => void;
}) {
  const tr = useTr();
  const ids = new Set(atleta.equipas.map((e) => e.team_id));
  const livres = equipas.filter((e) => !ids.has(e.team_id));
  const visiveis = atleta.equipas.filter((e) => equipas.some((q) => q.team_id === e.team_id));
  return (
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
      {visiveis.length === 0 && <span style={{ color: cores.textoFraco, fontSize: "0.8rem" }}>{tr("sem equipa")}</span>}
      {visiveis.map((e) => (
        <span key={e.team_id} style={chip}>
          {e.escalao ?? e.rotulo}
          <button title={tr("Tirar dos {0}", [e.rotulo])} onClick={() => remover(e.team_id, e.escalao ?? e.rotulo)}
            style={{ background: "none", border: "none", color: cores.textoFraco, cursor: "pointer", padding: 0, marginLeft: 4, fontSize: "0.9rem", lineHeight: 1 }}>
            ×
          </button>
        </span>
      ))}
      {livres.length > 0 && (
        <select value="" onChange={(ev) => { const e = livres.find((x) => x.team_id === ev.target.value); if (e) adicionar(e.team_id, e.escalao ?? e.rotulo); }}
          style={{ ...campo, height: 24, width: 30, padding: "0 4px", fontSize: "0.8rem", color: cores.textoSuave, appearance: "none", textAlign: "center", cursor: "pointer" }}
          title={tr("Adicionar a outra equipa")} aria-label={tr("Adicionar a outra equipa")}>
          <option value="">+</option>
          {livres.map((e) => <option key={e.team_id} value={e.team_id}>{e.rotulo}</option>)}
        </select>
      )}
    </div>
  );
}

function Pendente({ cor, texto, ativo, alternar }: { cor: string; texto: string; ativo: boolean; alternar: () => void }) {
  const tr = useTr();
  return (
    <div style={{ display: "flex", alignItems: "center", gap: espaco.md, flexWrap: "wrap", fontSize: "0.8rem", color: cores.texto,
      borderLeft: `3px solid ${cor}`, background: `color-mix(in srgb, ${cor} 8%, transparent)`, borderRadius: raio.sm, padding: `${espaco.sm}px ${espaco.md}px` }}>
      <span style={{ flex: 1, minWidth: 220 }}>{texto}</span>
      <button onClick={alternar} style={{ ...estiloBotao.ligacao, fontSize: "0.78rem" }}>{ativo ? tr("Mostrar todos") : tr("Mostrar só esses")}</button>
    </div>
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

const campo: React.CSSProperties = { background: cores.bgCartao, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: cores.textoForte, fontSize: "0.82rem", padding: "6px 8px", height: 32 };
const chip: React.CSSProperties = { display: "inline-flex", alignItems: "center", border: `1px solid ${cores.bordaForte}`, borderRadius: 999, padding: "2px 10px", fontSize: "0.76rem", color: cores.texto, whiteSpace: "nowrap" };
const th: React.CSSProperties = { padding: `9px ${espaco.lg}px`, fontSize: "0.68rem", fontWeight: 500, color: cores.textoFraco, letterSpacing: "0.03em" };
const td: React.CSSProperties = { padding: `10px ${espaco.lg}px`, fontSize: "0.85rem", color: cores.texto };
