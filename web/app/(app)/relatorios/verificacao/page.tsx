import Link from "next/link";
import { PageHeader } from "@/components/layout/PageHeader";
import { Cartao, EstadoVazio, SecaoTitulo } from "@/components/ui/base";
import { ListaProblemas, type Verificacao } from "@/components/relatorios/problemas";
import { FiltroNivel } from "@/components/relatorios/FiltroNivel";
import { contextoEquipa, getApi } from "@/lib/api-servidor";
import { obterTr } from "@/lib/i18n/servidor";
import type { Tr } from "@/lib/i18n/core";
import { cores, espaco, raio } from "@/lib/theme";

interface Registo {
  id: string; ficheiro: string | null; origem: string; bloqueou: boolean; criado_em: string;
  resumo: Verificacao["resumo"]; problemas: Verificacao["problemas"];
}
interface Resposta { disponivel: boolean; historico: Registo[]; dados_atuais: Verificacao }

const NIVEIS: Record<string, ("erro" | "aviso" | "info")[]> = {
  erros_avisos: ["erro", "aviso"], erros: ["erro"], avisos: ["aviso"], info: ["info"], todos: ["erro", "aviso", "info"],
};

export default async function VerificacaoPage({ searchParams }: { searchParams: Promise<{ nivel?: string; id?: string }> }) {
  const tr = await obterTr();
  const { nivel = "erros_avisos", id } = await searchParams;
  const ctx = await contextoEquipa();
  if (!ctx) return null;
  if (ctx === "sem_equipa") return <EstadoVazio mensagem={tr("Ainda não estás associado a nenhuma equipa.")} />;

  let r: Resposta;
  try {
    r = await getApi<Resposta>(`/api/teams/${ctx.teamId}/verificacao-dados`, ctx.token);
  } catch {
    return <EstadoVazio mensagem={tr("Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr.")} />;
  }

  const niveis = NIVEIS[nivel] ?? NIVEIS.erros_avisos;
  const ultima = r.historico.find((h) => h.id === id) ?? r.historico[0];
  const atual = r.dados_atuais;
  const okAtual = atual.resumo.erros === 0 && atual.resumo.avisos === 0;
  const okUltima = ultima && !ultima.bloqueou && ultima.resumo.erros === 0;
  const loc = tr.loc;

  return (
    <div>
      <PageHeader titulo={tr("Verificação de dados")}
        subtitulo={tr("Cada importação é verificada antes de gravar: os erros bloqueiam, os avisos ficam aqui para corrigires a origem (GPS, plantel, plano).")} />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px`, display: "flex", flexDirection: "column", gap: espaco.xl }}>

        {!r.disponivel && (
          <Cartao destaque={cores.atencao}>
            <p style={{ margin: 0, fontSize: "0.85rem" }}>{tr("O histórico de verificações precisa da migração supabase/migrations/0026_periodos_verificacao.sql (aplica-se sozinha no próximo deploy). A verificação dos dados atuais funciona já.")}</p>
          </Cartao>
        )}

        {/* Faixa de estado */}
        <div style={{ background: "#0f1115", borderRadius: raio.lg, padding: espaco.xl, color: "#e5e7eb" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: espaco.md }}>
            <div className="font-display" style={{ fontSize: "1.7rem", fontWeight: 700, color: okAtual && (okUltima ?? true) ? "#4ade80" : atual.resumo.erros || ultima?.bloqueou ? "#f87171" : "#fbbf24" }}>
              {okAtual && (okUltima ?? true) ? tr("Todas as verificações passaram") : atual.resumo.erros ? tr("Há valores impossíveis nos dados guardados") : ultima?.bloqueou ? tr("A última importação foi bloqueada") : tr("Dados válidos, com avisos")}
            </div>
            {ultima && <span style={{ fontSize: "0.78rem", color: "#9ca3af" }}>{tr("Última importação")}: {ultima.ficheiro ?? "—"} · {new Date(ultima.criado_em).toLocaleString(loc, { dateStyle: "short", timeStyle: "short" })}</span>}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: espaco.md, marginTop: espaco.lg }}>
            <Etapa n="1" titulo={tr("Ficheiro")} tr={tr}
              texto={ultima ? tr("{0} linhas · {1} jogadores", [ultima.resumo.linhas ?? "—", ultima.resumo.jogadores ?? "—"]) : tr("Ainda sem importações verificadas")} />
            <Etapa n="2" titulo={tr("Regras")} tr={tr}
              texto={ultima ? tr("{0} erros · {1} avisos · {2} info", [ultima.resumo.erros, ultima.resumo.avisos, ultima.resumo.info]) : "—"}
              cor={ultima ? (ultima.resumo.erros ? "#f87171" : "#4ade80") : undefined} />
            <Etapa n="3" titulo={tr("Recontagem")} tr={tr}
              texto={ultima?.resumo.recontagem
                ? tr("{0} sessões · {1} valores relidos da base de dados e iguais ao ficheiro", [ultima.resumo.recontagem.sessoes?.linhas ?? 0, (ultima.resumo.recontagem.sessoes?.valores ?? 0) + (ultima.resumo.recontagem.periodos?.valores ?? 0)])
                : ultima?.bloqueou ? tr("Não gravado — nada para recontar") : "—"}
              cor={ultima?.resumo.recontagem ? "#4ade80" : undefined} />
            <Etapa n="4" titulo={tr("Dados guardados")} tr={tr}
              texto={tr("{0} sessões · {1} erros · {2} avisos", [atual.resumo.linhas ?? 0, atual.resumo.erros, atual.resumo.avisos])}
              cor={atual.resumo.erros ? "#f87171" : "#4ade80"} />
          </div>
        </div>

        <Cartao>
          <SecaoTitulo acoes={<FiltroNivel atual={nivel} />}
            subtitulo={ultima ? `${ultima.ficheiro ?? "—"}${ultima.bloqueou ? ` · ${tr("bloqueada — nada foi gravado")}` : ""}` : undefined}>
            {tr("Problemas da importação")}
          </SecaoTitulo>
          <ListaProblemas problemas={(ultima?.problemas ?? []).filter((p) => niveis.includes(p.nivel))} tr={tr} vazio={tr("Nada para mostrar aqui.")} />
        </Cartao>

        <Cartao>
          <SecaoTitulo subtitulo={tr("As mesmas regras sobre tudo o que já está guardado (inclui dados importados antes de haver verificação).")}>{tr("Dados guardados da equipa")}</SecaoTitulo>
          <ListaProblemas problemas={atual.problemas.filter((p) => niveis.includes(p.nivel))} tr={tr} vazio={tr("Nenhum valor impossível ou suspeito nos dados guardados.")} />
        </Cartao>

        {r.historico.length > 0 && (
          <Cartao>
            <SecaoTitulo>{tr("Histórico")}</SecaoTitulo>
            <div style={{ display: "flex", flexDirection: "column" }}>
              {r.historico.map((h) => (
                <Link key={h.id} href={`/relatorios/verificacao?id=${h.id}&nivel=${nivel}`}
                  style={{ display: "flex", gap: espaco.md, alignItems: "center", padding: "8px 4px", borderBottom: `1px solid ${cores.borda}`, textDecoration: "none", color: cores.texto, fontSize: "0.83rem", background: h.id === ultima?.id ? cores.superficie : undefined }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: h.bloqueou || h.resumo.erros ? cores.perigo : h.resumo.avisos ? cores.atencao : cores.sucesso }} />
                  <span style={{ flex: 1, fontWeight: 600 }}>{h.ficheiro ?? "—"}</span>
                  <span style={{ color: cores.textoSuave }}>{h.bloqueou ? tr("bloqueada") : tr("{0} erros · {1} avisos", [h.resumo.erros, h.resumo.avisos])}</span>
                  <span style={{ color: cores.textoSuave, minWidth: 120, textAlign: "right" }}>{new Date(h.criado_em).toLocaleString(loc, { dateStyle: "short", timeStyle: "short" })}</span>
                </Link>
              ))}
            </div>
          </Cartao>
        )}
      </div>
    </div>
  );
}

function Etapa({ n, titulo, texto, cor }: { n: string; titulo: string; texto: string; cor?: string; tr: Tr }) {
  return (
    <div style={{ background: "#1a1d23", borderRadius: raio.md, padding: espaco.md }}>
      <div style={{ fontSize: "0.66rem", fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", color: "#f87171" }}>{n} · {titulo}</div>
      <div style={{ fontSize: "0.84rem", marginTop: 6, color: cor ?? "#e5e7eb", fontWeight: cor ? 600 : 400 }}>{texto}</div>
    </div>
  );
}
