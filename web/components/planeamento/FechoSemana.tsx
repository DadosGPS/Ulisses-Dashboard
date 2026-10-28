"use client";

/** Fecho de semana para o treinador principal: poucas linhas, prontas a copiar
 * ou a enviar por WhatsApp. */
import { useEffect, useState } from "react";
import { cores, espaco } from "@/lib/theme";
import { Cartao, SecaoTitulo, Vazio, estiloBotao } from "@/components/ui/base";
import { pedidoApi } from "@/lib/api-cliente";
import { useTr } from "@/lib/i18n/cliente";

type Fecho = { microciclo: number | null; microciclos?: number[]; linhas: string[]; texto: string; motivo: string | null };

export function FechoSemana({ teamId }: { teamId: string }) {
  const tr = useTr();
  const [mc, setMc] = useState<number | null>(null);
  const [dados, setDados] = useState<Fecho | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [copiado, setCopiado] = useState(false);

  useEffect(() => {
    setErro(null);
    pedidoApi<Fecho>(`/api/teams/${teamId}/semana/fecho${mc != null ? `?microciclo=${mc}` : ""}`)
      .then(setDados).catch((e) => setErro(e.message));
  }, [teamId, mc]);

  async function copiar() {
    if (!dados?.texto) return;
    try {
      await navigator.clipboard.writeText(dados.texto);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      setErro(tr("Não foi possível copiar — seleciona o texto e copia à mão."));
    }
  }

  return (
    <section style={{ marginBottom: espaco.xxl }}>
      <SecaoTitulo
        subtitulo={tr("Resumo curto da semana para o treinador principal: carga, exposição, disponibilidade, decisões e o que muda na próxima.")}
        acoes={dados?.microciclos && dados.microciclos.length > 1 ? (
          <select aria-label={tr("Microciclo")} value={dados.microciclo ?? ""} onChange={(e) => setMc(Number(e.target.value))}
            style={{ fontSize: "0.8rem", padding: "4px 8px", borderRadius: 6, border: `1px solid ${cores.borda}`, background: cores.bgCartao, color: cores.texto }}>
            {[...dados.microciclos].reverse().map((m) => <option key={m} value={m}>{tr("Microciclo")} {m}</option>)}
          </select>
        ) : undefined}>
        {tr("Fecho de semana")}</SecaoTitulo>
      {erro ? <Vazio>{erro}</Vazio> : !dados ? <Vazio>{tr("A carregar…")}</Vazio> : !dados.linhas.length ? <Vazio>{tr(dados.motivo ?? "Sem dados.")}</Vazio> : (
        <Cartao>
          <ul style={{ margin: 0, paddingLeft: 18, display: "flex", flexDirection: "column", gap: 4, fontSize: "0.84rem", color: cores.texto, lineHeight: 1.45 }}>
            {dados.linhas.map((l, i) => <li key={i}>{l}</li>)}
          </ul>
          <div style={{ display: "flex", gap: espaco.sm, marginTop: espaco.md, flexWrap: "wrap" }}>
            <button onClick={copiar} style={estiloBotao.primario}>{copiado ? tr("Copiado") : tr("Copiar texto")}</button>
            <a href={`https://wa.me/?text=${encodeURIComponent(dados.texto)}`} target="_blank" rel="noopener noreferrer"
              style={{ ...estiloBotao.secundario, textDecoration: "none", display: "inline-flex", alignItems: "center" }}>{tr("Enviar por WhatsApp")}</a>
          </div>
        </Cartao>
      )}
    </section>
  );
}
