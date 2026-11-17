"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { pedidoApi } from "@/lib/api-cliente";
import { cores, espaco, raio } from "@/lib/theme";
import type { EstadoJogador } from "@/lib/types";
import { useTr } from "@/lib/i18n/cliente";
import { Cartao, estiloBotao } from "@/components/ui/base";

interface Lado { player_id: string; nome: string; estado: string; sessoes: number; lesoes: number; ultima_sessao: string | null }
interface Par { manter: Lado; juntar: Lado }

const campo: React.CSSProperties = {
  background: cores.bgCartao, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: cores.textoForte,
  fontSize: "0.84rem", padding: "6px 8px", height: 34, minWidth: 0, flex: 1,
};

/** Jogadores duplicados (o mesmo jogador com o nome escrito de maneiras
 * diferentes, ex.: «Olle Brännström» no GPS e «Olle Brannstrom» na PSE):
 * mostra os pares prováveis e junta-os — tudo passa para o que fica. */
export function JuntarJogadores({ teamId, jogadores }: { teamId: string; jogadores: EstadoJogador[] }) {
  const tr = useTr();
  const router = useRouter();
  const [pares, setPares] = useState<Par[] | null>(null);
  const [trocados, setTrocados] = useState<Record<number, boolean>>({});
  const [manual, setManual] = useState({ manter: "", juntar: "" });
  const [ocupado, setOcupado] = useState(false);
  const [msg, setMsg] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);

  async function carregar() {
    try {
      setPares((await pedidoApi<{ pares: Par[] }>(`/api/teams/${teamId}/jogadores/duplicados`)).pares);
    } catch {
      setPares([]);
    }
  }
  useEffect(() => { carregar(); }, [teamId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function juntar(manterId: string, juntarId: string, manterNome: string, juntarNome: string) {
    if (!window.confirm(tr("Juntar «{0}» em «{1}»? As sessões, PSE, wellness, lesões e testes de «{0}» passam para «{1}» e «{0}» é apagado. Não dá para desfazer.", [juntarNome, manterNome]))) return;
    setOcupado(true); setMsg(null);
    try {
      await pedidoApi(`/api/teams/${teamId}/jogadores/juntar`, "POST", { origem_id: juntarId, destino_id: manterId });
      setMsg({ tipo: "ok", texto: tr("«{0}» foi junto em «{1}».", [juntarNome, manterNome]) });
      setTrocados({}); setManual({ manter: "", juntar: "" });
      await carregar();
      router.refresh();
    } catch (e) {
      setMsg({ tipo: "erro", texto: (e as Error).message });
    } finally {
      setOcupado(false);
    }
  }

  const ativos = jogadores.filter((j) => j.ativo);
  const nome = (id: string) => ativos.find((j) => j.player_id === id)?.nome ?? "";
  const descr = (l: Lado) => tr("{0} sessões", [l.sessoes]) + (l.lesoes ? ` · ${tr("{0} lesões", [l.lesoes])}` : "");

  return (
    <Cartao style={{ marginTop: espaco.xxl }}>
      <div style={{ fontWeight: 600, color: cores.textoForte, fontSize: "0.95rem", marginBottom: 4 }}>{tr("Jogadores duplicados")}</div>
      <p style={{ margin: `0 0 ${espaco.md}px`, fontSize: "0.8rem", color: cores.textoSuave, lineHeight: 1.5 }}>
        {tr("O mesmo jogador com o nome escrito de maneiras diferentes (com e sem acentos, ou com um erro) aparece duas vezes. Juntar passa tudo — sessões, PSE, wellness, lesões e testes — para o jogador que fica.")}
      </p>

      {pares === null ? null : pares.length === 0 ? (
        <div style={{ fontSize: "0.8rem", color: cores.textoSuave, marginBottom: espaco.md }}>{tr("Não encontrei nomes parecidos no plantel.")}</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: espaco.sm, marginBottom: espaco.md }}>
          {pares.map((p, i) => {
            const [m, j] = trocados[i] ? [p.juntar, p.manter] : [p.manter, p.juntar];
            return (
              <div key={`${p.manter.player_id}-${p.juntar.player_id}`} style={{ display: "flex", alignItems: "center", gap: espaco.sm, flexWrap: "wrap", background: cores.superficie, borderRadius: raio.sm, padding: `${espaco.sm}px ${espaco.md}px`, fontSize: "0.82rem" }}>
                <span style={{ color: cores.textoSuave }}>{tr("Manter")}</span>
                <strong style={{ color: cores.textoForte }}>{m.nome}</strong>
                <span style={{ color: cores.textoFraco, fontSize: "0.74rem" }}>({descr(m)})</span>
                <button style={estiloBotao.ligacao} onClick={() => setTrocados({ ...trocados, [i]: !trocados[i] })} disabled={ocupado} title={tr("Trocar qual fica")}>⇄</button>
                <span style={{ color: cores.textoSuave }}>{tr("juntar")}</span>
                <strong style={{ color: cores.textoForte }}>{j.nome}</strong>
                <span style={{ color: cores.textoFraco, fontSize: "0.74rem" }}>({descr(j)})</span>
                <button style={{ ...estiloBotao.primario, marginLeft: "auto" }} onClick={() => juntar(m.player_id, j.player_id, m.nome, j.nome)} disabled={ocupado}>
                  {tr("Juntar jogadores")}
                </button>
              </div>
            );
          })}
        </div>
      )}

      <div style={{ fontSize: "0.74rem", color: cores.textoSuave, margin: `${espaco.sm}px 0 4px` }}>{tr("Ou escolhe à mão:")}</div>
      <div style={{ display: "flex", gap: espaco.sm, alignItems: "center", flexWrap: "wrap" }}>
        <select style={campo} value={manual.manter} onChange={(e) => setManual({ ...manual, manter: e.target.value })}>
          <option value="">{tr("Jogador que fica…")}</option>
          {ativos.map((j) => <option key={j.player_id} value={j.player_id}>{j.nome}</option>)}
        </select>
        <span style={{ color: cores.textoSuave, fontSize: "0.8rem" }}>←</span>
        <select style={campo} value={manual.juntar} onChange={(e) => setManual({ ...manual, juntar: e.target.value })}>
          <option value="">{tr("Duplicado a juntar…")}</option>
          {ativos.filter((j) => j.player_id !== manual.manter).map((j) => <option key={j.player_id} value={j.player_id}>{j.nome}</option>)}
        </select>
        <button style={estiloBotao.secundario} disabled={ocupado || !manual.manter || !manual.juntar}
          onClick={() => juntar(manual.manter, manual.juntar, nome(manual.manter), nome(manual.juntar))}>{tr("Juntar jogadores")}</button>
      </div>

      {msg && <div style={{ marginTop: espaco.sm, fontSize: "0.8rem", color: msg.tipo === "ok" ? cores.sucesso : cores.perigo }}>{msg.texto}</div>}
    </Cartao>
  );
}
