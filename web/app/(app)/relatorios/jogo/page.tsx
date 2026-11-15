import Link from "next/link";
import { PageHeader } from "@/components/layout/PageHeader";
import { Cartao, EstadoVazio, SecaoTitulo } from "@/components/ui/base";
import { NomeJogador } from "@/components/ui/NomeJogador";
import { BotaoImprimir, SeletorSessao } from "@/components/relatorios/Seletores";
import {
  COR, COR_ESTADO, Kpi, dataCurta, fmt, fmtPct, nota, tabela, td, tdEsq, th, thEsq, type Estado, type MetricaDesc,
} from "@/components/relatorios/comum";
import { contextoEquipa, getApi } from "@/lib/api-servidor";
import { obterTr } from "@/lib/i18n/servidor";
import type { Tr } from "@/lib/i18n/core";
import { cores, espaco } from "@/lib/theme";

interface ValorJ { valor: number | null; por_min: number | null; media_epoca_min: number | null; media_epoca: number | null; estado: Estado; delta_pct: number | null }
interface LinhaJ { jogador: string; posicao: string; minutos: number | null; n_jogos_epoca: number; dist_min: number | null; valores: Record<string, ValorJ> }
interface Partes {
  nomes: string[]; n_ambas: number; variacao_pct: Record<string, number | null>;
  equipa: ({ periodo: string; n_jogadores: number; minutos_medios: number | null; vmax?: number | null } & Record<string, number | string | null | undefined>)[];
  por_jogador: ({ jogador: string; periodo: string; minutos: number | null } & Record<string, number | string | null>)[];
}
interface Individual {
  jogador: string; posicao: string; minutos_medios: number | null; n_validos: number;
  jogos: { data: string; adversario: string | null; minutos: number | null; atual: boolean; valores: Record<string, { valor: number | null; estado: Estado }> }[];
  media_epoca: Record<string, number | null>; recordes: Record<string, { valor: number | null; data: string; adversario: string | null }>;
}
interface Relatorio {
  tem_dados: boolean; jogos: { data: string; adversario: string | null }[];
  data?: string; adversario?: string | null; duracao_min?: number | null; duracao_ref?: number | null; minimo_completo?: number | null;
  n_completos?: number; n_jogos_epoca?: number; min_minutos_hist?: number;
  metricas?: MetricaDesc[]; kpis?: { chave: string; valor: number | null; media_epoca: number | null; delta_pct: number | null }[];
  jogadores?: LinhaJ[]; posicoes?: ({ posicao: string } & Record<string, { jogo: number | null; epoca: number | null; delta_pct: number | null } | string>)[];
  partes?: Partes | null; individual?: Individual | null;
}

const RAIZ = "/relatorios/jogo";

export default async function RelatorioJogoPage({ searchParams }: { searchParams: Promise<{ data?: string; jogador?: string }> }) {
  const tr = await obterTr();
  const loc = tr.loc;
  const { data, jogador } = await searchParams;
  const ctx = await contextoEquipa();
  if (!ctx) return null;
  if (ctx === "sem_equipa") return <EstadoVazio mensagem={tr("Ainda não estás associado a nenhuma equipa.")} />;

  let r: Relatorio;
  try {
    r = await getApi<Relatorio>(`/api/teams/${ctx.teamId}/relatorios/jogo`, ctx.token, { data, jogador });
  } catch {
    return <EstadoVazio mensagem={tr("Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr.")} />;
  }
  if (!r.tem_dados || !r.data) {
    return <EstadoVazio acao={{ href: "/upload", label: tr("Importar GPS") }} mensagem={tr("Ainda não há jogos com dados de GPS para esta equipa.")} />;
  }

  const metricas = r.metricas ?? [];
  const opcoes = r.jogos.map((j) => ({ valor: j.data, texto: `${dataCurta(j.data, loc)}${j.adversario ? ` · ${j.adversario}` : ""}` }));
  const ligacao = (j?: string) => `${RAIZ}?data=${r.data}${j ? `&jogador=${encodeURIComponent(j)}` : ""}`;

  return (
    <div>
      <PageHeader
        titulo={r.adversario ? tr("Jogo · vs {0}", [r.adversario]) : tr("Relatório de jogo")}
        subtitulo={`${dataCurta(r.data, loc)} · ${tr("{0} min", [fmt(r.duracao_min, 0, loc)])} · ${tr("{0} jogos anteriores na época", [r.n_jogos_epoca ?? 0])}`}
        acoes={<><SeletorSessao opcoes={opcoes} atual={r.data} rotulo="Jogo" /><BotaoImprimir /></>}
      />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px`, display: "flex", flexDirection: "column", gap: espaco.xl }}>

        {/* KPIs de equipa */}
        <div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: espaco.md }}>
            {metricas.map((m) => {
              const k = r.kpis?.find((x) => x.chave === m.chave);
              const d = k?.delta_pct ?? null;
              return (
                <Kpi key={m.chave} rotulo={tr(m.label)} valor={fmt(k?.valor, m.casas, loc)} unidade={m.unidade}
                  rodape={d === null ? tr("sem jogos anteriores") : <span style={{ color: Math.abs(d) < 5 ? cores.textoSuave : cores.texto, fontWeight: 600 }}>{Math.abs(d) >= 5 ? (d > 0 ? "▲ " : "▼ ") : ""}{fmtPct(d, loc)} {tr("vs época")}</span>} />
              );
            })}
          </div>
          <p style={nota}>{tr("Média dos {0} jogadores com pelo menos {1} min (75 % do jogo), face à mesma média nos outros jogos da época.", [r.n_completos ?? 0, fmt(r.minimo_completo, 0, loc)])}</p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: espaco.lg }}>
          {/* 1.ª vs 2.ª parte */}
          <Cartao>
            <SecaoTitulo subtitulo={r.partes ? tr("Por minuto, só jogadores que jogaram as duas partes ({0}).", [r.partes.n_ambas]) : undefined}>{tr("1.ª parte vs 2.ª parte")}</SecaoTitulo>
            {r.partes && r.partes.equipa.length >= 2 ? <Partes p={r.partes} metricas={metricas} loc={loc} tr={tr} /> : (
              <p style={{ fontSize: "0.84rem", color: cores.textoSuave, margin: 0 }}>
                {tr("Sem dados por parte para este jogo. Importa o export do jogo por períodos (1st half / 2nd half) e mapeia a coluna do período para «Período».")}{" "}
                <Link href="/upload" style={{ color: cores.acento }}>{tr("Importar GPS")}</Link>
              </p>
            )}
          </Cartao>

          {/* Perfil por posição */}
          <Cartao>
            <SecaoTitulo subtitulo={tr("Por jogo completo ({0} min): ritmo por minuto × duração do jogo, jogadores com ≥ {1} min.", [fmt(r.duracao_ref, 0, loc), r.min_minutos_hist ?? 30])}>{tr("Perfil por posição")}</SecaoTitulo>
            {(r.posicoes ?? []).length === 0 ? <p style={{ fontSize: "0.84rem", color: cores.textoSuave, margin: 0 }}>{tr("Sem posições definidas nos jogadores.")}</p> : (
              <table style={tabela}>
                <thead><tr><th style={thEsq}>{tr("Posição")}</th><th style={th}>{tr("Distância")}</th><th style={th}>HSR</th><th style={th}>{tr("Sprint")}</th></tr></thead>
                <tbody>
                  {(r.posicoes ?? []).map((p) => (
                    <tr key={p.posicao}>
                      <td style={{ ...tdEsq, fontWeight: 600 }}>{p.posicao}</td>
                      {(["distancia", "hsr", "sprint"] as const).map((k) => {
                        const v = p[k] as { jogo: number | null; epoca: number | null; delta_pct: number | null } | undefined;
                        return (
                          <td key={k} style={td} title={v ? tr("Época: {0}", [fmt(v.epoca, 0, loc)]) : undefined}>
                            {fmt(v?.jogo, 0, loc)} <span style={{ fontSize: "0.72rem", color: v?.delta_pct == null || Math.abs(v.delta_pct) < 5 ? cores.textoSuave : v.delta_pct > 0 ? cores.sucesso : cores.perigo }}>{fmtPct(v?.delta_pct, loc)}</span>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Cartao>
        </div>

        {/* Plantel */}
        <Cartao>
          <SecaoTitulo
            subtitulo={tr("Totais do jogo. A cor compara o ritmo por minuto com os jogos da própria época (≥ {0} min): verde = acima de +1 DP, vermelho = abaixo de −1 DP. A velocidade máxima compara-se em bruto. Clica num jogador para o relatório individual.", [r.min_minutos_hist ?? 30])}
            acoes={<Legenda tr={tr} />}
          >{tr("Plantel")}</SecaoTitulo>
          <div style={{ overflowX: "auto" }}>
            <table style={{ ...tabela, minWidth: 820 }}>
              <thead>
                <tr>
                  <th style={thEsq}>{tr("Jogador")}</th><th style={th}>{tr("Min")}</th>
                  {metricas.map((m) => <th key={m.chave} style={{ ...th, color: COR[m.chave] }}>{tr(m.label)}</th>)}
                  <th style={th}>{tr("m/min")}</th><th style={th}>{tr("Jogos")}</th>
                </tr>
              </thead>
              <tbody>
                {(r.jogadores ?? []).map((j) => (
                  <tr key={j.jogador} style={{ background: r.individual?.jogador === j.jogador ? cores.superficie : undefined }}>
                    <td style={tdEsq}>
                      <Link href={ligacao(j.jogador)} style={{ fontWeight: 600, color: cores.textoForte, textDecoration: "none" }}><NomeJogador nome={j.jogador} /></Link>
                      <span style={{ color: cores.textoSuave, fontSize: "0.72rem", marginLeft: 6 }}>{j.posicao}</span>
                    </td>
                    <td style={td}>{fmt(j.minutos, 0, loc)}</td>
                    {metricas.map((m) => {
                      const v = j.valores[m.chave];
                      return <CelulaEstado key={m.chave} estado={v?.estado} texto={fmt(v?.valor, m.casas, loc)}
                        title={v?.media_epoca_min != null ? tr("{0}/min vs {1}/min na época", [fmt(v.por_min, 2, loc), fmt(v.media_epoca_min, 2, loc)]) : v?.media_epoca != null ? tr("Época: {0}", [fmt(v.media_epoca, 1, loc)]) : undefined} />;
                    })}
                    <td style={td}>{fmt(j.dist_min, 0, loc)}</td>
                    <td style={{ ...td, color: cores.textoSuave }}>{j.n_jogos_epoca}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Cartao>

        {r.individual && <BlocoIndividual ind={r.individual} metricas={metricas} partes={r.partes ?? null} loc={loc} tr={tr} fechar={ligacao()} />}
      </div>
    </div>
  );
}

function CelulaEstado({ estado, texto, title }: { estado?: Estado; texto: string; title?: string }) {
  const cor = estado === "alto" ? cores.sucesso : estado === "baixo" ? cores.perigo : null;
  return <td title={title} style={{ ...td, background: cor ? `color-mix(in srgb, ${cor} 14%, transparent)` : undefined, fontWeight: cor ? 650 : 400 }}>{texto}</td>;
}

function Legenda({ tr }: { tr: Tr }) {
  const item = (cor: string, t: string) => (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}><span style={{ width: 9, height: 9, borderRadius: 3, background: `color-mix(in srgb, ${cor} 35%, transparent)` }} />{t}</span>
  );
  return <div style={{ display: "flex", gap: espaco.md, fontSize: "0.72rem", color: cores.textoSuave }}>{item(cores.sucesso, tr("Acima +1 DP"))}{item(cores.textoSuave, tr("Típico"))}{item(cores.perigo, tr("Abaixo −1 DP"))}</div>;
}

function Partes({ p, metricas, loc, tr }: { p: Partes; metricas: MetricaDesc[]; loc: string; tr: Tr }) {
  const linhas = metricas.filter((m) => m.chave !== "vmax").map((m) => ({ ...m, k: `${m.chave}_min`, rot: tr("{0}/min", [tr(m.label)]) }));
  const vm = metricas.find((m) => m.chave === "vmax");
  const todas = [...linhas, ...(vm ? [{ ...vm, k: "vmax", rot: tr("Vel. máx. média") }] : [])];
  const [a, b] = p.equipa;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {todas.map((m) => {
        const va = (a[m.k] as number | null) ?? null, vb = (b[m.k] as number | null) ?? null;
        const max = Math.max(va ?? 0, vb ?? 0) || 1;
        const d = p.variacao_pct[m.chave] ?? null;
        return (
          <div key={m.k} style={{ display: "grid", gridTemplateColumns: "110px 1fr 56px", alignItems: "center", gap: 10, fontSize: "0.78rem" }}>
            <span style={{ color: cores.textoSuave }}>{m.rot}</span>
            <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
              {[[va, cores.textoForte], [vb, cores.perigo]].map(([v, cor], i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <div style={{ height: 7, width: `${((v as number | null) ?? 0) / max * 100}%`, background: cor as string, borderRadius: 4, minWidth: 2 }} />
                  <span style={{ fontSize: "0.7rem", color: cores.textoSuave }}>{fmt(v as number | null, m.chave === "distancia" ? 0 : m.chave === "vmax" ? 1 : 2, loc)}</span>
                </div>
              ))}
            </div>
            <span style={{ textAlign: "right", fontWeight: 650, color: d === null || Math.abs(d) < 5 ? cores.textoSuave : d > 0 ? cores.sucesso : cores.atencao }}>{fmtPct(d, loc)}</span>
          </div>
        );
      })}
      <div style={{ display: "flex", gap: espaco.md, fontSize: "0.72rem", color: cores.textoSuave, marginTop: 4 }}>
        <span><span style={{ display: "inline-block", width: 9, height: 9, background: cores.textoForte, borderRadius: 2, marginRight: 4 }} />{a.periodo}</span>
        <span><span style={{ display: "inline-block", width: 9, height: 9, background: cores.perigo, borderRadius: 2, marginRight: 4 }} />{b.periodo}</span>
        <span style={{ marginLeft: "auto" }}>{tr("% = variação na 2.ª parte")}</span>
      </div>
    </div>
  );
}

function BlocoIndividual({ ind, metricas, partes, loc, tr, fechar }: { ind: Individual; metricas: MetricaDesc[]; partes: Partes | null; loc: string; tr: Tr; fechar: string }) {
  const minhas = partes?.por_jogador.filter((x) => x.jogador === ind.jogador) ?? [];
  const COR_EST: Record<Estado, string | null> = { alto: COR_ESTADO.alto, baixo: COR_ESTADO.baixo, normal: null, insuficiente: null };
  return (
    <Cartao destaque={cores.acento}>
      <SecaoTitulo
        subtitulo={tr("{0} · {1} jogos com ≥ 30 min · {2} min por jogo em média", [ind.posicao, ind.n_validos, fmt(ind.minutos_medios, 0, loc)])}
        acoes={<Link href={fechar} style={{ fontSize: "0.8rem", color: cores.acento }}>{tr("Fechar")}</Link>}
      ><NomeJogador nome={ind.jogador} /></SecaoTitulo>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: espaco.md, marginBottom: espaco.lg }}>
        {metricas.map((m) => {
          const rec = ind.recordes[m.chave];
          return <Kpi key={m.chave} rotulo={tr("Recorde · {0}", [tr(m.label)])} valor={fmt(rec?.valor, m.casas, loc)} unidade={m.unidade}
            rodape={rec ? `${dataCurta(rec.data, loc)}${rec.adversario ? ` · ${rec.adversario}` : ""}` : undefined} />;
        })}
      </div>

      {minhas.length > 0 && (
        <div style={{ marginBottom: espaco.lg }}>
          <SecaoTitulo margem={espaco.sm}>{tr("Por parte")}</SecaoTitulo>
          <table style={tabela}>
            <thead><tr><th style={thEsq}>{tr("Período")}</th><th style={th}>{tr("Min")}</th>{metricas.map((m) => <th key={m.chave} style={th}>{tr(m.label)}</th>)}</tr></thead>
            <tbody>
              {minhas.map((x) => (
                <tr key={x.periodo}><td style={tdEsq}>{x.periodo}</td><td style={td}>{fmt(x.minutos, 0, loc)}</td>
                  {metricas.map((m) => <td key={m.chave} style={td}>{fmt(x[m.chave] as number | null, m.casas, loc)}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <SecaoTitulo margem={espaco.sm} subtitulo={tr("Cor = ritmo por minuto face aos outros jogos dele (≥ 30 min).")}>{tr("Jogo a jogo")}</SecaoTitulo>
      <div style={{ overflowX: "auto" }}>
        <table style={{ ...tabela, minWidth: 720 }}>
          <thead><tr><th style={thEsq}>{tr("Jogo")}</th><th style={th}>{tr("Min")}</th>{metricas.map((m) => <th key={m.chave} style={th}>{tr(m.label)}</th>)}</tr></thead>
          <tbody>
            {ind.jogos.map((g) => (
              <tr key={g.data} style={{ background: g.atual ? cores.superficie : undefined }}>
                <td style={{ ...tdEsq, fontWeight: g.atual ? 700 : 500 }}>{dataCurta(g.data, loc)}{g.adversario ? ` · ${g.adversario}` : ""}</td>
                <td style={td}>{fmt(g.minutos, 0, loc)}</td>
                {metricas.map((m) => {
                  const v = g.valores[m.chave];
                  const cor = v ? COR_EST[v.estado] : null;
                  return <td key={m.chave} style={{ ...td, background: cor ? `color-mix(in srgb, ${cor} 14%, transparent)` : undefined }}>{fmt(v?.valor, m.casas, loc)}</td>;
                })}
              </tr>
            ))}
            <tr>
              <td style={{ ...tdEsq, fontWeight: 700 }}>{tr("Média da época")}</td><td style={td}>{fmt(ind.minutos_medios, 0, loc)}</td>
              {metricas.map((m) => <td key={m.chave} style={{ ...td, fontWeight: 700 }}>{fmt(ind.media_epoca[m.chave], m.casas, loc)}</td>)}
            </tr>
          </tbody>
        </table>
      </div>
    </Cartao>
  );
}
