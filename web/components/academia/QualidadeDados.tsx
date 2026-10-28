"use client";

/** Qualidade dos dados por equipa e por mês: % dos jogador-dias com sessão que
 * têm wellness, PSE e GPS. Antes de comparar equipas, saber em que números se
 * pode confiar. */
import { useEffect, useState } from "react";
import { cores, espaco, raio } from "@/lib/theme";
import { SecaoTitulo, Vazio } from "@/components/ui/base";
import { pedidoApi } from "@/lib/api-cliente";
import { useTr } from "@/lib/i18n/cliente";

type Mes = { mes: string; jogador_dias: number; dias_sessao: number;
  wellness_pct: number; pse_pct: number; gps_pct: number;
  wellness_nivel: Nivel; pse_nivel: Nivel; gps_nivel: Nivel };
type Nivel = "bom" | "medio" | "fraco" | null;
type Resposta = { meses: number; limites: { bom: number; fraco: number }; equipas: { team_id: string; nome?: string; escalao?: string | null; epoca?: string | null; meses: Mes[] }[] };

const COR: Record<string, string> = { bom: cores.sucesso, medio: cores.atencao, fraco: cores.perigo };

export function QualidadeDados() {
  const tr = useTr();
  const [dados, setDados] = useState<Resposta | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  useEffect(() => {
    pedidoApi<{ disponivel: boolean; academias: { academia_id: string }[] }>("/api/academia")
      .then((d) => {
        const a = d.academias?.[0];
        if (!a) { setErro(tr("Ainda não pertences a nenhuma academia.")); return; }
        return pedidoApi<Resposta>(`/api/academia/${a.academia_id}/qualidade-dados?meses=3`).then(setDados);
      })
      .catch((e) => setErro(e.message));
  }, [tr]);

  const nomeMes = (m: string) => new Date(`${m}-01T00:00:00`).toLocaleDateString(tr.loc, { month: "short", year: "2-digit" });
  const celula = (pct: number, nivel: Nivel) => (
    <td style={{ ...td, textAlign: "right" }}>
      <span style={{ fontWeight: 600, color: nivel ? COR[nivel] : cores.texto, fontVariantNumeric: "tabular-nums" }}>{Math.round(pct)}%</span>
    </td>
  );
  return (
    <section>
      <SecaoTitulo subtitulo={dados ? tr("Percentagem dos jogador-dias com sessão que têm cada registo. Verde ≥ {0} %, vermelho < {1} %: abaixo disso, a prontidão e as comparações entre equipas não são fiáveis.", [dados.limites.bom, dados.limites.fraco]) : undefined}>
        {tr("Qualidade dos dados por equipa")}</SecaoTitulo>
      {erro ? <Vazio>{erro}</Vazio> : !dados ? <Vazio>{tr("A carregar…")}</Vazio> : dados.equipas.length === 0 ? (
        <Vazio>{tr("Sem sessões nos últimos {0} meses.", [dados.meses])}</Vazio>
      ) : (
        <div style={{ overflowX: "auto", background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem", minWidth: 620 }}>
            <thead>
              <tr style={{ background: "rgb(var(--ink) / 0.04)" }}>
                {["Equipa", "Mês", "Dias de sessão", "Wellness", "PSE", "GPS"].map((h, i) => (
                  <th key={h} style={{ ...th, textAlign: i > 1 ? "right" : "left" }}>{tr(h)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dados.equipas.flatMap((e) => e.meses.map((m, i) => (
                <tr key={`${e.team_id}-${m.mes}`} style={{ borderTop: `1px solid ${cores.borda}` }}>
                  <td style={{ ...td, fontWeight: 600 }}>{i === 0 ? [e.escalao, e.epoca].filter(Boolean).join(" · ") || e.nome : ""}</td>
                  <td style={td}>{nomeMes(m.mes)}</td>
                  <td style={{ ...td, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{m.dias_sessao}</td>
                  {celula(m.wellness_pct, m.wellness_nivel)}
                  {celula(m.pse_pct, m.pse_nivel)}
                  {celula(m.gps_pct, m.gps_nivel)}
                </tr>
              )))}
            </tbody>
          </table>
        </div>
      )}
      <div style={{ height: espaco.lg }} />
    </section>
  );
}

const th: React.CSSProperties = { padding: "7px 10px", fontSize: "0.68rem", letterSpacing: "0.04em", textTransform: "uppercase", color: cores.textoSuave, fontWeight: 600, whiteSpace: "nowrap" };
const td: React.CSSProperties = { padding: "7px 10px", color: cores.texto, whiteSpace: "nowrap" };
