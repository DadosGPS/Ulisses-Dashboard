import type { AlertaDashboard } from "@/lib/types";

const COR_ESTADO: Record<string, string> = {
  RISCO: "#e74c3c",
  "ATENÇÃO": "#f39c12",
};

function corDoAlerta(estado: string): string {
  const chave = Object.keys(COR_ESTADO).find((k) => estado.includes(k));
  return chave ? COR_ESTADO[chave] : "#888";
}

/** Lista de alertas prioritários — mesmo padrão visual do bloco em app_pages/dashboard.py. */
export function AlertList({ alertas }: { alertas: AlertaDashboard[] }) {
  if (alertas.length === 0) {
    return (
      <div
        style={{
          background: "rgba(34,197,94,0.08)",
          border: "1px solid rgba(34,197,94,0.3)",
          borderRadius: 10,
          padding: "12px 16px",
          color: "#22c55e",
          fontSize: "0.85rem",
        }}
      >
        ✅ Nenhum alerta ativo — toda a equipa dentro dos parâmetros normais.
      </div>
    );
  }

  return (
    <div>
      {alertas.map((a, i) => {
        const cor = corDoAlerta(a.estado);
        return (
          <div
            key={`${a.jogador}-${a.tipo}-${i}`}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "10px 16px",
              margin: "3px 0",
              background: `${cor}0d`,
              borderLeft: `3px solid ${cor}`,
              borderRadius: "0 8px 8px 0",
            }}
          >
            <div style={{ minWidth: 90 }}>
              <b style={{ color: cor, fontSize: "0.9rem" }}>{a.jogador}</b>
              <div style={{ fontSize: "0.65rem", color: "#888" }}>{a.posicao}</div>
            </div>
            <div style={{ flex: 1, fontSize: "0.8rem", color: "rgba(255,255,255,0.7)" }}>
              {a.tipo === "ACWR" ? "Carga excessiva" : "Fadiga/stress elevado"}
            </div>
            <span
              style={{
                background: `${cor}22`,
                color: cor,
                padding: "3px 8px",
                borderRadius: 4,
                fontSize: "0.7rem",
                fontWeight: 700,
              }}
            >
              {a.tipo} {a.valor}
            </span>
          </div>
        );
      })}
    </div>
  );
}
