"use client";

/** Protocolo de limites da academia (Definições · Academia). Com ele ativo,
 * todas as equipas usam os mesmos limiares de alerta (com exceções por
 * escalão), e os avisos de equipas diferentes passam a ser comparáveis. */
import { useEffect, useState } from "react";
import { cores, espaco, raio } from "@/lib/theme";
import { Cartao, SecaoTitulo, estiloBotao } from "@/components/ui/base";
import { pedidoApi } from "@/lib/api-cliente";
import { useTr } from "@/lib/i18n/cliente";

type Protocolo = { ativo: boolean; base: Record<string, number>; escaloes: Record<string, Record<string, number>>; e_head: boolean };
type Estrutura = { disponivel: boolean; academias: { academia_id: string; nome: string; papel: string }[] };

export function ProtocoloAcademia() {
  const tr = useTr();
  const [academia, setAcademia] = useState<{ id: string; nome: string } | null>(null);
  const [prot, setProt] = useState<Protocolo | null>(null);
  const [aGuardar, setAGuardar] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    pedidoApi<Estrutura>("/api/academia").then((d) => {
      const a = d.academias?.[0];
      if (!d.disponivel || !a) return;
      setAcademia({ id: a.academia_id, nome: a.nome });
      pedidoApi<Protocolo>(`/api/academia/${a.academia_id}/protocolo`).then(setProt).catch(() => setProt(null));
    }).catch(() => {});
  }, []);

  if (!academia || !prot) return null;

  async function mudar(body: { ativo: boolean; limpar_escalao?: string }) {
    if (!academia) return;
    setAGuardar(true);
    setErro(null);
    try {
      setProt(await pedidoApi<Protocolo>(`/api/academia/${academia.id}/protocolo`, "PUT", body));
    } catch (e) {
      setErro(e instanceof Error ? e.message : tr("Não foi possível guardar."));
    } finally {
      setAGuardar(false);
    }
  }

  const excecoes = Object.entries(prot.escaloes).filter(([, v]) => Object.keys(v).length > 0);
  return (
    <section>
      <SecaoTitulo subtitulo={tr("Os mesmos limiares de alerta em todas as equipas da academia, para os avisos se poderem comparar entre escalões.")}>
        {tr("Protocolo de limites")}</SecaoTitulo>
      <Cartao>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: espaco.md, flexWrap: "wrap" }}>
          <div style={{ fontSize: "0.85rem", color: cores.texto }}>
            <strong>{prot.ativo ? tr("Ativo") : tr("Desligado")}</strong>
            {" · "}
            {prot.ativo ? tr("cada equipa usa a base da academia (ou a exceção do seu escalão); os limites pessoais deixam de contar.")
              : tr("cada preparador físico usa os seus próprios limites.")}
          </div>
          {prot.e_head && (
            <button disabled={aGuardar} onClick={() => mudar({ ativo: !prot.ativo })} style={prot.ativo ? estiloBotao.secundario : estiloBotao.primario}>
              {aGuardar ? tr("A guardar…") : prot.ativo ? tr("Desligar protocolo") : tr("Ativar com os meus limites atuais")}
            </button>
          )}
        </div>
        {prot.ativo && (
          <p style={{ margin: `${espaco.sm}px 0 0`, fontSize: "0.78rem", color: cores.textoSuave }}>
            {prot.e_head ? tr("Para mudar os valores, abre Definições · Limites numa equipa e escolhe «todas as equipas» ou «só este escalão».")
              : tr("Só o responsável da academia pode alterar o protocolo.")}
          </p>
        )}
        {prot.ativo && excecoes.length > 0 && (
          <div style={{ marginTop: espaco.md, display: "flex", flexWrap: "wrap", gap: 6 }}>
            {excecoes.map(([esc, v]) => (
              <span key={esc} style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "3px 9px", borderRadius: 999, border: `1px solid ${cores.borda}`, fontSize: "0.78rem", background: cores.superficie }}>
                {tr("{0}: exceção ({1} limiares)", [esc, Object.keys(v).length])}
                {prot.e_head && <button disabled={aGuardar} onClick={() => mudar({ ativo: true, limpar_escalao: esc })} style={{ ...estiloBotao.ligacao, fontSize: "0.74rem" }}>{tr("voltar à base")}</button>}
              </span>
            ))}
          </div>
        )}
        {erro && <p role="alert" style={{ margin: `${espaco.sm}px 0 0`, fontSize: "0.78rem", color: cores.perigo, borderRadius: raio.sm }}>{erro}</p>}
      </Cartao>
    </section>
  );
}
