"use client";

import { useEffect, useState } from "react";
import { pedidoApi } from "@/lib/api-cliente";
import { cores, espaco, raio } from "@/lib/theme";
import { Cartao, Etiqueta, SecaoTitulo, Vazio, estiloBotao } from "@/components/ui/base";

type Papel = "head" | "pf" | "treinador";
interface Equipa { team_id: string; rotulo: string; escalao: string | null; epoca: string | null }
interface Membro { user_id: string; nome: string; email: string | null; eu: boolean; papel: Papel; equipas: { team_id: string; rotulo: string; role: string }[] }
interface Convite { id: string; papel: Papel; equipas: string[]; email: string | null; nome: string | null; token: string; expira_em: string; convidado_por: string }
interface Dados {
  disponivel: boolean; motivo?: string; pode_gerir: boolean; pode_convidar: boolean; meu_papel: Papel;
  equipas: Equipa[]; equipas_editaveis: string[]; papeis: Record<Papel, string>; membros: Membro[]; convites: Convite[];
}

const COR: Record<Papel, string> = { head: "#a855f7", pf: "#3b82f6", treinador: "#64748b" };
const DESCRICAO: Record<Papel, string> = {
  head: "vê e gere a academia toda, incluindo a equipa técnica",
  pf: "edita as equipas escolhidas (testes, planeamento, jogos, cargas)",
  treinador: "consulta as equipas escolhidas, sem alterar nada",
};

/** Equipa técnica: membros, papéis e convites por link. */
export function EquipaTecnica() {
  const [dados, setDados] = useState<Dados | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);
  const [editar, setEditar] = useState<string | null>(null);

  async function carregar() {
    try {
      setDados(await pedidoApi<Dados>("/api/academia/equipa-tecnica"));
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro inesperado.");
    }
  }
  useEffect(() => { carregar(); }, []);

  async function executar(acao: () => Promise<unknown>, ok: string) {
    setAviso(null);
    try {
      await acao();
      setAviso({ tipo: "ok", texto: ok });
      await carregar();
      return true;
    } catch (e) {
      setAviso({ tipo: "erro", texto: e instanceof Error ? e.message : "Erro inesperado." });
      return false;
    }
  }

  if (erro) return <Vazio>{erro}</Vazio>;
  if (!dados) return <p style={{ color: cores.textoSuave, fontSize: "0.88rem" }}>A carregar…</p>;
  if (!dados.disponivel) return <Vazio>{dados.motivo}</Vazio>;

  const linkDe = (token: string) => `${window.location.origin}/convite/${token}`;

  return (
    <section style={{ display: "flex", flexDirection: "column", gap: espaco.lg }}>
      <SecaoTitulo subtitulo="Quem trabalha na academia e com que papel. Os colegas entram por um link de convite.">Equipa técnica</SecaoTitulo>
      {aviso && <div role="status" style={{ fontSize: "0.84rem", color: aviso.tipo === "ok" ? cores.sucesso : cores.perigo }}>{aviso.texto}</div>}

      <Cartao padding={0}>
        {dados.membros.map((m, i) => (
          <div key={m.user_id} style={{ padding: `${espaco.md}px ${espaco.lg}px`, borderTop: i ? `1px solid ${cores.borda}` : "none" }}>
            <div style={{ display: "flex", alignItems: "center", gap: espaco.md, flexWrap: "wrap" }}>
              <div style={{ flex: "1 1 220px", minWidth: 0 }}>
                <div style={{ fontWeight: 600, color: cores.textoForte }}>{m.nome}{m.eu && <span style={{ color: cores.textoFraco, fontWeight: 400 }}> · tu</span>}</div>
                <div style={{ fontSize: "0.76rem", color: cores.textoSuave }}>{m.email ?? "—"}</div>
              </div>
              <Etiqueta cor={COR[m.papel]}>{dados.papeis[m.papel]}</Etiqueta>
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap", flex: "2 1 260px" }}>
                {m.papel === "head" ? <span style={chip}>Todas as equipas</span> : m.equipas.map((e) => <span key={e.team_id} style={chip}>{e.rotulo}</span>)}
              </div>
              {dados.pode_gerir && !m.eu && (
                <div style={{ display: "flex", gap: espaco.md }}>
                  <button style={estiloBotao.ligacao} onClick={() => setEditar(editar === m.user_id ? null : m.user_id)}>Alterar</button>
                  <button style={{ ...estiloBotao.ligacao, color: cores.perigo }} onClick={() => {
                    if (confirm(`Remover ${m.nome} da academia? Deixa de ter acesso a todas as equipas.`))
                      executar(() => pedidoApi(`/api/academia/membros/${m.user_id}`, "DELETE"), `${m.nome} removido.`);
                  }}>Remover</button>
                </div>
              )}
            </div>
            {editar === m.user_id && (
              <EscolhaPapel
                equipas={dados.equipas} papeis={dados.papeis} permitirHead
                inicial={{ papel: m.papel, equipas: m.equipas.map((e) => e.team_id) }}
                rotuloBotao="Guardar"
                guardar={async (papel, team_ids) => {
                  const ok = await executar(() => pedidoApi(`/api/academia/membros/${m.user_id}`, "PATCH", { papel, team_ids }), `Papel de ${m.nome} atualizado.`);
                  if (ok) setEditar(null);
                }}
              />
            )}
          </div>
        ))}
      </Cartao>

      {dados.pode_convidar && (
        <Cartao>
          <div style={{ fontWeight: 700, color: cores.textoForte, marginBottom: 4 }}>Convidar colega</div>
          <p style={{ fontSize: "0.78rem", color: cores.textoSuave, margin: `0 0 ${espaco.md}px` }}>
            Escolhe o papel e as equipas. A app cria um link pessoal (válido 14 dias) para enviares por email ou WhatsApp.
          </p>
          <NovoConvite dados={dados} criar={async (corpo) => {
            const r = await pedidoApi<{ token: string }>("/api/academia/convites", "POST", corpo);
            await carregar();
            return linkDe(r.token);
          }} />
        </Cartao>
      )}

      {dados.convites.length > 0 && (
        <div>
          <div style={{ fontSize: "0.72rem", color: cores.textoSuave, fontWeight: 600, margin: `0 0 ${espaco.sm}px` }}>Convites por aceitar</div>
          <Cartao padding={0}>
            {dados.convites.map((c, i) => (
              <div key={c.id} style={{ display: "flex", alignItems: "center", gap: espaco.md, flexWrap: "wrap", padding: `${espaco.sm}px ${espaco.lg}px`, borderTop: i ? `1px solid ${cores.borda}` : "none", fontSize: "0.82rem" }}>
                <span style={{ flex: "1 1 200px", color: cores.texto }}>{c.nome || c.email || "Convite sem nome"} <span style={{ color: cores.textoFraco }}>· {c.equipas.join(", ") || "todas as equipas"}</span></span>
                <Etiqueta cor={COR[c.papel]}>{dados.papeis[c.papel]}</Etiqueta>
                <span style={{ color: cores.textoFraco }}>até {new Date(c.expira_em).toLocaleDateString("pt-PT")}</span>
                <CopiarLink link={linkDe(c.token)} />
                <button style={{ ...estiloBotao.ligacao, color: cores.perigo }} onClick={() => executar(() => pedidoApi(`/api/academia/convites/${c.id}`, "DELETE"), "Convite cancelado.")}>Cancelar</button>
              </div>
            ))}
          </Cartao>
        </div>
      )}
    </section>
  );
}

function NovoConvite({ dados, criar }: { dados: Dados; criar: (c: { papel: Papel; team_ids: string[]; email: string | null; nome: string | null }) => Promise<string> }) {
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [link, setLink] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const equipas = dados.pode_gerir ? dados.equipas : dados.equipas.filter((e) => dados.equipas_editaveis.includes(e.team_id));
  return (
    <div>
      <div style={{ display: "flex", gap: espaco.md, flexWrap: "wrap", marginBottom: espaco.md }}>
        <Rot t="Nome (opcional)"><input value={nome} onChange={(e) => setNome(e.target.value)} placeholder="ex.: Erik" style={campo} /></Rot>
        <Rot t="Email (opcional — só essa conta pode aceitar)"><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="erik@clube.se" style={{ ...campo, width: 260 }} /></Rot>
      </div>
      <EscolhaPapel
        equipas={equipas} papeis={dados.papeis} permitirHead={dados.pode_gerir}
        inicial={{ papel: "pf", equipas: equipas.length === 1 ? [equipas[0].team_id] : [] }}
        rotuloBotao="Criar link de convite"
        guardar={async (papel, team_ids) => {
          setErro(null);
          try {
            setLink(await criar({ papel, team_ids, email: email || null, nome: nome || null }));
          } catch (e) {
            setErro(e instanceof Error ? e.message : "Erro.");
          }
        }}
      />
      {erro && <p style={{ color: cores.perigo, fontSize: "0.82rem" }}>{erro}</p>}
      {link && (
        <div style={{ marginTop: espaco.md, padding: espaco.md, borderRadius: raio.sm, background: cores.superficie, display: "flex", gap: espaco.md, alignItems: "center", flexWrap: "wrap" }}>
          <code style={{ fontSize: "0.78rem", color: cores.textoForte, wordBreak: "break-all", flex: "1 1 260px" }}>{link}</code>
          <CopiarLink link={link} />
          <a style={{ ...estiloBotao.secundario, textDecoration: "none" }} target="_blank" rel="noreferrer"
            href={`https://wa.me/?text=${encodeURIComponent(`Convite para a app de monitorização da academia: ${link}`)}`}>WhatsApp</a>
          <a style={{ ...estiloBotao.secundario, textDecoration: "none" }}
            href={`mailto:${email}?subject=${encodeURIComponent("Convite — app da academia")}&body=${encodeURIComponent(`Olá${nome ? ` ${nome}` : ""},\n\nConvido-te para a app de monitorização da academia:\n${link}\n\nO link é válido durante 14 dias.`)}`}>Email</a>
        </div>
      )}
    </div>
  );
}

function EscolhaPapel({ equipas, papeis, permitirHead, inicial, rotuloBotao, guardar }: {
  equipas: Equipa[]; papeis: Record<Papel, string>; permitirHead: boolean;
  inicial: { papel: Papel; equipas: string[] }; rotuloBotao: string; guardar: (papel: Papel, team_ids: string[]) => Promise<void>;
}) {
  const [papel, setPapel] = useState<Papel>(inicial.papel);
  const [sel, setSel] = useState<string[]>(inicial.equipas);
  const [aGravar, setAGravar] = useState(false);
  const opcoes = (Object.keys(papeis) as Papel[]).filter((p) => permitirHead || p !== "head");
  return (
    <div style={{ marginTop: espaco.sm }}>
      <div role="radiogroup" aria-label="Papel" style={{ display: "flex", gap: espaco.sm, flexWrap: "wrap" }}>
        {opcoes.map((p) => (
          <label key={p} style={{ flex: "1 1 200px", display: "flex", gap: 8, alignItems: "flex-start", cursor: "pointer", border: `1px solid ${papel === p ? cores.acento : cores.bordaForte}`, borderRadius: raio.sm, padding: "8px 10px" }}>
            <input type="radio" name={`papel-${rotuloBotao}`} checked={papel === p} onChange={() => setPapel(p)} />
            <span>
              <span style={{ fontWeight: 600, color: cores.textoForte, fontSize: "0.84rem" }}>{papeis[p]}</span>
              <span style={{ display: "block", fontSize: "0.74rem", color: cores.textoSuave }}>{DESCRICAO[p]}</span>
            </span>
          </label>
        ))}
      </div>
      {papel !== "head" && (
        <div style={{ display: "flex", gap: espaco.sm, flexWrap: "wrap", marginTop: espaco.md }}>
          {equipas.map((e) => (
            <label key={e.team_id} style={{ display: "inline-flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: "0.82rem", border: `1px solid ${sel.includes(e.team_id) ? cores.acento : cores.bordaForte}`, borderRadius: raio.sm, padding: "5px 10px", color: cores.textoForte }}>
              <input type="checkbox" checked={sel.includes(e.team_id)} onChange={() => setSel(sel.includes(e.team_id) ? sel.filter((x) => x !== e.team_id) : [...sel, e.team_id])} />
              {e.rotulo}
            </label>
          ))}
        </div>
      )}
      <button style={{ ...estiloBotao.primario, marginTop: espaco.md }} disabled={aGravar || (papel !== "head" && sel.length === 0)}
        onClick={async () => { setAGravar(true); await guardar(papel, papel === "head" ? [] : sel); setAGravar(false); }}>
        {aGravar ? "A guardar…" : rotuloBotao}
      </button>
      {papel !== "head" && sel.length === 0 && <span style={{ fontSize: "0.76rem", color: cores.textoSuave, marginLeft: espaco.md }}>Escolhe pelo menos uma equipa.</span>}
    </div>
  );
}

function CopiarLink({ link }: { link: string }) {
  const [copiado, setCopiado] = useState(false);
  return (
    <button style={estiloBotao.secundario} onClick={async () => {
      try { await navigator.clipboard.writeText(link); setCopiado(true); setTimeout(() => setCopiado(false), 1500); } catch { prompt("Copia o link:", link); }
    }}>{copiado ? "Copiado ✓" : "Copiar link"}</button>
  );
}

function Rot({ t, children }: { t: string; children: React.ReactNode }) {
  return <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: "0.72rem", color: cores.textoSuave, fontWeight: 500 }}>{t}{children}</label>;
}

const chip: React.CSSProperties = { fontSize: "0.74rem", border: `1px solid ${cores.bordaForte}`, borderRadius: 999, padding: "1px 8px", color: cores.texto, whiteSpace: "nowrap" };
const campo: React.CSSProperties = { background: cores.bgCartao, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: cores.textoForte, fontSize: "0.84rem", padding: "6px 8px", height: 34, boxSizing: "border-box", width: 200 };
