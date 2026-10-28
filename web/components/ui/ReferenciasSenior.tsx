"use client";

/** Referências do plantel sénior (Definições · Academia): os valores do
 * primeiro plantel em cada teste, geral e por posição. Cada ficha de atleta
 * mostra a distância que lhe falta. Só o responsável edita. */
import { useEffect, useState } from "react";
import { cores, espaco, raio } from "@/lib/theme";
import { Cartao, SecaoTitulo, estiloBotao } from "@/components/ui/base";
import { pedidoApi } from "@/lib/api-cliente";
import { useTr } from "@/lib/i18n/cliente";

type Metrica = { chave: string; label: string; unidade: string; grupo: string };
type Refs = Record<string, { valor?: number; posicoes?: Record<string, number> }>;
type Resposta = { referencias: Refs; metricas: Metrica[]; e_head: boolean };

const posTexto = (p?: Record<string, number>) => Object.entries(p ?? {}).map(([k, v]) => `${k}=${v}`).join(", ");
function lerPos(t: string): Record<string, number> {
  const out: Record<string, number> = {};
  for (const parte of t.split(",")) {
    const [k, v] = parte.split("=").map((x) => x.trim());
    const n = Number((v ?? "").replace(",", "."));
    if (k && v && Number.isFinite(n)) out[k] = n;
  }
  return out;
}

export function ReferenciasSenior() {
  const tr = useTr();
  const [academia, setAcademia] = useState<string | null>(null);
  const [dados, setDados] = useState<Resposta | null>(null);
  const [valores, setValores] = useState<Record<string, { valor: string; pos: string }>>({});
  const [msg, setMsg] = useState<{ ok: boolean; t: string } | null>(null);
  const [aGuardar, setAGuardar] = useState(false);

  useEffect(() => {
    pedidoApi<{ disponivel: boolean; academias: { academia_id: string }[] }>("/api/academia").then((d) => {
      const a = d.academias?.[0];
      if (!d.disponivel || !a) return;
      setAcademia(a.academia_id);
      pedidoApi<Resposta>(`/api/academia/${a.academia_id}/referencias-senior`).then((r) => {
        setDados(r);
        setValores(Object.fromEntries(r.metricas.map((m) => [m.chave, { valor: r.referencias[m.chave]?.valor?.toString() ?? "", pos: posTexto(r.referencias[m.chave]?.posicoes) }])));
      }).catch(() => setDados(null));
    }).catch(() => {});
  }, []);
  if (!academia || !dados) return null;

  async function guardar() {
    setAGuardar(true);
    setMsg(null);
    const referencias: Refs = {};
    for (const [k, v] of Object.entries(valores)) {
      const n = Number(v.valor.replace(",", "."));
      const pos = lerPos(v.pos);
      if ((v.valor && Number.isFinite(n)) || Object.keys(pos).length) referencias[k] = { ...(v.valor && Number.isFinite(n) ? { valor: n } : {}), ...(Object.keys(pos).length ? { posicoes: pos } : {}) };
    }
    try {
      const r = await pedidoApi<Resposta>(`/api/academia/${academia}/referencias-senior`, "PUT", { referencias });
      setDados(r);
      setMsg({ ok: true, t: tr("Guardado. As fichas dos atletas passam a mostrar a distância ao sénior.") });
    } catch (e) {
      setMsg({ ok: false, t: e instanceof Error ? e.message : String(e) });
    } finally {
      setAGuardar(false);
    }
  }

  return (
    <section>
      <SecaoTitulo subtitulo={tr("Valores do primeiro plantel em cada teste (mediana, ou o valor-alvo do clube). Por posição: ex. «DC=48, EX=46». Cada ficha de atleta mostra quanto lhe falta.")}>
        {tr("Referências do plantel sénior")}</SecaoTitulo>
      <Cartao padding={0}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem", minWidth: 560 }}>
            <thead><tr style={{ background: "rgb(var(--ink) / 0.04)" }}>
              {["Teste", "Sénior (geral)", "Por posição"].map((h) => <th key={h} style={th}>{tr(h)}</th>)}
            </tr></thead>
            <tbody>
              {dados.metricas.map((m) => (
                <tr key={m.chave} style={{ borderTop: `1px solid ${cores.borda}` }}>
                  <td style={td}>{tr(m.label)} <span style={{ color: cores.textoFraco }}>({m.unidade || "—"})</span></td>
                  <td style={td}><input aria-label={tr("Sénior (geral)")} disabled={!dados.e_head} inputMode="decimal" value={valores[m.chave]?.valor ?? ""}
                    onChange={(e) => setValores({ ...valores, [m.chave]: { ...valores[m.chave], valor: e.target.value } })} style={{ ...inp, width: 90 }} /></td>
                  <td style={td}><input aria-label={tr("Por posição")} disabled={!dados.e_head} value={valores[m.chave]?.pos ?? ""} placeholder="DC=…, EX=…"
                    onChange={(e) => setValores({ ...valores, [m.chave]: { ...valores[m.chave], pos: e.target.value } })} style={{ ...inp, width: 220, textAlign: "left" }} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div style={{ display: "flex", gap: espaco.md, alignItems: "center", padding: espaco.md, borderTop: `1px solid ${cores.borda}` }}>
          {dados.e_head ? <button disabled={aGuardar} onClick={guardar} style={estiloBotao.primario}>{aGuardar ? tr("A guardar…") : tr("Guardar referências")}</button>
            : <span style={{ fontSize: "0.78rem", color: cores.textoSuave }}>{tr("Só o responsável da academia pode alterar as referências.")}</span>}
          {msg && <span role={msg.ok ? "status" : "alert"} style={{ fontSize: "0.8rem", color: msg.ok ? cores.sucesso : cores.perigo }}>{msg.t}</span>}
        </div>
      </Cartao>
    </section>
  );
}

const th: React.CSSProperties = { padding: "7px 10px", fontSize: "0.68rem", letterSpacing: "0.04em", textTransform: "uppercase", color: cores.textoSuave, fontWeight: 600, textAlign: "left" };
const td: React.CSSProperties = { padding: "6px 10px", color: cores.texto };
const inp: React.CSSProperties = { padding: "5px 7px", fontSize: "0.82rem", borderRadius: raio.sm, border: `1px solid ${cores.borda}`, background: cores.bg, color: cores.textoForte, textAlign: "right" };
