import { cores, espaco, raio, sombra } from "@/lib/theme";
import type { Resumo5W1H } from "@/lib/types";

const COR_DIA_MD: Record<string, string> = {
  "MD-5": "#e63946",
  "MD-4": "#f39c12",
  "MD-3": "#e63946",
  "MD-2": "#f39c12",
  "MD-1": "#9b59b6",
  MD: "#e63946",
  "MD+1": "#3498db",
  "MD+2": "#2ecc71",
};

function formatarData(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("pt-PT", { weekday: "long", day: "numeric", month: "long" });
}

/**
 * Resumo da sessão mais recente segundo o modelo 5W+1H — transforma os
 * números brutos em comunicação com contexto, tal como ensinado no curso
 * "O Uso do GPS no Futebol" (S. Querido): Dados → Informação → Conhecimento.
 */
export function Resumo5W1HCard({ resumo }: { resumo: Resumo5W1H }) {
  const corDia = (resumo.dia_md && COR_DIA_MD[resumo.dia_md]) || cores.textoSuave;

  return (
    <div
      style={{
        background: cores.bgCartao,
        border: `1px solid ${cores.borda}`,
        borderRadius: raio.md,
        boxShadow: sombra.cartao,
        padding: espaco.lg,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: espaco.sm, marginBottom: espaco.lg }}>
        <div style={{ display: "flex", alignItems: "center", gap: espaco.sm }}>
          <span style={{ fontSize: "1.1rem" }}>🗞️</span>
          <span className="font-display" style={{ fontWeight: 600, color: "white", fontSize: "0.92rem" }}>
            Resumo da Sessão — Modelo 5W+1H
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: espaco.sm }}>
          {resumo.dia_md && (
            <span
              style={{
                fontFamily: "monospace",
                fontWeight: 700,
                fontSize: "0.78rem",
                color: corDia,
                background: `${corDia}18`,
                border: `1px solid ${corDia}40`,
                borderRadius: 6,
                padding: "3px 9px",
              }}
            >
              {resumo.dia_md}
            </span>
          )}
          <span style={{ fontSize: "0.76rem", color: cores.textoSuave, textTransform: "capitalize" }}>
            {formatarData(resumo.data)}
          </span>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: espaco.md,
          marginBottom: espaco.lg,
        }}
      >
        <Campo label="Quem" valor={`${resumo.who.n_jogadores} jogadores`} />
        <Campo label="Onde" valor={resumo.where} />
        <Campo label="Porquê" valor={resumo.why} />
        <Campo label="Como" valor={`Intensidade ${resumo.how}`} />
      </div>

      {resumo.what.length > 0 && (
        <div>
          <div
            style={{
              fontSize: "0.64rem",
              color: cores.textoSuave,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              fontWeight: 600,
              marginBottom: espaco.sm,
            }}
          >
            O quê — vs. média histórica de sessões {resumo.dia_md ?? "semelhantes"}
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {resumo.what.map((c) => (
              <LinhaComparacao key={c.metrica} comparacao={c} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Campo({ label, valor }: { label: string; valor: string }) {
  return (
    <div>
      <div style={{ fontSize: "0.62rem", color: cores.textoSuave, letterSpacing: "0.06em", textTransform: "uppercase", fontWeight: 600, marginBottom: 3 }}>
        {label}
      </div>
      <div style={{ fontSize: "0.85rem", color: "rgba(255,255,255,0.9)", fontWeight: 600, textTransform: "capitalize" }}>{valor}</div>
    </div>
  );
}

function LinhaComparacao({ comparacao }: { comparacao: Resumo5W1H["what"][number] }) {
  const { metrica, valor, media_historica, variacao_pct } = comparacao;
  const subida = (variacao_pct ?? 0) >= 0;
  const cor = variacao_pct === null ? cores.textoSuave : subida ? cores.sucesso : cores.perigo;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "7px 12px",
        background: "rgba(255,255,255,0.03)",
        borderRadius: 8,
        fontSize: "0.8rem",
      }}
    >
      <span style={{ color: "rgba(255,255,255,0.8)", fontWeight: 500 }}>{metrica}</span>
      <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ fontWeight: 700, color: "white" }}>{valor.toLocaleString("pt-PT")}</span>
        {media_historica !== null && variacao_pct !== null && (
          <>
            <span style={{ color: cores.textoFraco, fontSize: "0.72rem" }}>
              (média {media_historica.toLocaleString("pt-PT")})
            </span>
            <span style={{ color: cor, fontWeight: 700, fontSize: "0.76rem" }}>
              {subida ? "▲" : "▼"} {Math.abs(variacao_pct)}%
            </span>
          </>
        )}
      </span>
    </div>
  );
}
