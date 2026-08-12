import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { PageHeader } from "@/components/layout/PageHeader";
import { KpiTile } from "@/components/ui/KpiTile";
import { LoadProfileTable } from "@/components/ui/LoadProfileTable";
import { MicrocicloSelector } from "@/components/ui/MicrocicloSelector";
import { DiaMdSelector } from "@/components/ui/DiaMdSelector";
import { alphaHex, cores, espaco, raio } from "@/lib/theme";
import type { AnaliseResponse } from "@/lib/types";

async function obterAnalise(
  teamId: string,
  accessToken: string,
  microciclo?: string,
  diaMd?: string
): Promise<AnaliseResponse> {
  const url = new URL(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/analise`);
  if (microciclo) url.searchParams.set("microciclo", microciclo);
  if (diaMd) url.searchParams.set("dia_md", diaMd);
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Falha ao carregar a análise (${res.status}).`);
  }
  return res.json();
}

export default async function AnalisePage({
  searchParams,
}: {
  searchParams: Promise<{ microciclo?: string; dia_md?: string }>;
}) {
  const { microciclo, dia_md } = await searchParams;

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

  if (!membro) {
    return <EstadoVazio mensagem="Ainda não estás associado a nenhuma equipa." />;
  }

  let dados: AnaliseResponse;
  try {
    dados = await obterAnalise(membro.team_id, session.access_token, microciclo, dia_md);
  } catch {
    return <EstadoVazio mensagem="Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr." />;
  }

  if (!dados.tem_dados) {
    return (
      <EstadoVazio mensagem="Ainda não há dados carregados para esta equipa.">
        <Link
          href="/upload"
          style={{
            display: "inline-block",
            marginTop: 16,
            padding: "10px 20px",
            background: cores.cargaInterna,
            borderRadius: 8,
            color: "white",
            fontWeight: 700,
            fontSize: "0.85rem",
            textDecoration: "none",
          }}
        >
          📤 Carregar dados
        </Link>
      </EstadoVazio>
    );
  }

  const cargaLabel = dados.dia_md_selecionado
    ? `média de ${dados.dia_md_selecionado}`
    : "carga semanal total média";

  return (
    <div>
      <PageHeader
        titulo="Análise"
        subtitulo={dados.microciclo_selecionado ? `Microciclo ${dados.microciclo_selecionado}` : undefined}
        acoes={
          <>
            <DiaMdSelector opcoes={dados.dias_md_disponiveis} atual={dados.dia_md_selecionado} />
            <MicrocicloSelector opcoes={dados.microciclos_disponiveis} atual={dados.microciclo_selecionado} />
          </>
        }
      />

      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px` }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: espaco.md, marginBottom: espaco.xxl }}>
          <KpiTile
            label="Carga Interna"
            valor={dados.carga_interna_media ?? "—"}
            unidade="UA"
            subLabel={cargaLabel}
            cor={cores.cargaInterna}
          />
          <KpiTile
            label="Carga Máxima"
            valor={dados.carga_maxima?.valor ?? "—"}
            unidade="UA"
            subLabel={dados.carga_maxima?.jogador ?? "—"}
            cor={cores.perigo}
          />
          <KpiTile
            label="Carga Mínima"
            valor={dados.carga_minima?.valor ?? "—"}
            unidade="UA"
            subLabel={dados.carga_minima?.jogador ?? "—"}
            cor={cores.info}
          />
          <KpiTile
            label="Monotonia / Strain"
            valor={dados.monotonia_media ?? "—"}
            unidade={dados.strain_medio ? `· Strain ${dados.strain_medio.toLocaleString("pt-PT")}` : ""}
            subLabel="médias da equipa · semana completa"
            cor={cores.destaque}
          />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: espaco.lg, marginBottom: espaco.xxl }}>
          <div>
            <SecaoTitulo>📊 Carga Média por Dia</SecaoTitulo>
            <TabelaPorDia linhas={dados.carga_por_dia.map((d) => ({ dia: d.dia_md, valor: d.carga_media }))} unidade="UA" cor={cores.cargaInterna} />
          </div>
          <div>
            <SecaoTitulo>🗣️ PSE Média por Dia</SecaoTitulo>
            <TabelaPorDia linhas={dados.pse_por_dia.map((d) => ({ dia: d.dia_md, valor: d.pse_media }))} unidade="/10" cor={cores.hsr} />
          </div>
        </div>

        <SecaoTitulo>🏆 Ranking de Atletas por Carga</SecaoTitulo>
        <LoadProfileTable
          colunas={[{ chave: "carga", label: cargaLabel, cor: cores.cargaInterna }]}
          linhas={dados.ranking_carga.map((r) => ({ jogador: r.jogador, valores: { carga: r.valor } }))}
        />
      </div>
    </div>
  );
}

function TabelaPorDia({ linhas, unidade, cor }: { linhas: { dia: string; valor: number }[]; unidade: string; cor: string }) {
  if (linhas.length === 0) return <SemDados />;
  const valores = linhas.map((l) => l.valor);
  const [lo, hi] = [Math.min(...valores), Math.max(...valores)];

  return (
    <div style={{ background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, padding: espaco.md, display: "flex", gap: espaco.sm, flexWrap: "wrap" }}>
      {linhas.map((l) => {
        const pct = hi > lo ? (l.valor - lo) / (hi - lo) : 0.5;
        return (
          <div key={l.dia} style={{ flex: "1 1 90px", textAlign: "center" }}>
            <div style={{ fontSize: "0.64rem", color: cores.textoSuave, marginBottom: 6, fontWeight: 600 }}>{l.dia}</div>
            <div
              style={{
                background: `${cor}${alphaHex(0.18 + pct * 0.55)}`,
                borderRadius: raio.sm,
                padding: "10px 6px",
                color: "white",
                fontWeight: 700,
                fontSize: "0.85rem",
              }}
            >
              {l.valor.toLocaleString("pt-PT")}
              <span style={{ fontSize: "0.6rem", fontWeight: 500, opacity: 0.8 }}> {unidade}</span>
            </div>
          </div>
        );
      })}
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

function SemDados() {
  return <p style={{ color: cores.textoSuave, fontSize: "0.85rem" }}>Sem dados suficientes.</p>;
}

function EstadoVazio({ mensagem, children }: { mensagem: string; children?: React.ReactNode }) {
  return (
    <div style={{ maxWidth: 600, margin: "80px auto", padding: "0 24px", textAlign: "center" }}>
      <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.95rem" }}>{mensagem}</p>
      {children}
    </div>
  );
}
