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
  respostas?: number;
  nao_podem_treinar?: number;
  jogadores?: number;
  dias?: number;
  intervalo?: [string, string] | null;
  dias_pse_esperada?: number;
  ignoradas?: { antes_inicio: number; sem_pse?: number; pse_invalida?: number; sem_jogador?: number };
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

type Tipo = "pse" | "wellness";
const FOLHA_PADRAO: Record<Tipo, string> = { pse: "RPE", wellness: "" };

/** Liga a equipa a uma folha do Google Sheets e importa a partir de uma data:
 * - tipo «pse»: a folha de RPE (ex.: «P15 - RPE») → PSE real e PSE esperada;
 * - tipo «wellness»: as respostas do formulário diário → wellness de cada jogador. */
export function LigacaoGoogleSheets({ teamId, tipo = "pse" }: { teamId: string; tipo?: Tipo }) {
  const tr = useTr();
  const wellness = tipo === "wellness";
  const base = `/api/teams/${teamId}/google-sheets`;
  const q = `?tipo=${tipo}`;
  const [config, setConfig] = useState<Config | null>(null);
  const [editar, setEditar] = useState(false);
  const [form, setForm] = useState({ url: "", folha: FOLHA_PADRAO[tipo], data_inicio: "", filtro_equipa: "" });
  const [ocupado, setOcupado] = useState<"guardar" | "sincronizar" | "remover" | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  async function carregar() {
    try {
      const c = await pedidoApi<Config>(`${base}${q}`);
      setConfig(c);
      if (c.fonte) {
        setForm({ url: c.fonte.url, folha: c.fonte.folha, data_inicio: c.fonte.data_inicio, filtro_equipa: c.fonte.filtro_equipa ?? "" });
      }
      setEditar(!c.fonte);
    } catch (e) {
      setErro((e as Error).message);
    }
  }

  useEffect(() => { carregar(); }, [teamId, tipo]); // eslint-disable-line react-hooks/exhaustive-deps

  async function guardar() {
    setErro(null);
    if (!form.url.trim() || !form.data_inicio) {
      setErro(tr("Indica o link da folha e a data a partir da qual importar."));
      return;
    }
    setOcupado("guardar");
    try {
      await pedidoApi(`${base}${q}`, "PUT", { ...form, filtro_equipa: form.filtro_equipa || null });
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
      await pedidoApi(`${base}/sincronizar${q}`, "POST");
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
      await pedidoApi(`${base}${q}`, "DELETE");
      setForm({ url: "", folha: FOLHA_PADRAO[tipo], data_inicio: "", filtro_equipa: "" });
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
        <div style={{ fontWeight: 600, color: cores.textoForte, fontSize: "0.95rem" }}>{wellness ? tr("Wellness do Google Sheets") : tr("PSE do Google Sheets")}</div>
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
        {wellness
          ? tr("Lê a folha de respostas do formulário de wellness (Player, Sleep quality, Muscle soreness, Energy level, Mental stress level…) e grava o wellness diário de cada jogador. A app volta a ler a folha de hora a hora.")
          : tr("Lê a folha de PSE da equipa técnica (colunas DATE, NAME, DURATION, RPE, expected RPE…) e grava a PSE de cada jogador e a PSE esperada de cada dia. A app volta a ler a folha de hora a hora.")}
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
              <input style={campo} value={form.folha} placeholder={wellness ? tr("o primeiro") : undefined} onChange={(e) => setForm({ ...form, folha: e.target.value })} />
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
            {fonte.folha && <>{" · "}{tr("separador «{0}»", [fonte.folha])}</>}
            {" · "}{tr("desde {0}", [dataPt(fonte.data_inicio)])}
            {fonte.filtro_equipa && <> · {tr("equipa {0}", [fonte.filtro_equipa])}</>}
          </div>
          {r && (r.ok ? (
            <div>
              <Etiqueta cor={cores.sucesso}>{tr("Importado")}</Etiqueta>{" "}
              {wellness
                ? tr("{0} respostas de {1} jogadores em {2} dias", [r.respostas, r.jogadores, r.dias])
                : tr("{0} sessões de {1} jogadores em {2} dias", [r.sessoes, r.jogadores, r.dias])}
              {r.intervalo && <> ({dataPt(r.intervalo[0])}–{dataPt(r.intervalo[1])})</>}
              {!wellness && <>{" · "}{tr("PSE esperada em {0} dias", [r.dias_pse_esperada])}</>}
              {!wellness && r.ignoradas && (r.ignoradas.sem_pse ?? 0) > 0 && <span style={{ color: cores.textoSuave }}> · {tr("{0} linhas sem PSE", [r.ignoradas.sem_pse])}</span>}
              {wellness && (r.nao_podem_treinar ?? 0) > 0 && <span style={{ color: cores.atencao }}> · {tr("{0} disseram que não podem treinar", [r.nao_podem_treinar])}</span>}
            </div>
          ) : (
            <div style={{ color: cores.perigo }}>{r.erro}</div>
          ))}
          {fonte.ultima_sincronizacao && (
            <div style={{ color: cores.textoSuave, fontSize: "0.74rem" }}>
              {tr("Última leitura: {0}", [new Date(fonte.ultima_sincronizacao).toLocaleString()])}
              {r?.ok && !wellness && <> · <Link href="/analise" style={{ color: cores.acento }}>{tr("Ver PSE esperada vs real")}</Link></>}
              {r?.ok && wellness && <> · <Link href="/hoje" style={{ color: cores.acento }}>{tr("Ver no Hoje")}</Link></>}
            </div>
          )}
        </div>
      )}

      {erro && <div style={{ marginTop: espaco.sm, fontSize: "0.8rem", color: cores.perigo }}>{erro}</div>}
    </Cartao>
  );
}
