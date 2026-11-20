"use client";

import { useMemo, useState } from "react";
import { NomeJogador } from "@/components/ui/NomeJogador";
import { Cartao, estiloBotao } from "@/components/ui/base";
import { cores, espaco, estado, estiloTd, estiloTh, letra, peso, raio } from "@/lib/theme";
import type { VelocidadeJogador, VelocidadeResponse } from "@/lib/types";
import { useTr } from "@/lib/i18n/cliente";
import {
  FORMATOS_MAS, LIMIAR_GPS_HSR_KMH, MAS_VELHA_DIAS, MSS_VELHA_DIAS,
  agruparCorredores, calcularHsr, calcularMas, diasDesde,
} from "@/lib/hiit";

type Modo = "hsr" | "mas";

const fmt1 = (x: number) => x.toLocaleString("pt-PT", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

/** Fila de botões em pílula para escolher uma opção. */
function Pilulas<T extends string | number>({ titulo, opcoes, valor, onChange }: {
  titulo: string; opcoes: { v: T; label: string }[]; valor: T; onChange: (v: T) => void;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: espaco.sm }}>
      <span style={{ fontSize: letra.legenda, fontWeight: peso.medio, color: cores.textoSuave }}>{titulo}</span>
      <div role="radiogroup" aria-label={titulo} style={{ display: "flex", gap: espaco.xs, flexWrap: "wrap" }}>
        {opcoes.map((o) => {
          const ativo = o.v === valor;
          return (
            <button
              key={String(o.v)}
              type="button"
              role="radio"
              aria-checked={ativo}
              onClick={() => onChange(o.v)}
              style={{
                height: 32, padding: "0 12px", borderRadius: raio.pilula, cursor: "pointer",
                fontSize: letra.texto, fontWeight: peso.medio,
                border: `1px solid ${ativo ? cores.acento : cores.bordaForte}`,
                background: ativo ? cores.acento : cores.bgCartao,
                color: ativo ? cores.sobreAcento : cores.texto,
              }}
            >
              {o.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function Kpi({ titulo, valor, nota, cor }: { titulo: string; valor: React.ReactNode; nota: string; cor?: string }) {
  return (
    <Cartao padding={espaco.lg}>
      <div style={{ fontSize: letra.legenda, fontWeight: peso.medio, color: cores.textoSuave }}>{titulo}</div>
      <div style={{ fontSize: letra.numero, fontWeight: peso.forte, color: cor ?? cores.textoForte, margin: `${espaco.xs}px 0` }}>{valor}</div>
      <div style={{ fontSize: letra.legenda, color: cores.textoSuave }}>{nota}</div>
    </Cartao>
  );
}

export function CalculadoraHiit({ dados }: { dados: VelocidadeResponse }) {
  const tr = useTr();
  const [modo, setModo] = useState<Modo>("hsr");
  const [excluidos, setExcluidos] = useState<Set<string>>(new Set());
  // Modo HSR
  const [pctMss, setPctMss] = useState(75);
  const [tempo, setTempo] = useState(6);
  const [volume, setVolume] = useState(300);
  // Modo % MAS
  const [pctMas, setPctMas] = useState(110);
  const [formatoId, setFormatoId] = useState(FORMATOS_MAS[0].id);
  const [series, setSeries] = useState(2);
  const [minutos, setMinutos] = useState(6);

  const jogadores = useMemo(() => dados.jogadores.filter((j) => (j.mss_kmh ?? 0) > 0), [dados]);
  const ativos = jogadores.filter((j) => !excluidos.has(j.jogador));
  const alternar = (nome: string) =>
    setExcluidos((s) => { const n = new Set(s); if (n.has(nome)) n.delete(nome); else n.add(nome); return n; });

  if (!dados.tem_dados || jogadores.length === 0) {
    return (
      <Cartao>
        <p style={{ margin: 0, color: cores.textoSuave, fontSize: letra.texto }}>
          {tr("Ainda não há velocidade máxima registada. Importa sessões de GPS com a coluna de velocidade máxima.")}
        </p>
      </Cartao>
    );
  }

  const formato = FORMATOS_MAS.find((f) => f.id === formatoId) ?? FORMATOS_MAS[0];

  const linhasHsr = ativos.map((j) => {
    const c = calcularHsr(j.mss_kmh as number, pctMss, tempo, volume);
    const idadeMss = diasDesde(j.mss_data);
    const avisos: string[] = [];
    if (c.abaixoGps) avisos.push(tr("abaixo de {0} km/h: o GPS não conta como HSR", [fmt1(LIMIAR_GPS_HSR_KMH)]));
    if (idadeMss != null && idadeMss > MSS_VELHA_DIAS) avisos.push(tr("recorde de velocidade há {0} semanas", [Math.floor(idadeMss / 7)]));
    return { j, c, avisos };
  });

  const comMas = ativos.filter((j) => (j.mas_kmh ?? 0) > 0);
  const semMas = ativos.filter((j) => !((j.mas_kmh ?? 0) > 0));
  const linhasMas = comMas.map((j) => {
    const c = calcularMas(j.mas_kmh as number, j.mss_kmh, pctMas, formato, series, minutos);
    const idadeMas = diasDesde(j.mas_data);
    const avisos: string[] = [];
    if (idadeMas != null && idadeMas > MAS_VELHA_DIAS) avisos.push(tr("teste de 1 km há {0} semanas", [Math.floor(idadeMas / 7)]));
    if (c.pctMss != null && c.pctMss >= 85) avisos.push(tr("{0}% da Vmáx: já é trabalho de velocidade", [c.pctMss]));
    return { j, c, avisos };
  }).sort((a, b) => b.c.distM - a.c.distM);

  const corredores = modo === "hsr"
    ? agruparCorredores(linhasHsr, (l) => l.c.coneFinalM)
    : agruparCorredores(linhasMas, (l) => l.c.distM);

  const distsHsr = linhasHsr.map((l) => l.c.distM);
  const nAbaixo = linhasHsr.filter((l) => l.c.abaixoGps).length;
  const nVelhos = modo === "hsr"
    ? linhasHsr.filter((l) => (diasDesde(l.j.mss_data) ?? 0) > MSS_VELHA_DIAS).length
    : linhasMas.filter((l) => (diasDesde(l.j.mas_data) ?? 0) > MAS_VELHA_DIAS).length;

  const thDir: React.CSSProperties = { ...estiloTh, textAlign: "right" };
  const tdDir: React.CSSProperties = { ...estiloTd, textAlign: "right", fontVariantNumeric: "tabular-nums" };
  const corAviso = (n: number) => (n ? estado.vigiar : estado.ok);

  const celulaJogador = (j: VelocidadeJogador) => (
    <td style={{ ...estiloTd, fontWeight: peso.medio, color: cores.textoForte, whiteSpace: "nowrap" }}>
      <NomeJogador nome={j.jogador} ficha />
      <span style={{ fontWeight: peso.normal, color: cores.textoSuave }}> · {j.posicao}</span>
    </td>
  );
  const celulaAvisos = (avisos: string[]) => (
    <td style={{ ...estiloTd, fontSize: letra.pequeno, color: avisos.length ? estado.vigiar : estado.ok }}>
      {avisos.length ? avisos.join(" · ") : tr("ok")}
    </td>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: espaco.lg }}>
      <style>{`@media print { nav, aside, header, .nao-imprimir { display: none !important; } }`}</style>

      {/* Escolhas */}
      <Cartao>
        <div style={{ display: "flex", flexWrap: "wrap", gap: espaco.xl, alignItems: "flex-end" }}>
          <Pilulas<Modo> titulo={tr("Modo")} valor={modo} onChange={setModo}
            opcoes={[{ v: "hsr", label: tr("HSR individual") }, { v: "mas", label: tr("% MAS") }]} />
          {modo === "hsr" ? (
            <>
              <Pilulas titulo={tr("Velocidade alvo (% da Vmáx)")} valor={pctMss} onChange={setPctMss}
                opcoes={[70, 75, 80, 85].map((v) => ({ v, label: `${v}%` }))} />
              <Pilulas titulo={tr("Tempo em HSR por repetição")} valor={tempo} onChange={setTempo}
                opcoes={[4, 6, 8, 10].map((v) => ({ v, label: `${v} s` }))} />
              <Pilulas titulo={tr("Volume HSR alvo por jogador")} valor={volume} onChange={setVolume}
                opcoes={[200, 300, 400, 500].map((v) => ({ v, label: `${v} m` }))} />
            </>
          ) : (
            <>
              <Pilulas titulo={tr("Formato")} valor={formatoId} onChange={setFormatoId}
                opcoes={FORMATOS_MAS.map((f) => ({ v: f.id, label: tr(f.label) }))} />
              <Pilulas titulo={tr("Intensidade (% MAS)")} valor={pctMas} onChange={setPctMas}
                opcoes={[95, 100, 105, 110, 115, 120].map((v) => ({ v, label: `${v}%` }))} />
              <Pilulas titulo={tr("Séries")} valor={series} onChange={setSeries}
                opcoes={[1, 2, 3].map((v) => ({ v, label: String(v) }))} />
              <Pilulas titulo={tr("Minutos por série")} valor={minutos} onChange={setMinutos}
                opcoes={[4, 5, 6, 8].map((v) => ({ v, label: `${v} min` }))} />
            </>
          )}
          <button type="button" className="nao-imprimir" onClick={() => window.print()} style={{ ...estiloBotao.secundario, marginLeft: "auto" }}>
            {tr("Imprimir folha dos cones")}
          </button>
        </div>
      </Cartao>

      {/* Resumo */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: espaco.md }}>
        {modo === "hsr" ? (
          <>
            <Kpi titulo={tr("Distância em HSR por repetição")} valor={distsHsr.length ? `${Math.min(...distsHsr)}–${Math.max(...distsHsr)} m` : "—"}
              nota={tr("{0} s a {1}% da Vmáx de cada jogador", [tempo, pctMss])} />
            <Kpi titulo={tr("Corredores de cones")} valor={corredores.length} nota={tr("jogadores juntos de 5 em 5 m")} />
            <Kpi titulo={tr("Abaixo do limiar do GPS")} valor={nAbaixo} cor={corAviso(nAbaixo)}
              nota={tr("o GPS só conta HSR acima de {0} km/h", [fmt1(LIMIAR_GPS_HSR_KMH)])} />
            <Kpi titulo={tr("Vmáx desatualizada")} valor={nVelhos} cor={corAviso(nVelhos)}
              nota={tr("recorde com mais de {0} semanas", [MSS_VELHA_DIAS / 7])} />
          </>
        ) : (
          <>
            <Kpi titulo={tr("Repetições por série")} valor={linhasMas[0]?.c.repsPorSerie ?? "—"}
              nota={tr("{0} séries × {1} min · {2}", [series, minutos, tr(formato.label)])} />
            <Kpi titulo={tr("Corredores de cones")} valor={corredores.length} nota={tr("jogadores juntos de 5 em 5 m")} />
            <Kpi titulo={tr("Sem teste de 1 km")} valor={semMas.length} cor={corAviso(semMas.length)}
              nota={tr("sem MAS do último ano")} />
            <Kpi titulo={tr("Teste de 1 km antigo")} valor={nVelhos} cor={corAviso(nVelhos)}
              nota={tr("mais de {0} semanas: reteste recomendado", [Math.round(MAS_VELHA_DIAS / 7)])} />
          </>
        )}
      </div>

      {/* Corredores no campo */}
      <Cartao>
        <div style={{ fontSize: letra.realce, fontWeight: peso.forte, color: cores.textoForte, marginBottom: espaco.md }}>
          {tr("Corredores no campo")}
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: espaco.md }}>
          {corredores.map((c) => (
            <div key={c.distM} style={{ border: `1px solid ${cores.borda}`, borderRadius: raio.sm, padding: espaco.md }}>
              <div style={{ fontSize: letra.numero, fontWeight: peso.forte, color: cores.acento }}>{c.distM} m</div>
              <div style={{ fontSize: letra.legenda, color: cores.textoSuave, marginBottom: espaco.xs }}>
                {modo === "hsr" ? tr("cone final (arranque + HSR)") : tr("por repetição")}
              </div>
              <div style={{ fontSize: letra.pequeno, color: cores.texto, lineHeight: 1.6 }}>
                {c.itens.map((l) => l.j.jogador).join(" · ")}
              </div>
            </div>
          ))}
        </div>
      </Cartao>

      {/* Tabela por jogador */}
      <Cartao padding={0}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${cores.borda}` }}>
                <th style={estiloTh}>{tr("Jogador")}</th>
                {modo === "hsr" ? (
                  <>
                    <th style={thDir}>{tr("Vmáx")}</th>
                    <th style={thDir}>{tr("Velocidade alvo")}</th>
                    <th style={thDir}>{tr("Distância em HSR")}</th>
                    <th style={thDir}>{tr("Arranque antes")}</th>
                    <th style={thDir}>{tr("Cone final")}</th>
                    <th style={thDir}>{tr("Repetições")}</th>
                  </>
                ) : (
                  <>
                    <th style={thDir}>{tr("MAS")}</th>
                    <th style={thDir}>{tr("Velocidade alvo")}</th>
                    <th style={thDir}>{tr("Distância por repetição")}</th>
                    <th style={estiloTh}>{tr("Cones")}</th>
                    <th style={thDir}>{tr("% da Vmáx")}</th>
                    <th style={thDir}>{tr("Total")}</th>
                  </>
                )}
                <th style={estiloTh}>{tr("Avisos")}</th>
              </tr>
            </thead>
            <tbody>
              {modo === "hsr"
                ? linhasHsr.map(({ j, c, avisos }) => (
                  <tr key={j.jogador} style={{ borderBottom: `1px solid ${cores.borda}` }}>
                    {celulaJogador(j)}
                    <td style={tdDir}>{fmt1(j.mss_kmh as number)} km/h</td>
                    <td style={tdDir}>{fmt1(c.velKmh)} km/h</td>
                    <td style={{ ...tdDir, fontWeight: peso.forte, color: cores.acento }}>{c.distM} m</td>
                    <td style={tdDir}>~{c.arranqueM} m</td>
                    <td style={{ ...tdDir, fontWeight: peso.medio, color: cores.textoForte }}>{c.coneFinalM} m</td>
                    <td style={tdDir}>{c.reps}</td>
                    {celulaAvisos(avisos)}
                  </tr>
                ))
                : linhasMas.map(({ j, c, avisos }) => (
                  <tr key={j.jogador} style={{ borderBottom: `1px solid ${cores.borda}` }}>
                    {celulaJogador(j)}
                    <td style={tdDir}>{fmt1(j.mas_kmh as number)} km/h</td>
                    <td style={tdDir}>{fmt1(c.velKmh)} km/h</td>
                    <td style={{ ...tdDir, fontWeight: peso.forte, color: cores.acento }}>{c.distM} m</td>
                    <td style={estiloTd}>{c.cones}</td>
                    <td style={tdDir}>{c.pctMss != null ? `${c.pctMss}%` : "—"}</td>
                    <td style={tdDir}>{c.totalM.toLocaleString("pt-PT")} m</td>
                    {celulaAvisos(avisos)}
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
        {modo === "mas" && semMas.length > 0 && (
          <div style={{ padding: espaco.md, borderTop: `1px solid ${cores.borda}`, fontSize: letra.pequeno, color: cores.textoSuave }}>
            {tr("Sem teste de 1 km (não entram no cálculo):")} {semMas.map((j) => j.jogador).join(" · ")}
          </div>
        )}
      </Cartao>

      {/* Quem participa */}
      <Cartao>
        <div className="nao-imprimir">
          <div style={{ fontSize: letra.legenda, fontWeight: peso.medio, color: cores.textoSuave, marginBottom: espaco.sm }}>
            {tr("Quem faz o exercício (clica para tirar ou voltar a pôr)")}
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: espaco.xs }}>
            {jogadores.map((j) => {
              const fora = excluidos.has(j.jogador);
              return (
                <button key={j.jogador} type="button" onClick={() => alternar(j.jogador)} aria-pressed={!fora}
                  style={{
                    padding: "4px 10px", borderRadius: raio.pilula, cursor: "pointer", fontSize: letra.pequeno,
                    border: `1px solid ${fora ? cores.borda : cores.bordaForte}`,
                    background: fora ? "transparent" : cores.superficie,
                    color: fora ? cores.textoFraco : cores.texto,
                    textDecoration: fora ? "line-through" : "none",
                  }}>
                  {j.jogador}
                </button>
              );
            })}
          </div>
        </div>
      </Cartao>

      {/* Notas */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: espaco.md }}>
        <Cartao destaque={cores.info}>
          <div style={{ fontSize: letra.pequeno, lineHeight: 1.6, color: cores.texto }}>
            {modo === "hsr"
              ? tr("Cada jogador corre à sua velocidade alvo durante o tempo escolhido, entre o cone do arranque e o cone final. O arranque é uma estimativa para chegar a essa velocidade sem acelerar ao máximo. A Vmáx é o recorde do GPS (página Velocidade).")
              : tr("A MAS vem do teste de 1 km da academia (1000 m ÷ tempo). O teste é curto e tende a sobrestimar a MAS, por isso confirma pela PSE e pelo GPS da 1.ª série. No vaivém, cada mudança de direção desconta ~0,7 s.")}
          </div>
        </Cartao>
        <Cartao destaque={cores.atencao}>
          <div style={{ fontSize: letra.pequeno, lineHeight: 1.6, color: cores.texto }}>
            {tr("O GPS conta os metros de HSR num limiar fixo de {0} km/h. Quem corre abaixo disso faz o trabalho certo para si, mas aparece com pouco HSR nos dados da sessão.", [fmt1(LIMIAR_GPS_HSR_KMH)])}
          </div>
        </Cartao>
      </div>
    </div>
  );
}
