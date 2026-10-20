"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { pedidoApi } from "@/lib/api-cliente";
import { cores, espaco, raio } from "@/lib/theme";
import { Cartao, SecaoTitulo, Vazio } from "@/components/ui/base";
import { NomeJogador } from "@/components/ui/NomeJogador";
import type { AtletaLista } from "./tipos";

/** Todos os atletas da academia — uma ficha por atleta, para todas as épocas. */
export function ListaAtletas() {
  const [dados, setDados] = useState<{ disponivel: boolean; motivo?: string; atletas: AtletaLista[] } | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [busca, setBusca] = useState("");
  const [escalao, setEscalao] = useState("");

  useEffect(() => {
    pedidoApi<{ disponivel: boolean; motivo?: string; atletas: AtletaLista[] }>("/api/academia/atletas")
      .then(setDados)
      .catch((e) => setErro(e.message));
  }, []);

  const escaloes = useMemo(() => [...new Set((dados?.atletas ?? []).map((a) => a.escalao_atual).filter(Boolean))] as string[], [dados]);
  const lista = useMemo(() => {
    const q = busca.trim().toLowerCase();
    return (dados?.atletas ?? []).filter((a) => (!q || a.nome.toLowerCase().includes(q)) && (!escalao || a.escalao_atual === escalao));
  }, [dados, busca, escalao]);

  if (erro) return <Vazio>{erro}</Vazio>;
  if (!dados) return <p style={{ color: cores.textoSuave, fontSize: "0.88rem" }}>A carregar…</p>;
  if (!dados.disponivel) return <Vazio>{dados.motivo}</Vazio>;

  const semNascimento = dados.atletas.filter((a) => !a.data_nascimento).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: espaco.lg }}>
      <SecaoTitulo
        subtitulo={`${dados.atletas.length} atleta(s)${semNascimento ? ` · ${semNascimento} sem data de nascimento (necessária para idade, maturação e percentis)` : ""}`}
        acoes={
          <>
            <input placeholder="Procurar atleta" value={busca} onChange={(e) => setBusca(e.target.value)} style={{ ...campo, width: 200 }} />
            <select value={escalao} onChange={(e) => setEscalao(e.target.value)} style={campo}>
              <option value="">Todos os escalões</option>
              {escaloes.map((e) => <option key={e} value={e}>{e}</option>)}
            </select>
          </>
        }
      >
        Atletas da academia
      </SecaoTitulo>
      {lista.length === 0 ? (
        <Vazio>{dados.atletas.length ? "Nenhum atleta corresponde à pesquisa." : "Ainda não há atletas — importa dados de uma equipa ou cria jogadores em Definições."}</Vazio>
      ) : (
        <Cartao padding={0}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 640 }}>
              <thead>
                <tr>{["Atleta", "Idade", "Escalão atual", "Épocas", "Avaliações", "Última avaliação"].map((h, i) => <th key={h} style={{ ...th, textAlign: i > 0 && i < 5 && i !== 2 ? "right" : "left" }}>{h}</th>)}</tr>
              </thead>
              <tbody>
                {lista.map((a) => (
                  <tr key={a.atleta_id} style={{ borderTop: `1px solid ${cores.borda}` }}>
                    <td style={td}>
                      <Link href={`/academia/atleta/${a.atleta_id}`} style={{ color: cores.textoForte, fontWeight: 600, textDecoration: "none" }}>
                        <NomeJogador nome={a.nome} />
                      </Link>
                      {a.posicao && <span style={{ color: cores.textoFraco }}> · {a.posicao}</span>}
                    </td>
                    <td style={{ ...td, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{a.idade != null ? Math.floor(a.idade) : <span style={{ color: cores.textoFraco }}>—</span>}</td>
                    <td style={td}>{a.escalao_atual ? `${a.escalao_atual} · ${a.epoca_atual}` : <span style={{ color: cores.textoFraco }}>—</span>}</td>
                    <td style={{ ...td, textAlign: "right" }}>{a.epocas}</td>
                    <td style={{ ...td, textAlign: "right" }}>{a.n_avaliacoes}</td>
                    <td style={{ ...td, color: cores.textoSuave }}>{a.ultima_avaliacao ? new Date(`${a.ultima_avaliacao}T00:00:00`).toLocaleDateString("pt-PT") : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Cartao>
      )}
    </div>
  );
}

const campo: React.CSSProperties = { background: cores.bgCartao, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: cores.textoForte, fontSize: "0.82rem", padding: "6px 8px", height: 32 };
const th: React.CSSProperties = { padding: `9px ${espaco.lg}px`, fontSize: "0.68rem", fontWeight: 500, color: cores.textoFraco, letterSpacing: "0.03em" };
const td: React.CSSProperties = { padding: `10px ${espaco.lg}px`, fontSize: "0.85rem", color: cores.texto };
