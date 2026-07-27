import { cores } from "@/lib/theme";
import type { RankingItem } from "@/lib/types";

/** Porta direta de _ranking_bar_row() em utils/ui_safe.py. */
function RankingBarRow({
  rank,
  nome,
  valor,
  unidade,
  pct,
  cor,
  subida,
}: {
  rank: number;
  nome: string;
  valor: number;
  unidade: string;
  pct: number;
  cor: string;
  subida: boolean;
}) {
  const seta = subida ? "▲" : "▼";
  const setaCor = subida ? cores.sucesso : cores.perigo;
  const largura = Math.max(4, Math.min(100, pct));
  const nomeCurto = nome.length <= 13 ? nome : `${nome.slice(0, 12)}…`;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, margin: "5px 0" }}>
      <div
        style={{
          width: 20,
          height: 20,
          borderRadius: "50%",
          background: cor,
          color: "white",
          fontSize: "0.64rem",
          fontWeight: 800,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
        }}
      >
        {rank}
      </div>
      <div
        title={nome}
        style={{
          width: 76,
          fontSize: "0.72rem",
          color: "rgba(255,255,255,0.85)",
          fontWeight: 600,
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
          flexShrink: 0,
        }}
      >
        {nomeCurto}
      </div>
      <div
        style={{
          flex: 1,
          background: "rgba(255,255,255,0.06)",
          borderRadius: 6,
          height: 20,
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div style={{ width: `${largura}%`, height: "100%", background: cor, borderRadius: 6 }} />
        <span
          style={{
            position: "absolute",
            right: 7,
            top: "50%",
            transform: "translateY(-50%)",
            fontSize: "0.65rem",
            fontWeight: 700,
            color: "white",
            textShadow: "0 1px 2px rgba(0,0,0,0.45)",
          }}
        >
          {valor.toLocaleString("pt-PT")}
          {unidade}
        </span>
      </div>
      <div style={{ minWidth: 48, textAlign: "right", fontSize: "0.65rem", fontWeight: 800, color: setaCor }}>
        {pct.toFixed(0)}% {seta}
      </div>
    </div>
  );
}

/** Porta direta de ranking_metric_card() em utils/ui_safe.py — Top3/Bottom3 com barras. */
export function RankingCard({
  icon,
  titulo,
  cor,
  top3,
  bottom3,
  unidade,
}: {
  icon: string;
  titulo: string;
  cor: string;
  top3: RankingItem[];
  bottom3: RankingItem[];
  unidade: string;
}) {
  if (top3.length === 0) return null;
  const maxVal = top3[0].valor || 1;
  const corBottom = `${cor}75`; // tom mais suave (alpha hex), igual ao Python

  return (
    <div
      style={{
        background: "#12171f",
        border: "1px solid rgba(255,255,255,0.08)",
        borderLeft: `3px solid ${cor}`,
        borderRadius: 12,
        boxShadow: "0 1px 2px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.04) inset",
        padding: "16px 18px",
        marginBottom: 14,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
        <span style={{ fontSize: "1.1rem" }}>{icon}</span>
        <span className="font-display" style={{ fontWeight: 600, color: "white", fontSize: "0.9rem" }}>{titulo}</span>
      </div>

      <div
        style={{
          fontSize: "0.64rem",
          color: cor,
          fontWeight: 700,
          letterSpacing: "1px",
          textTransform: "uppercase",
          marginBottom: 6,
        }}
      >
        🥇 Top 3
      </div>
      {top3.map((item, i) => (
        <RankingBarRow
          key={item.jogador}
          rank={i + 1}
          nome={item.jogador}
          valor={item.valor}
          unidade={unidade}
          pct={maxVal ? (item.valor / maxVal) * 100 : 0}
          cor={cor}
          subida
        />
      ))}

      <div
        style={{
          fontSize: "0.64rem",
          color: "rgba(255,255,255,0.4)",
          fontWeight: 700,
          letterSpacing: "1px",
          textTransform: "uppercase",
          margin: "12px 0 6px",
        }}
      >
        🔻 Bottom 3
      </div>
      {bottom3.map((item, i) => (
        <RankingBarRow
          key={item.jogador}
          rank={i + 1}
          nome={item.jogador}
          valor={item.valor}
          unidade={unidade}
          pct={maxVal ? (item.valor / maxVal) * 100 : 0}
          cor={corBottom}
          subida={false}
        />
      ))}
    </div>
  );
}
