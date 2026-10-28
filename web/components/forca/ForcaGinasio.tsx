"use client";

/** Força e ginásio: prescrever uma sessão, registar o que cada jogador fez
 * (séries × repetições × carga + PSE) e seguir a progressão (tonelagem por
 * semana e 1RM estimado por exercício). A PSE × duração entra na carga
 * interna do dia como sessão «Ginásio». */
import { useEffect, useState } from "react";
import { cores, espaco, raio } from "@/lib/theme";
import { Cartao, SecaoTitulo, Vazio, estiloBotao } from "@/components/ui/base";
import { pedidoApi } from "@/lib/api-cliente";
import { useTr } from "@/lib/i18n/cliente";

type Linha = { exercicio: string; series: number | null; repeticoes: number | null; carga_kg: number | null; feito?: boolean; e1rm?: number | null };
type SessaoResumo = { id: string; data: string; nome: string; duracao_min: number | null; n_jogadores: number; tonelagem: number };
type JogadorSessao = { player_id: string; nome: string; linhas: Linha[]; tonelagem: number; pse: number | null; duracao_min: number | null };
type Sessao = { id: string; data: string; nome: string; duracao_min: number | null; prescricao: Linha[]; notas: string | null; jogadores: JogadorSessao[] };
type Jogador = { player_id: string; nome: string; estado: string; ativo: boolean };
type Progressao = { disponivel: boolean; motivo: string | null; semanas: { semana: string; tonelagem: number; sessoes: number }[];
  exercicios: { exercicio: string; atual: number; variacao_pct: number | null; serie: { data: string; e1rm: number }[] }[] };

const vazia = (): Linha => ({ exercicio: "", series: 3, repeticoes: 8, carga_kg: null });
const hoje = () => new Date().toLocaleDateString("sv-SE");
const num = (v: string) => (v === "" ? null : Number(v.replace(",", ".")));

export function ForcaGinasio({ teamId }: { teamId: string }) {
  const tr = useTr();
  const [sessoes, setSessoes] = useState<SessaoResumo[] | null>(null);
  const [motivo, setMotivo] = useState<string | null>(null);
  const [jogadores, setJogadores] = useState<Jogador[]>([]);
  const [modo, setModo] = useState<{ tipo: "lista" } | { tipo: "nova" } | { tipo: "sessao"; id: string } | { tipo: "jogador"; id: string }>({ tipo: "lista" });
  const [erro, setErro] = useState<string | null>(null);

  async function carregar() {
    try {
      const r = await pedidoApi<{ disponivel: boolean; motivo: string | null; sessoes: SessaoResumo[] }>(`/api/teams/${teamId}/forca/sessoes`);
      setSessoes(r.sessoes);
      setMotivo(r.disponivel ? null : r.motivo);
    } catch (e) {
      setErro(e instanceof Error ? e.message : String(e));
    }
  }
  useEffect(() => {
    carregar();
    pedidoApi<{ jogadores: Jogador[] }>(`/api/teams/${teamId}/jogadores/estado`).then((r) => setJogadores(r.jogadores.filter((j) => j.ativo))).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [teamId]);

  if (erro) return <Vazio>{erro}</Vazio>;
  if (!sessoes) return <Vazio>{tr("A carregar…")}</Vazio>;
  if (motivo) return <Vazio>{motivo}</Vazio>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: espaco.xl }}>
      <div style={{ display: "flex", gap: espaco.sm, flexWrap: "wrap", alignItems: "center" }}>
        <button onClick={() => setModo({ tipo: "lista" })} style={modo.tipo === "lista" ? estiloBotao.primario : estiloBotao.secundario}>{tr("Sessões")}</button>
        <button onClick={() => setModo({ tipo: "nova" })} style={modo.tipo === "nova" ? estiloBotao.primario : estiloBotao.secundario}>{tr("Nova sessão")}</button>
        <select aria-label={tr("Progressão de um jogador")} value={modo.tipo === "jogador" ? modo.id : ""}
          onChange={(e) => e.target.value && setModo({ tipo: "jogador", id: e.target.value })}
          style={{ fontSize: "0.82rem", padding: "6px 9px", borderRadius: raio.sm, border: `1px solid ${cores.borda}`, background: cores.bgCartao, color: cores.texto }}>
          <option value="">{tr("Progressão de um jogador…")}</option>
          {jogadores.map((j) => <option key={j.player_id} value={j.player_id}>{j.nome}</option>)}
        </select>
      </div>

      {modo.tipo === "lista" && <ListaSessoes sessoes={sessoes} abrir={(id) => setModo({ tipo: "sessao", id })} />}
      {modo.tipo === "nova" && <NovaSessao teamId={teamId} jogadores={jogadores}
        criada={async (id) => { await carregar(); setModo({ tipo: "sessao", id }); }} />}
      {modo.tipo === "sessao" && <DetalheSessao teamId={teamId} id={modo.id}
        apagada={async () => { await carregar(); setModo({ tipo: "lista" }); }} atualizada={carregar} />}
      {modo.tipo === "jogador" && <ProgressaoJogador teamId={teamId} id={modo.id} nome={jogadores.find((j) => j.player_id === modo.id)?.nome ?? ""} />}
    </div>
  );
}

function ListaSessoes({ sessoes, abrir }: { sessoes: SessaoResumo[]; abrir: (id: string) => void }) {
  const tr = useTr();
  return (
    <section>
      <SecaoTitulo subtitulo={tr("Últimos 60 dias. Abre uma sessão para registar o que cada jogador fez e a PSE.")}>{tr("Sessões de ginásio")}</SecaoTitulo>
      {sessoes.length === 0 ? <Vazio>{tr("Ainda não há sessões. Cria a primeira em «Nova sessão».")}</Vazio> : (
        <Cartao padding={0}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
            <thead><tr style={{ background: "rgb(var(--ink) / 0.04)" }}>
              {["Data", "Sessão", "Jogadores", "Tonelagem"].map((h, i) => <th key={h} style={{ ...th, textAlign: i > 1 ? "right" : "left" }}>{tr(h)}</th>)}
            </tr></thead>
            <tbody>
              {sessoes.map((s) => (
                <tr key={s.id} onClick={() => abrir(s.id)} className="lm-linha" style={{ borderTop: `1px solid ${cores.borda}`, cursor: "pointer" }}>
                  <td style={td}>{new Date(`${s.data}T00:00:00`).toLocaleDateString(tr.loc, { weekday: "short", day: "numeric", month: "short" })}</td>
                  <td style={{ ...td, fontWeight: 600 }}>{s.nome}</td>
                  <td style={tdN}>{s.n_jogadores}</td>
                  <td style={tdN}>{s.tonelagem.toLocaleString(tr.loc)} kg</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Cartao>
      )}
    </section>
  );
}

function TabelaLinhas({ linhas, mudar, comFeito }: { linhas: Linha[]; mudar: (l: Linha[]) => void; comFeito?: boolean }) {
  const tr = useTr();
  const set = (i: number, k: keyof Linha, v: unknown) => mudar(linhas.map((l, j) => (j === i ? { ...l, [k]: v } : l)));
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem", minWidth: 520 }}>
        <thead><tr>
          {[...(comFeito ? ["Feito"] : []), "Exercício", "Séries", "Reps", "Carga (kg)", ...(comFeito ? ["1RM est."] : []), ""].map((h, i) => <th key={i} style={th}>{tr(h)}</th>)}
        </tr></thead>
        <tbody>
          {linhas.map((l, i) => (
            <tr key={i} style={{ borderTop: `1px solid ${cores.borda}`, opacity: comFeito && l.feito === false ? 0.5 : 1 }}>
              {comFeito && <td style={td}><input type="checkbox" aria-label={tr("Feito")} checked={l.feito !== false} onChange={(e) => set(i, "feito", e.target.checked)} /></td>}
              <td style={td}><input aria-label={tr("Exercício")} value={l.exercicio} onChange={(e) => set(i, "exercicio", e.target.value)} placeholder={tr("ex.: Agachamento")} style={{ ...inp, width: 180, textAlign: "left" }} /></td>
              <td style={td}><input aria-label={tr("Séries")} inputMode="numeric" value={l.series ?? ""} onChange={(e) => set(i, "series", num(e.target.value))} style={inp} /></td>
              <td style={td}><input aria-label={tr("Reps")} inputMode="numeric" value={l.repeticoes ?? ""} onChange={(e) => set(i, "repeticoes", num(e.target.value))} style={inp} /></td>
              <td style={td}><input aria-label={tr("Carga (kg)")} inputMode="decimal" value={l.carga_kg ?? ""} onChange={(e) => set(i, "carga_kg", num(e.target.value))} placeholder={tr("peso corporal")} style={{ ...inp, width: 96 }} /></td>
              {comFeito && <td style={tdN}>{l.e1rm ? `${l.e1rm.toLocaleString(tr.loc)} kg` : "—"}</td>}
              <td style={td}><button onClick={() => mudar(linhas.filter((_, j) => j !== i))} aria-label={tr("Remover exercício")} style={{ ...estiloBotao.ligacao, fontSize: "0.78rem" }}>✕</button></td>
            </tr>
          ))}
        </tbody>
      </table>
      <button onClick={() => mudar([...linhas, vazia()])} style={{ ...estiloBotao.ligacao, fontSize: "0.8rem", marginTop: 6 }}>{tr("+ exercício")}</button>
    </div>
  );
}

function NovaSessao({ teamId, jogadores, criada }: { teamId: string; jogadores: Jogador[]; criada: (id: string) => void }) {
  const tr = useTr();
  const [data, setData] = useState(hoje());
  const [nome, setNome] = useState("");
  const [duracao, setDuracao] = useState<number | null>(45);
  const [linhas, setLinhas] = useState<Linha[]>([vazia()]);
  const [escolhidos, setEscolhidos] = useState<Set<string>>(new Set());
  const [aGuardar, setAGuardar] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  useEffect(() => { setEscolhidos(new Set(jogadores.filter((j) => j.estado === "apto").map((j) => j.player_id))); }, [jogadores]);

  async function criar() {
    setAGuardar(true);
    setErro(null);
    try {
      const r = await pedidoApi<{ id: string }>(`/api/teams/${teamId}/forca/sessoes`, "POST", {
        data, nome, duracao_min: duracao, prescricao: linhas.filter((l) => l.exercicio.trim()), jogadores: [...escolhidos],
      });
      criada(r.id);
    } catch (e) {
      setErro(e instanceof Error ? e.message : String(e));
    } finally {
      setAGuardar(false);
    }
  }
  const alternar = (id: string) => setEscolhidos((s) => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  return (
    <section>
      <SecaoTitulo subtitulo={tr("A prescrição é copiada para cada jogador escolhido; depois ajustas o que cada um fez.")}>{tr("Nova sessão de ginásio")}</SecaoTitulo>
      <Cartao>
        <div style={{ display: "flex", gap: espaco.md, flexWrap: "wrap", marginBottom: espaco.md }}>
          <label style={lbl}>{tr("Data")}<input type="date" value={data} onChange={(e) => setData(e.target.value)} style={{ ...inp, width: 150 }} /></label>
          <label style={{ ...lbl, flex: 1, minWidth: 220 }}>{tr("Nome")}<input value={nome} onChange={(e) => setNome(e.target.value)} placeholder={tr("ex.: Força — membros inferiores")} style={{ ...inp, width: "100%", textAlign: "left" }} /></label>
          <label style={lbl}>{tr("Duração (min)")}<input inputMode="numeric" value={duracao ?? ""} onChange={(e) => setDuracao(num(e.target.value))} style={{ ...inp, width: 90 }} /></label>
        </div>
        <TabelaLinhas linhas={linhas} mudar={setLinhas} />
        <div style={{ marginTop: espaco.md, fontSize: "0.8rem", color: cores.textoSuave }}>{tr("Jogadores ({0})", [escolhidos.size])}</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 6 }}>
          {jogadores.map((j) => (
            <label key={j.player_id} style={{ display: "inline-flex", gap: 5, alignItems: "center", padding: "3px 9px", borderRadius: 999, border: `1px solid ${cores.borda}`, fontSize: "0.78rem", opacity: j.estado === "apto" ? 1 : 0.6 }}>
              <input type="checkbox" checked={escolhidos.has(j.player_id)} onChange={() => alternar(j.player_id)} />{j.nome}
            </label>
          ))}
        </div>
        <div style={{ display: "flex", gap: espaco.md, alignItems: "center", marginTop: espaco.lg }}>
          <button disabled={aGuardar} onClick={criar} style={estiloBotao.primario}>{aGuardar ? tr("A guardar…") : tr("Criar sessão")}</button>
          {erro && <span role="alert" style={{ fontSize: "0.8rem", color: cores.perigo }}>{erro}</span>}
        </div>
      </Cartao>
    </section>
  );
}

function DetalheSessao({ teamId, id, apagada, atualizada }: { teamId: string; id: string; apagada: () => void; atualizada: () => void }) {
  const tr = useTr();
  const [s, setS] = useState<Sessao | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const carregar = () => pedidoApi<Sessao>(`/api/teams/${teamId}/forca/sessoes/${id}`).then(setS).catch((e) => setErro(e.message));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { carregar(); }, [id]);
  if (erro) return <Vazio>{erro}</Vazio>;
  if (!s) return <Vazio>{tr("A carregar…")}</Vazio>;
  async function apagar() {
    if (!window.confirm(tr("Apagar esta sessão e o que foi registado nela?"))) return;
    await pedidoApi(`/api/teams/${teamId}/forca/sessoes/${id}`, "DELETE");
    apagada();
  }
  return (
    <section>
      <SecaoTitulo
        subtitulo={`${new Date(`${s.data}T00:00:00`).toLocaleDateString(tr.loc, { weekday: "long", day: "numeric", month: "long" })}${s.duracao_min ? ` · ${s.duracao_min} min` : ""}`}
        acoes={<button onClick={apagar} style={{ ...estiloBotao.ligacao, color: cores.perigo }}>{tr("Apagar sessão")}</button>}>
        {s.nome}</SecaoTitulo>
      <div style={{ display: "flex", flexDirection: "column", gap: espaco.md }}>
        {s.jogadores.map((j) => <CartaoJogador key={j.player_id} teamId={teamId} sessao={s} j={j} guardado={() => { carregar(); atualizada(); }} />)}
      </div>
    </section>
  );
}

function CartaoJogador({ teamId, sessao, j, guardado }: { teamId: string; sessao: Sessao; j: JogadorSessao; guardado: () => void }) {
  const tr = useTr();
  const [linhas, setLinhas] = useState<Linha[]>(j.linhas);
  const [pse, setPse] = useState<number | null>(j.pse);
  const [msg, setMsg] = useState<{ ok: boolean; t: string } | null>(null);
  const [aGuardar, setAGuardar] = useState(false);
  async function guardar() {
    setAGuardar(true);
    setMsg(null);
    try {
      const r = await pedidoApi<{ tonelagem: number }>(`/api/teams/${teamId}/forca/sessoes/${sessao.id}/jogadores/${j.player_id}`, "PUT", {
        linhas: linhas.filter((l) => l.exercicio.trim()), pse, duracao_min: j.duracao_min ?? sessao.duracao_min,
      });
      setMsg({ ok: true, t: tr("Guardado · {0} kg", [r.tonelagem.toLocaleString(tr.loc)]) });
      guardado();
    } catch (e) {
      setMsg({ ok: false, t: e instanceof Error ? e.message : String(e) });
    } finally {
      setAGuardar(false);
    }
  }
  return (
    <Cartao>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: espaco.md, flexWrap: "wrap", marginBottom: 8 }}>
        <span style={{ fontWeight: 600, color: cores.textoForte }}>{j.nome}</span>
        <span style={{ fontSize: "0.78rem", color: cores.textoSuave }}>{tr("Tonelagem")} {j.tonelagem.toLocaleString(tr.loc)} kg</span>
      </div>
      <TabelaLinhas linhas={linhas} mudar={setLinhas} comFeito />
      <div style={{ display: "flex", gap: espaco.md, alignItems: "center", flexWrap: "wrap", marginTop: espaco.md }}>
        <label style={{ ...lbl, flexDirection: "row", alignItems: "center", gap: 6 }}>{tr("PSE (0–10)")}
          <input inputMode="decimal" value={pse ?? ""} onChange={(e) => setPse(num(e.target.value))} style={{ ...inp, width: 60 }} /></label>
        <button disabled={aGuardar} onClick={guardar} style={estiloBotao.primario}>{aGuardar ? tr("A guardar…") : tr("Guardar")}</button>
        {msg && <span role={msg.ok ? "status" : "alert"} style={{ fontSize: "0.78rem", color: msg.ok ? cores.sucesso : cores.perigo }}>{msg.t}</span>}
      </div>
      {pse == null && <p style={{ margin: "6px 0 0", fontSize: "0.74rem", color: cores.textoFraco }}>{tr("Sem PSE, a sessão não entra na carga interna nem no ACWR.")}</p>}
    </Cartao>
  );
}

function ProgressaoJogador({ teamId, id, nome }: { teamId: string; id: string; nome: string }) {
  const tr = useTr();
  const [p, setP] = useState<Progressao | null>(null);
  useEffect(() => { pedidoApi<Progressao>(`/api/teams/${teamId}/forca/jogador/${id}`).then(setP).catch(() => setP(null)); }, [teamId, id]);
  if (!p) return <Vazio>{tr("A carregar…")}</Vazio>;
  if (!p.disponivel) return <Vazio>{p.motivo}</Vazio>;
  return (
    <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 340px), 1fr))", gap: espaco.lg }}>
      <div>
        <SecaoTitulo subtitulo={tr("Séries × repetições × carga, por semana (últimas 8).")}>{tr("Tonelagem de {0}", [nome])}</SecaoTitulo>
        {p.semanas.length === 0 ? <Vazio>{tr("Sem sessões de ginásio registadas nas últimas 8 semanas.")}</Vazio> : (
          <Cartao padding={0}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
              <thead><tr style={{ background: "rgb(var(--ink) / 0.04)" }}>{["Semana de", "Sessões", "Tonelagem"].map((h, i) => <th key={h} style={{ ...th, textAlign: i ? "right" : "left" }}>{tr(h)}</th>)}</tr></thead>
              <tbody>{p.semanas.map((s) => (
                <tr key={s.semana} style={{ borderTop: `1px solid ${cores.borda}` }}>
                  <td style={td}>{new Date(`${s.semana}T00:00:00`).toLocaleDateString(tr.loc, { day: "numeric", month: "short" })}</td>
                  <td style={tdN}>{s.sessoes}</td><td style={tdN}>{s.tonelagem.toLocaleString(tr.loc)} kg</td>
                </tr>))}</tbody>
            </table>
          </Cartao>
        )}
      </div>
      <div>
        <SecaoTitulo subtitulo={tr("1RM estimado (Epley) da melhor série de cada sessão, com 12 repetições ou menos.")}>{tr("Força por exercício")}</SecaoTitulo>
        {p.exercicios.length === 0 ? <Vazio>{tr("Ainda sem séries com carga para estimar o 1RM.")}</Vazio> : (
          <Cartao padding={0}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
              <thead><tr style={{ background: "rgb(var(--ink) / 0.04)" }}>{["Exercício", "Sessões", "1RM est.", "Desde o início"].map((h, i) => <th key={h} style={{ ...th, textAlign: i ? "right" : "left" }}>{tr(h)}</th>)}</tr></thead>
              <tbody>{p.exercicios.map((e) => (
                <tr key={e.exercicio} style={{ borderTop: `1px solid ${cores.borda}` }}>
                  <td style={{ ...td, fontWeight: 600 }}>{e.exercicio}</td>
                  <td style={tdN}>{e.serie.length}</td>
                  <td style={tdN}>{e.atual.toLocaleString(tr.loc)} kg</td>
                  <td style={{ ...tdN, color: (e.variacao_pct ?? 0) > 0 ? cores.sucesso : (e.variacao_pct ?? 0) < 0 ? cores.perigo : cores.textoSuave }}>
                    {e.variacao_pct == null ? "—" : `${e.variacao_pct > 0 ? "+" : ""}${e.variacao_pct.toLocaleString(tr.loc)}%`}</td>
                </tr>))}</tbody>
            </table>
          </Cartao>
        )}
      </div>
    </section>
  );
}

const th: React.CSSProperties = { padding: "7px 10px", fontSize: "0.68rem", letterSpacing: "0.04em", textTransform: "uppercase", color: cores.textoSuave, fontWeight: 600, whiteSpace: "nowrap", textAlign: "left" };
const td: React.CSSProperties = { padding: "6px 8px", color: cores.texto };
const tdN: React.CSSProperties = { ...td, textAlign: "right", fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" };
const inp: React.CSSProperties = { width: 64, padding: "5px 7px", fontSize: "0.82rem", borderRadius: raio.sm, border: `1px solid ${cores.borda}`, background: cores.bg, color: cores.textoForte, textAlign: "center" };
const lbl: React.CSSProperties = { display: "flex", flexDirection: "column", gap: 4, fontSize: "0.74rem", color: cores.textoSuave };
