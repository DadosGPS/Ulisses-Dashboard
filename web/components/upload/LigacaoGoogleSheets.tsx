"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { pedidoApi } from "@/lib/api-cliente";
import { cores, espaco, raio } from "@/lib/theme";
import { useTr } from "@/lib/i18n/cliente";
import { Cartao, Etiqueta, estiloBotao } from "@/components/ui/base";

interface Resultado {
  ok: boolean;
  erro?: string;
  sessoes?: number;
  jogadores?: number;
  dias?: number;
  intervalo?: [string, string] | null;
  dias_pse_esperada?: number;
  ignoradas?: { antes_inicio: number; sem_pse: number; pse_invalida: number };
}
interface Fonte {
  spreadsheet_id: string;
  url: string;
  folha: string;
  data_inicio: string;
  filtro_equipa: string | null;
  ativo: boolean;
  ultima_sincronizacao: string | null;
  ultimo_resultado: Resultado | null;
}
interface Config {
  disponivel: boolean;
  email_conta_servico: string | null;
  fonte: Fonte | null;
}

const campo: React.CSSProperties = {
  background: cores.bgCartao, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.sm, color: cores.textoForte,
  fontSize: "0.84rem", padding: "6px 8px", height: 34, width: "100%", boxSizing: "border-box",
};

function Campo({ rotulo, children, largura }: { rotulo: string; children: React.ReactNode; largura?: number }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: "0.72rem", color: cores.textoSuave, fontWeight: 500, flex: largura ? `0 0 ${largura}px` : 1, minWidth: 0 }}>
      {rotulo}
      {children}
    </label>
  );
}

const dataPt = (iso: string) => iso.split("-").reverse().join("/");

/** Liga a equipa a uma folha do Google Sheets com a PSE dos jogadores (ex.:
 * «P15 - RPE»): importa a PSE real e a PSE esperada a partir de uma data. */
export function LigacaoGoogleSheets({ teamId }: { teamId: string }) {
  const tr = useTr();
  const [config, setConfig] = useState<Config | null>(null);
  const [editar, setEditar] = useState(false);
  const [form, setForm] = useState({ url: "", folha: "RPE", data_inicio: "", filtro_equipa: "" });
  const [ocupado, setOcupado] = useState<"guardar" | "sincronizar" | "remover" | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  async function carregar() {
    try {
      const c = await pedidoApi<Config>(`/api/teams/${teamId}/google-sheets`);
      setConfig(c);
      if (c.fonte) {
        setForm({ url: c.fonte.url, folha: c.fonte.folha, data_inicio: c.fonte.data_inicio, filtro_equipa: c.fonte.filtro_equipa ?? "" });
      }
      setEditar(!c.fonte);
    } catch (e) {
      setErro((e as Error).message);
    }
  }

  useEffect(() => { carregar(); }, [teamId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function guardar() {
    setErro(null);
    if (!form.url.trim() || !form.data_inicio) {
      setErro(tr("Indica o link da folha e a data a partir da qual importar."));
      return;
    }
    setOcupado("guardar");
    try {
      await pedidoApi(`/api/teams/${teamId}/google-sheets`, "PUT", { ...form, filtro_equipa: form.filtro_equipa || null });
      await carregar();
      await sincronizar();
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setOcupado(null);
    }
  }

  async function sincronizar() {
    setErro(null);
    setOcupado("sincronizar");
    try {
      await pedidoApi(`/api/teams/${teamId}/google-sheets/sincronizar`, "POST");
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setOcupado(null);
      await carregar();
    }
  }

  async function remover() {
    if (!window.confirm(tr("Desligar esta folha? Os dados já importados ficam na app."))) return;
    setOcupado("remover");
    try {
      await pedidoApi(`/api/teams/${teamId}/google-sheets`, "DELETE");
      setForm({ url: "", folha: "RPE", data_inicio: "", filtro_equipa: "" });
      await carregar();
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setOcupado(null);
    }
  }

  if (!config) return null;
  if (!config.disponivel) {
    return (
      <Cartao style={{ marginBottom: espaco.xl }}>
        <p style={{ margin: 0, fontSize: "0.82rem", color: cores.textoSuave }}>
          {tr("A ligação ao Google Sheets fica disponível depois de aplicada a migração 0028 (no próximo deploy).")}
        </p>
      </Cartao>
    );
  }

  const fonte = config.fonte;
  const r = fonte?.ultimo_resultado;

  return (
    <Cartao style={{ marginBottom: espaco.xl }} destaque={r ? (r.ok ? cores.sucesso : cores.perigo) : undefined}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: espaco.sm, marginBottom: espaco.sm }}>
        <div style={{ fontWeight: 600, color: cores.textoForte, fontSize: "0.95rem" }}>{tr("PSE do Google Sheets")}</div>
        {fonte && !editar && (
          <div style={{ display: "flex", gap: espaco.sm }}>
            <button style={estiloBotao.primario} onClick={sincronizar} disabled={ocupado !== null}>
              {ocupado === "sincronizar" ? tr("A importar…") : tr("Importar agora")}
            </button>
            <button style={estiloBotao.secundario} onClick={() => setEditar(true)} disabled={ocupado !== null}>{tr("Alterar")}</button>
          </div>
        )}
      </div>
      <p style={{ margin: `0 0 ${espaco.md}px`, fontSize: "0.8rem", color: cores.textoSuave, lineHeight: 1.5 }}>
        {tr("Lê a folha de PSE da equipa técnica (colunas DATE, NAME, DURATION, RPE, expected RPE…) e grava a PSE de cada jogador e a PSE esperada de cada dia. A app volta a ler a folha de hora a hora.")}
      </p>

      {config.email_conta_servico ? (
        <div style={{ background: cores.superficie, borderRadius: raio.sm, padding: `${espaco.sm}px ${espaco.md}px`, fontSize: "0.78rem", color: cores.texto, marginBottom: espaco.md }}>
          {tr("Partilha a folha (Partilhar → Leitor) com:")}{" "}
          <code style={{ userSelect: "all", color: cores.textoForte }}>{config.email_conta_servico}</code>
        </div>
      ) : (
        <div style={{ background: cores.superficie, borderRadius: raio.sm, padding: `${espaco.sm}px ${espaco.md}px`, fontSize: "0.78rem", color: cores.atencao, marginBottom: espaco.md }}>
          {tr("A API ainda não tem conta de serviço Google (GOOGLE_SERVICE_ACCOUNT_JSON). Sem ela só dá para ler folhas partilhadas com «qualquer pessoa com o link».")}
        </div>
      )}

      {editar ? (
        <div style={{ display: "flex", flexDirection: "column", gap: espaco.md }}>
          <Campo rotulo={tr("Link da folha")}>
            <input style={campo} value={form.url} placeholder="https://docs.google.com/spreadsheets/d/…" onChange={(e) => setForm({ ...form, url: e.target.value })} />
          </Campo>
          <div style={{ display: "flex", gap: espaco.md, flexWrap: "wrap" }}>
            <Campo rotulo={tr("Separador")} largura={140}>
              <input style={campo} value={form.folha} onChange={(e) => setForm({ ...form, folha: e.target.value })} />
            </Campo>
            <Campo rotulo={tr("Importar a partir de")} largura={170}>
              <input type="date" style={campo} value={form.data_inicio} onChange={(e) => setForm({ ...form, data_inicio: e.target.value })} />
            </Campo>
            <Campo rotulo={tr("Só a equipa (coluna TEAM)")} largura={170}>
              <input style={campo} value={form.filtro_equipa} placeholder="P15" onChange={(e) => setForm({ ...form, filtro_equipa: e.target.value })} />
            </Campo>
          </div>
          <div style={{ display: "flex", gap: espaco.sm }}>
            <button style={estiloBotao.primario} onClick={guardar} disabled={ocupado !== null}>
              {ocupado ? tr("A importar…") : tr("Guardar e importar")}
            </button>
            {fonte && <button style={estiloBotao.secundario} onClick={() => setEditar(false)} disabled={ocupado !== null}>{tr("Cancelar")}</button>}
            {fonte && <button style={{ ...estiloBotao.ligacao, color: cores.perigo, marginLeft: "auto" }} onClick={remover} disabled={ocupado !== null}>{tr("Desligar")}</button>}
          </div>
        </div>
      ) : fonte && (
        <div style={{ fontSize: "0.8rem", color: cores.texto, display: "flex", flexDirection: "column", gap: 6 }}>
          <div>
            <a href={fonte.url} target="_blank" rel="noreferrer" style={{ color: cores.acento }}>{tr("Abrir folha")}</a>
            {" · "}{tr("separador «{0}»", [fonte.folha])}
            {" · "}{tr("desde {0}", [dataPt(fonte.data_inicio)])}
            {fonte.filtro_equipa && <> · {tr("equipa {0}", [fonte.filtro_equipa])}</>}
          </div>
          {r && (r.ok ? (
            <div>
              <Etiqueta cor={cores.sucesso}>{tr("Importado")}</Etiqueta>{" "}
              {tr("{0} sessões de {1} jogadores em {2} dias", [r.sessoes, r.jogadores, r.dias])}
              {r.intervalo && <> ({dataPt(r.intervalo[0])}–{dataPt(r.intervalo[1])})</>}
              {" · "}{tr("PSE esperada em {0} dias", [r.dias_pse_esperada])}
              {r.ignoradas && r.ignoradas.sem_pse > 0 && <span style={{ color: cores.textoSuave }}> · {tr("{0} linhas sem PSE", [r.ignoradas.sem_pse])}</span>}
            </div>
          ) : (
            <div style={{ color: cores.perigo }}>{r.erro}</div>
          ))}
          {fonte.ultima_sincronizacao && (
            <div style={{ color: cores.textoSuave, fontSize: "0.74rem" }}>
              {tr("Última leitura: {0}", [new Date(fonte.ultima_sincronizacao).toLocaleString()])}
              {r?.ok && <> · <Link href="/analise" style={{ color: cores.acento }}>{tr("Ver PSE esperada vs real")}</Link></>}
            </div>
          )}
        </div>
      )}

      {erro && <div style={{ marginTop: espaco.sm, fontSize: "0.8rem", color: cores.perigo }}>{erro}</div>}
    </Cartao>
  );
}
