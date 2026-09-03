import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { KpiCargaCard, type KpiCarga } from "@/components/ui/KpiCargaCard";
import { LoadProfileTable, type ColunaCarga, type LinhaCarga } from "@/components/ui/LoadProfileTable";
import { cores, espaco, raio } from "@/lib/theme";

interface MetricaDef { chave: string; label: string; unidade: string; cor: string; casas: number }

interface SessaoDetalhe {
  tem_dados: boolean;
  data?: string;
  tipo?: string;
  dia_md?: string;
  microciclo?: number | null;
  duracao_min?: number | null;
  n_jogadores?: number;
  n_equivalentes?: number;
  metricas?: MetricaDef[];
  kpis?: KpiCarga[];
  jogadores?: { jogador: string; posicao: string; valores: Record<string, number | null> }[];
}

async function obterSessao(teamId: string, accessToken: string, data: string, tipo?: string): Promise<SessaoDetalhe> {
  const url = new URL(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/sessao`);
  url.searchParams.set("data", data);
  if (tipo) url.searchParams.set("tipo", tipo);
  const res = await fetch(url, { headers: { Authorization: `Bearer ${accessToken}` }, cache: "no-store" });
  if (!res.ok) throw new Error(`Falha (${res.status}).`);
  return res.json();
}

export default async function SessaoDetalhePage({
  searchParams,
}: {
  searchParams: Promise<{ data?: string; tipo?: string }>;
}) {
  const { data, tipo } = await searchParams;

  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;

  const { data: membro } = await supabase.from("team_members").select("team_id").eq("user_id", session.user.id).limit(1).single();
  if (!membro) return <EstadoVazio mensagem="Ainda não estás associado a nenhuma equipa." />;
  if (!data) return <EstadoVazio mensagem="Sessão não indicada." />;

  let dados: SessaoDetalhe;
  try {
    dados = await obterSessao(membro.team_id, session.access_token, data, tipo);
  } catch {
    return <EstadoVazio mensagem="Não foi possível ligar à API." />;
  }

  if (!dados.tem_dados) {
    return (
      <div>
        <PageHeader titulo="Sessão" subtitulo="Detalhe da sessão" />
        <EstadoVazio mensagem="Sessão não encontrada." />
      </div>
    );
  }

  const dataLegivel = new Date(dados.data!).toLocaleDateString("pt-PT", { weekday: "long", day: "2-digit", month: "long", year: "numeric" });
  const colunas: ColunaCarga[] = (dados.metricas ?? []).map((m) => ({ chave: m.chave, label: m.label, cor: m.cor, casas: m.casas }));
  const linhas: LinhaCarga[] = (dados.jogadores ?? []).map((j) => ({ jogador: `${j.jogador}  ·  ${j.posicao}`, valores: j.valores }));

  return (
    <div>
      <PageHeader
        titulo={`${dados.tipo} · ${dados.dia_md}`}
        subtitulo={`${dataLegivel} · ${dados.n_jogadores} jogadores${dados.duracao_min ? ` · ${dados.duracao_min} min` : ""}${dados.microciclo ? ` · Semana ${dados.microciclo}` : ""}`}
        acoes={<Link href="/sessoes/lista" style={{ color: cores.destaque, fontSize: "0.82rem", fontWeight: 600, textDecoration: "none" }}>← Todas as sessões</Link>}
      />

      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        <SecaoTitulo>
          📊 Carga da sessão vs sessões equivalentes
          {dados.n_equivalentes! > 0 ? <span style={{ color: cores.textoSuave, fontWeight: 400 }}> · média de {dados.n_equivalentes} sessões {dados.tipo}{dados.dia_md !== "—" ? ` ${dados.dia_md}` : ""}</span> : null}
        </SecaoTitulo>
        {dados.n_equivalentes === 0 && (
          <p style={{ color: cores.textoSuave, fontSize: "0.78rem", margin: `0 0 ${espaco.md}px` }}>
            Ainda não há outras sessões deste tipo para comparar — mostra-se só o valor da sessão.
          </p>
        )}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: espaco.md, marginBottom: espaco.xxl }}>
          {(dados.kpis ?? []).map((k) => (
            <KpiCargaCard key={k.chave} kpi={k} compacto />
          ))}
        </div>

        <SecaoTitulo>🏃 Por Jogador</SecaoTitulo>
        <LoadProfileTable colunas={colunas} linhas={linhas} labelLinha="Jogador · Posição" />
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
