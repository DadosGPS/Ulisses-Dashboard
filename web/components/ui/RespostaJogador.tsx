"use client";

import { cores } from "@/lib/theme";
import { useEffect, useState } from "react";

/** Página que o jogador abre no telemóvel a partir do WhatsApp — sem login,
 * identificada só pelo token secreto do link. Botões grandes, uma mão. */

type Pedido = { tipo: "wellness" | "pse"; data: string; nome: string; respondido: boolean; expirado: boolean };

const ITENS: { chave: "sono" | "dor_musc" | "stress" | "humor"; pergunta: string; escala: string[] }[] = [
  { chave: "sono", pergunta: "Como dormiste?", escala: ["Muito mal", "Mal", "Normal", "Bem", "Muito bem"] },
  { chave: "dor_musc", pergunta: "Dores musculares?", escala: ["Muitas", "Bastantes", "Algumas", "Poucas", "Nenhumas"] },
  { chave: "stress", pergunta: "Nível de stress?", escala: ["Muito alto", "Alto", "Normal", "Baixo", "Nenhum"] },
  { chave: "humor", pergunta: "Como está o teu humor?", escala: ["Muito mau", "Mau", "Normal", "Bom", "Muito bom"] },
];

// Escala CR-10 de Borg modificada por Foster (PSE da sessão).
const PSE: { valor: number; label: string }[] = [
  { valor: 0, label: "Repouso" },
  { valor: 1, label: "Muito, muito fácil" },
  { valor: 2, label: "Fácil" },
  { valor: 3, label: "Moderado" },
  { valor: 4, label: "Algo difícil" },
  { valor: 5, label: "Difícil" },
  { valor: 6, label: "" },
  { valor: 7, label: "Muito difícil" },
  { valor: 8, label: "" },
  { valor: 9, label: "" },
  { valor: 10, label: "Máximo" },
];

const COR_ESCALA = ["#ef4444", "#f97316", "#eab308", "#84cc16", "#22c55e"];
const corPse = (v: number) => (v <= 2 ? "#22c55e" : v <= 4 ? "#84cc16" : v <= 6 ? "#eab308" : v <= 8 ? "#f97316" : "#ef4444");

export function RespostaJogador({ token }: { token: string }) {
  const api = `${process.env.NEXT_PUBLIC_API_URL}/api/r/${token}`;
  const [pedido, setPedido] = useState<Pedido | null>(null);
  const [estado, setEstado] = useState<"a_carregar" | "pronto" | "erro" | "enviado">("a_carregar");
  const [erro, setErro] = useState<string | null>(null);
  const [wellness, setWellness] = useState<Record<string, number>>({});
  const [pse, setPse] = useState<number | null>(null);
  const [aEnviar, setAEnviar] = useState(false);

  useEffect(() => {
    fetch(api)
      .then(async (r) => {
        if (!r.ok) throw new Error(r.status === 404 ? "Este link não é válido." : "Não foi possível abrir o questionário.");
        setPedido(await r.json());
        setEstado("pronto");
      })
      .catch((e) => {
        setErro(e.message);
        setEstado("erro");
      });
  }, [api]);

  async function enviar() {
    setAEnviar(true);
    setErro(null);
    try {
      const corpo = pedido?.tipo === "pse" ? { pse } : wellness;
      const r = await fetch(api, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo) });
      if (!r.ok) {
        const j = await r.json().catch(() => null);
        throw new Error(j?.detail ?? "Não foi possível enviar. Tenta outra vez.");
      }
      setEstado("enviado");
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro inesperado.");
    } finally {
      setAEnviar(false);
    }
  }

  const completo = pedido?.tipo === "pse" ? pse !== null : ITENS.every((i) => wellness[i.chave]);
  const dataLegivel = pedido ? new Date(`${pedido.data}T00:00:00`).toLocaleDateString("pt-PT", { weekday: "long", day: "numeric", month: "long" }) : "";

  return (
    <main style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--text)", padding: "20px 16px 40px", maxWidth: 480, margin: "0 auto" }}>
      {estado === "a_carregar" && <p style={suave}>A abrir…</p>}
      {estado === "erro" && <Mensagem titulo="Ups" texto={erro ?? ""} />}
      {estado === "enviado" && <Mensagem titulo="Obrigado!" texto="Resposta registada. Já podes fechar esta página." />}

      {estado === "pronto" && pedido && pedido.expirado && <Mensagem titulo="Link expirado" texto="Este questionário já fechou. Fala com o preparador físico se quiseres registar a resposta." />}

      {estado === "pronto" && pedido && !pedido.expirado && (
        <>
          <h1 style={{ fontSize: "1.35rem", margin: "0 0 4px" }}>Olá, {pedido.nome}!</h1>
          <p style={{ ...suave, margin: "0 0 20px" }}>{dataLegivel.charAt(0).toUpperCase() + dataLegivel.slice(1)}</p>
          {pedido.respondido && <p style={{ ...suave, background: "rgba(59,130,246,0.12)", padding: 10, borderRadius: 10 }}>Já respondeste — se enviares de novo, a resposta é atualizada.</p>}

          {pedido.tipo === "wellness" ? (
            ITENS.map((item) => (
              <section key={item.chave} style={{ marginBottom: 22 }}>
                <h2 style={pergunta}>{item.pergunta}</h2>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 6 }}>
                  {item.escala.map((label, i) => {
                    const v = i + 1;
                    const ativo = wellness[item.chave] === v;
                    return (
                      <button key={v} onClick={() => setWellness({ ...wellness, [item.chave]: v })} aria-pressed={ativo}
                        style={{ ...opcao, borderColor: ativo ? COR_ESCALA[i] : "rgb(var(--ink) / 0.12)", background: ativo ? `${COR_ESCALA[i]}33` : "rgb(var(--ink) / 0.04)" }}>
                        <span style={{ fontSize: "1.15rem", fontWeight: 800, color: COR_ESCALA[i] }}>{v}</span>
                        <span style={{ fontSize: "0.66rem", lineHeight: 1.15 }}>{label}</span>
                      </button>
                    );
                  })}
                </div>
              </section>
            ))
          ) : (
            <section style={{ marginBottom: 22 }}>
              <h2 style={pergunta}>Qual foi o esforço do treino de hoje?</h2>
              <p style={{ ...suave, margin: "0 0 12px" }}>Pensa na sessão inteira, do aquecimento ao fim.</p>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {[...PSE].reverse().map((p) => {
                  const ativo = pse === p.valor;
                  const cor = corPse(p.valor);
                  return (
                    <button key={p.valor} onClick={() => setPse(p.valor)} aria-pressed={ativo}
                      style={{ display: "flex", alignItems: "center", gap: 14, minHeight: 46, padding: "0 14px", borderRadius: 12, border: `2px solid ${ativo ? cor : "rgb(var(--ink) / 0.1)"}`, background: ativo ? `${cor}33` : "rgb(var(--ink) / 0.04)", color: cores.textoForte, fontSize: "0.95rem", cursor: "pointer", textAlign: "left" }}>
                      <span style={{ width: 28, fontSize: "1.2rem", fontWeight: 800, color: cor }}>{p.valor}</span>
                      <span>{p.label}</span>
                    </button>
                  );
                })}
              </div>
            </section>
          )}

          {erro && <p style={{ color: "#f87171", fontSize: "0.9rem" }}>{erro}</p>}
          <button onClick={enviar} disabled={!completo || aEnviar}
            style={{ width: "100%", minHeight: 54, borderRadius: 14, border: "none", background: completo ? "#22c55e" : "rgb(var(--ink) / 0.1)", color: "white", fontSize: "1.05rem", fontWeight: 800, cursor: completo ? "pointer" : "default", position: "sticky", bottom: 16 }}>
            {aEnviar ? "A enviar…" : completo ? "Enviar resposta" : "Responde a todas as perguntas"}
          </button>
        </>
      )}
    </main>
  );
}

function Mensagem({ titulo, texto }: { titulo: string; texto: string }) {
  return (
    <div style={{ textAlign: "center", marginTop: "30vh" }}>
      <h1 style={{ fontSize: "1.5rem", margin: "0 0 8px" }}>{titulo}</h1>
      <p style={suave}>{texto}</p>
    </div>
  );
}

const suave: React.CSSProperties = { color: "rgb(var(--ink) / 0.6)", fontSize: "0.92rem" };
const pergunta: React.CSSProperties = { fontSize: "1.02rem", fontWeight: 700, margin: "0 0 8px" };
const opcao: React.CSSProperties = { display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 2, minHeight: 64, padding: "6px 2px", borderRadius: 12, border: "2px solid", color: cores.textoForte, cursor: "pointer" };
