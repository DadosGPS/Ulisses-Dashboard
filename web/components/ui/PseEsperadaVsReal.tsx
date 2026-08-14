"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { NomeJogador } from "@/components/ui/NomeJogador";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { cores, espaco, raio } from "@/lib/theme";
import type { PseSemanaResponse } from "@/lib/types";

/** PSE esperada (planeada pelo preparador) vs PSE real (registada nos
 * uploads), cruzada com a monotonia de cada jogador nessa semana — permite
 * confirmar visualmente se um plano (ex: deload) foi mesmo executado. */
export function PseEsperadaVsReal({ teamId, dadosIniciais }: { teamId: string; dadosIniciais: PseSemanaResponse }) {
  const [dados, setDados] = useState(dadosIniciais);
  const [aCarregar, setACarregar] = useState(false);
  const [aGuardar, setAGuardar] = useState<string | null>(null);

  async function token() {
    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();
    return session?.access_token ?? null;
  }

  async function mudarMicrociclo(mc: number) {
    setACarregar(true);
    const t = await token();
    if (!t) {
      setACarregar(false);
      return;
    }
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/planeamento/pse-semana?microciclo=${mc}`, {
        headers: { Authorization: `Bearer ${t}` },
      });
      if (res.ok) setDados(await res.json());
    } finally {
      setACarregar(false);
    }
  }

  async function guardarPseEsperada(diaMd: string, valor: number) {
    if (dados.microciclo === null) return;
    setAGuardar(diaMd);
    const t = await token();
    if (!t) {
      setAGuardar(null);
      return;
    }
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/planeamento/pse-esperada`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${t}` },
        body: JSON.stringify({ microciclo: dados.microciclo, dia_md: diaMd, pse_esperada: valor }),
      });
      setDados((atual) => ({
        ...atual,
        dias: atual.dias.map((d) => (d.dia_md === diaMd ? { ...d, pse_esperada: valor } : d)),
      }));
    } finally {
      setAGuardar(null);
    }
  }

  if (!dados.tem_dados) return null;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: espaco.md }}>
        <p style={{ color: cores.textoSuave, fontSize: "0.8rem", margin: 0, maxWidth: 560 }}>
          Define a PSE esperada de cada dia (o que planeaste) e compara com a PSE real registada nos uploads —
          útil para confirmar se um deload, por exemplo, realmente aconteceu.
        </p>
        {dados.microciclos_disponiveis.length > 0 && (
          <select
            value={dados.microciclo ?? ""}
            disabled={aCarregar}
            onChange={(e) => mudarMicrociclo(Number(e.target.value))}
            style={{
              background: cores.bgCartao,
              border: `1px solid ${cores.bordaForte}`,
              borderRadius: raio.sm,
              color: "white",
              padding: "8px 12px",
              fontSize: "0.85rem",
              fontWeight: 600,
              cursor: aCarregar ? "default" : "pointer",
              flexShrink: 0,
            }}
          >
            {dados.microciclos_disponiveis.map((mc) => (
              <option key={mc} value={mc}>
                Semana {mc}
              </option>
            ))}
          </select>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: espaco.lg, opacity: aCarregar ? 0.5 : 1 }}>
        <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
          <PlotlyChart
            data={[
              {
                x: dados.dias.map((d) => d.dia_md),
                y: dados.dias.map((d) => d.pse_esperada),
                type: "bar",
                name: "PSE Esperada",
                marker: { color: cores.info },
              },
              {
                x: dados.dias.map((d) => d.dia_md),
                y: dados.dias.map((d) => d.pse_real),
                type: "bar",
                name: "PSE Real",
                marker: { color: cores.cargaInterna },
              },
            ]}
            layout={{
              barmode: "group",
              legend: { orientation: "h", y: -0.18 },
              xaxis: { title: { text: "Dia do Microciclo" } },
              yaxis: { title: { text: "PSE (0-10)" }, range: [0, 10] },
            }}
            altura={260}
          />

          <div style={{ display: "flex", gap: espaco.sm, flexWrap: "wrap", marginTop: espaco.md }}>
            {dados.dias.map((d) => (
              <label key={d.dia_md} style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: "0.68rem", color: cores.textoSuave }}>
                {d.dia_md}
                <input
                  type="number"
                  min={0}
                  max={10}
                  step={0.5}
                  defaultValue={d.pse_esperada ?? ""}
                  disabled={aGuardar === d.dia_md}
                  placeholder="—"
                  onBlur={(e) => {
                    const v = parseFloat(e.target.value);
                    if (!Number.isNaN(v) && v !== d.pse_esperada) guardarPseEsperada(d.dia_md, v);
                  }}
                  style={{
                    width: 56,
                    background: cores.bg,
                    border: `1px solid ${cores.bordaForte}`,
                    borderRadius: raio.sm,
                    color: "white",
                    padding: "5px 6px",
                    fontSize: "0.78rem",
                  }}
                />
              </label>
            ))}
          </div>
        </div>

        <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md }}>
          <div style={{ fontSize: "0.68rem", color: cores.textoSuave, textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600, marginBottom: espaco.sm }}>
            Monotonia por Jogador · Semana {dados.microciclo}
          </div>
          {dados.monotonia_jogadores.length === 0 ? (
            <p style={{ color: cores.textoFraco, fontSize: "0.8rem" }}>Sem dados suficientes.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 4, maxHeight: 260, overflowY: "auto" }}>
              {dados.monotonia_jogadores.map((m) => (
                <div key={m.jogador} style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem", padding: "3px 0" }}>
                  <span style={{ color: "rgba(255,255,255,0.82)" }}>
                    <NomeJogador nome={m.jogador} />
                  </span>
                  <span style={{ fontWeight: 700, color: m.monotonia > 2 ? cores.perigo : m.monotonia > 1.5 ? cores.atencao : cores.sucesso }}>
                    {m.monotonia.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
