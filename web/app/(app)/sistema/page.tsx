import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { KpiTile } from "@/components/ui/KpiTile";
import { cores, espaco, raio } from "@/lib/theme";
import type { SistemaResponse } from "@/lib/types";

async function obterSistema(teamId: string, accessToken: string): Promise<SistemaResponse> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/sistema`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Falha ao carregar (${res.status}).`);
  return res.json();
}

export default async function SistemaPage() {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) return null;

  const { data: membro } = await supabase
    .from("team_members")
    .select("team_id")
    .eq("user_id", session.user.id)
    .limit(1)
    .single();

  if (!membro) return <EstadoVazio mensagem="Ainda não estás associado a nenhuma equipa." />;

  let dados: SistemaResponse;
  try {
    dados = await obterSistema(membro.team_id, session.access_token);
  } catch {
    return <EstadoVazio mensagem="Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr." />;
  }

  const v = dados.validacao;

  return (
    <div>
      <PageHeader titulo="Sistema" subtitulo="Qualidade dos dados e histórico de carregamentos" />

      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        {v.tem_dados ? (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: espaco.md, marginBottom: espaco.xxl }}>
              <KpiTile label="Sessões" valor={v.total_sessoes ?? 0} unidade="registos" subLabel="total na base de dados" cor={cores.cargaInterna} />
              <KpiTile label="Jogadores" valor={v.total_jogadores ?? 0} unidade="" subLabel="jogadores distintos" cor={cores.distanciaTotal} />
              <KpiTile label="Microciclos" valor={v.microciclos ?? 0} unidade="" subLabel="semanas cobertas" cor={cores.hsr} />
              <KpiTile label="Período" valor={v.data_inicio ?? "—"} unidade="" subLabel={`até ${v.data_fim ?? "—"}`} cor={cores.velMax} />
            </div>

            <SecaoTitulo>✅ Completude dos Dados</SecaoTitulo>
            <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md, marginBottom: espaco.xxl }}>
              {(v.colunas ?? []).map((c) => (
                <div key={c.coluna} style={{ display: "flex", alignItems: "center", gap: espaco.sm, padding: "6px 0" }}>
                  <div style={{ width: 160, fontSize: "0.78rem", color: "rgba(255,255,255,0.8)" }}>{c.coluna}</div>
                  <div style={{ flex: 1, background: "rgba(255,255,255,0.06)", borderRadius: 6, height: 14, position: "relative", overflow: "hidden" }}>
                    <div
                      style={{
                        width: `${c.pct}%`,
                        height: "100%",
                        background: c.pct >= 90 ? cores.sucesso : c.pct >= 60 ? cores.atencao : cores.perigo,
                        borderRadius: 6,
                      }}
                    />
                  </div>
                  <div style={{ minWidth: 84, textAlign: "right", fontSize: "0.74rem", color: cores.textoSuave }}>
                    {c.preenchidas}/{c.total} ({c.pct.toFixed(0)}%)
                  </div>
                </div>
              ))}
            </div>
          </>
        ) : (
          <p style={{ color: cores.textoSuave, fontSize: "0.85rem", marginBottom: espaco.xxl }}>Ainda não há dados carregados.</p>
        )}

        <SecaoTitulo>📤 Histórico de Carregamentos</SecaoTitulo>
        {dados.uploads.length === 0 ? (
          <p style={{ color: cores.textoSuave, fontSize: "0.85rem" }}>Ainda não carregaste nenhum ficheiro.</p>
        ) : (
          <div style={{ overflowX: "auto", border: `1px solid ${cores.borda}`, borderRadius: raio.md, background: cores.bgCartao }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "rgba(255,255,255,0.04)" }}>
                  {["Ficheiro", "Estado", "Linhas", "Data"].map((h) => (
                    <th key={h} style={{ padding: "9px 12px", fontSize: "0.62rem", letterSpacing: "0.06em", textTransform: "uppercase", color: cores.textoSuave, textAlign: "left" }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dados.uploads.map((u, i) => (
                  <tr key={i} style={{ borderTop: `1px solid ${cores.borda}` }}>
                    <td style={{ padding: "8px 12px", fontSize: "0.78rem", color: "rgba(255,255,255,0.85)" }}>{u.filename}</td>
                    <td style={{ padding: "8px 12px", fontSize: "0.78rem" }}>
                      <span
                        style={{
                          color: u.status === "done" ? cores.sucesso : u.status === "error" ? cores.perigo : cores.atencao,
                          fontWeight: 700,
                        }}
                      >
                        {u.status}
                      </span>
                    </td>
                    <td style={{ padding: "8px 12px", fontSize: "0.78rem", color: "rgba(255,255,255,0.7)" }}>{u.row_count ?? "—"}</td>
                    <td style={{ padding: "8px 12px", fontSize: "0.78rem", color: "rgba(255,255,255,0.7)" }}>
                      {u.criado_em ? new Date(u.criado_em).toLocaleString("pt-PT") : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function SecaoTitulo({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="font-display" style={{ fontSize: "1rem", fontWeight: 600, color: "white", margin: `0 0 ${espaco.md}px` }}>
      {children}
    </h2>
  );
}

function EstadoVazio({ mensagem }: { mensagem: string }) {
  return (
    <div style={{ maxWidth: 600, margin: "80px auto", padding: "0 24px", textAlign: "center" }}>
      <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.95rem" }}>{mensagem}</p>
    </div>
  );
}
