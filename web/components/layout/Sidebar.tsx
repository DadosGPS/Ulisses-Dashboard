"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { usePrivacidade } from "@/lib/privacidade";
import { useStore } from "@/lib/store";
import { cores, sombra, letra } from "@/lib/theme";
import { definirTema, useTema } from "@/lib/tema";
import { SeletorEquipa } from "@/components/layout/SeletorEquipa";
import { IconCalendar, IconFileText,
  IconUsers,
  IconActivity,
  IconUser,
  IconDumbbell,
  IconPlus,
  IconBarChart,
  IconClipboard,
  IconSettings,
  IconUpload,
  IconTrendLine,
  IconEye,
  IconEyeOff,
  IconPin,
  IconRoute,
  IconMoon,
  IconSun,
  IconCheckCircle,
  IconHeart,
  IconSearch,
  IconLogOut,
  IconChevronDown,
} from "@/components/icons/Icons";
import { mudarLingua, useTr } from "@/lib/i18n/cliente";
import { LogoMarca } from "@/components/layout/Logo";

type Item = { href: string; label: string; Icon: (p: { size?: number }) => React.ReactElement; /** Acende também em subpáginas deste prefixo. */ prefixo?: string };

// Navegação pelos momentos do dia do PF: o grupo principal tem só 5 entradas
// (manhã → treino → jogo → semana → evolução) e fica sempre aberto. Tudo o
// resto vive em «Mais», em grupos que se abrem ao clicar (o do ecrã atual
// abre sozinho). Importar GPS tem um botão próprio por cima do menu.
type Grupo = { id: string; titulo: string; itens: Item[] };
export const GRUPOS: Grupo[] = [
  { id: "dia", titulo: "O meu dia", itens: [
    { href: "/hoje", label: "Hoje", Icon: IconCheckCircle },
    { href: "/relatorios/treino", label: "Treino", Icon: IconActivity },
    { href: "/relatorios/jogo", label: "Jogo", Icon: IconTrendLine },
    { href: "/planeamento/semana", label: "Semana", Icon: IconCalendar },
  ] },
  { id: "planear", titulo: "Planear", itens: [
    { href: "/planeamento/calendario", label: "Calendário e época", Icon: IconCalendar, prefixo: "/planeamento" },
  ] },
  // Carga em duas pastas: interna (o que o jogador sente — PSE, sRPE,
  // monotonia, strain, wellness) e externa (o que o GPS mede).
  { id: "carga-interna", titulo: "Carga interna", itens: [
    { href: "/analise", label: "PSE e sRPE", Icon: IconBarChart },
    { href: "/hoje/prontidao", label: "Wellness e prontidão", Icon: IconHeart },
  ] },
  { id: "carga-externa", titulo: "Carga externa", itens: [
    { href: "/carga-externa", label: "Carga Externa (GPS)", Icon: IconActivity, prefixo: "/carga-externa" },
  ] },
  // A ficha junta tudo de um jogador (carga, wellness, testes, maturação),
  // por isso fica com a Academia e os testes, não dentro de uma das cargas.
  // Também se abre ao clicar no nome do jogador nas tabelas.
  { id: "jogadores", titulo: "Jogadores", itens: [
    { href: "/jogadores", label: "Ficha do jogador", Icon: IconUser },
    { href: "/academia", label: "Academia", Icon: IconUsers },
    { href: "/perfil", label: "Perfil / Testes", Icon: IconDumbbell },
  ] },
  { id: "saude", titulo: "Saúde", itens: [
    { href: "/lesoes", label: "Lesões", Icon: IconPlus },
    { href: "/regresso", label: "Regresso ao Jogo", Icon: IconRoute },
  ] },
  { id: "dados", titulo: "Dados", itens: [
    { href: "/upload", label: "Importar GPS", Icon: IconUpload },
    { href: "/relatorios/verificacao", label: "Verificação de dados", Icon: IconFileText },
  ] },
];
const DEFINICOES: Item = { href: "/configuracoes", label: "Definições", Icon: IconSettings };
const CHAVE_GRUPOS = "lm-menu-grupos";

const LARGURA = 264;
const botaoIcone: React.CSSProperties = {
  display: "flex", alignItems: "center", justifyContent: "center", minWidth: 36, height: 34, borderRadius: 8,
  border: "none", background: "transparent", color: cores.textoSuave, cursor: "pointer", flexShrink: 0,
};
const LARGURA_RAIL = 76;
const AZUL = cores.acento;
const ATIVO_BG = cores.superficieHover;

export function Sidebar({ email }: { email: string }) {
  const tr = useTr();
  const pathname = usePathname();
  const router = useRouter();
  const { oculto, alternar } = usePrivacidade();
  const fixado = useStore((s) => s.sidebarOpen);
  const alternarFixado = useStore((s) => s.toggleSidebar);

  // O estado "fixado" vem do localStorage — até montar, assume fixado para o
  // HTML do servidor coincidir com o primeiro render do cliente.
  const [montado, setMontado] = useState(false);
  const [hover, setHover] = useState(false);
  useEffect(() => setMontado(true), []);

  const [abertos, setAbertos] = useState<string[]>(["dia"]);
  useEffect(() => {
    try { const v = JSON.parse(localStorage.getItem(CHAVE_GRUPOS) ?? "null"); if (Array.isArray(v)) setAbertos(v); } catch { /* sem preferências */ }
  }, []);
  const alternarGrupo = (id: string) => {
    const novo = abertos.includes(id) ? abertos.filter((x) => x !== id) : [...abertos, id];
    setAbertos(novo);
    try { localStorage.setItem(CHAVE_GRUPOS, JSON.stringify(novo)); } catch { /* ignora */ }
  };
  // Só a entrada mais específica fica ativa (ex.: em /planeamento/semana acende
  // «Semana» e não também «Planeamento»).
  const corresponde = (base: string) => pathname === base || pathname.startsWith(`${base}/`);
  const hrefAtivo = [...GRUPOS.flatMap((g) => g.itens.map((it) => ({ href: it.href, base: it.prefixo ?? it.href }))), { href: DEFINICOES.href, base: DEFINICOES.href }]
    .filter((x) => corresponde(x.href) || corresponde(x.base))
    .sort((x, y) => (corresponde(y.href) ? y.href : y.base).length - (corresponde(x.href) ? x.href : x.base).length)[0]?.href;
  const ativoEm = (href: string) => href === hrefAtivo;

  const tema = useTema();
  const pinned = !montado || fixado;
  const aberto = pinned || hover;

  async function sair() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  function linha({ href, label, Icon }: Item) {
    const ativo = ativoEm(href);
    return (
      <Link
        key={href}
        href={href}
        title={aberto ? undefined : tr(label)}
        className="lm-nav-item"
        data-ativo={ativo || undefined}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          height: 38,
          padding: "0 12px",
          borderRadius: 8,
          fontSize: letra.texto,
          fontWeight: ativo ? 600 : 500,
          color: ativo ? cores.textoForte : cores.textoSuave,
          background: ativo ? ATIVO_BG : undefined,
          textDecoration: "none",
          whiteSpace: "nowrap",
          overflow: "hidden",
          flexShrink: 0,
        }}
      >
        <span style={{ display: "flex", flexShrink: 0, width: 22, justifyContent: "center", color: ativo ? cores.acento : "inherit" }}>
          <Icon size={18} />
        </span>
        <span style={{ opacity: aberto ? 1 : 0, transition: "opacity 0.15s" }}>{tr(label)}</span>
      </Link>
    );
  }

  const texto = (conteudo: React.ReactNode) => (
    <span style={{ opacity: aberto ? 1 : 0, transition: "opacity 0.15s", whiteSpace: "nowrap" }}>{conteudo}</span>
  );

  return (
    // O wrapper reserva o espaço no layout; a <aside> expande por cima do
    // conteúdo quando o menu não está fixado e o rato passa por cima.
    <div
      data-no-print
      style={{
        width: pinned ? LARGURA : LARGURA_RAIL,
        flexShrink: 0,
        height: "100vh",
        position: "sticky",
        top: 0,
        zIndex: 40,
        transition: "width 0.2s",
      }}
    >
      <aside
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
        style={{
          position: "absolute",
          inset: 0,
          right: "auto",
          width: aberto ? LARGURA : LARGURA_RAIL,
          display: "flex",
          flexDirection: "column",
          background: cores.bgElevado,
          borderRight: `1px solid ${cores.borda}`,
          boxShadow: !pinned && hover ? sombra.elevado : "none",
          padding: "20px 12px 16px",
          overflow: "hidden",
          transition: "width 0.2s, box-shadow 0.2s",
        }}
      >
        {/* Marca */}
        <div style={{ display: "flex", alignItems: "center", gap: 16, padding: "0 4px", marginBottom: 20, whiteSpace: "nowrap" }}>
          <div style={{ width: 44, height: 44, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <LogoMarca tamanho={36} />
          </div>
          {texto(
            <div>
              <div className="font-display" style={{ fontSize: letra.numero, fontWeight: 700, color: cores.textoForte, lineHeight: 1.1, letterSpacing: "-0.02em" }}>
                LoadMonitor</div>
              <div className="font-display" style={{ fontSize: letra.legenda, fontWeight: 600, letterSpacing: "0.42em", color: cores.textoFraco, marginTop: 4 }}>
                SYSTEM</div>
            </div>,
          )}
        </div>

        {/* Equipa ativa (escalão × época) */}
        {aberto && (
          <div style={{ padding: "0 2px", marginBottom: 16 }}>
            <SeletorEquipa />
          </div>
        )}

        {/* Procurar (Ctrl+K) */}
        <button onClick={() => window.dispatchEvent(new Event("lm-abrir-paleta"))} title={aberto ? undefined : tr("Procurar (Ctrl+K)")}
          style={{ display: "flex", alignItems: "center", gap: 12, height: 34, padding: "0 12px", marginBottom: 12, borderRadius: 8, flexShrink: 0,
            border: `1px solid ${cores.borda}`, background: cores.superficie, color: cores.textoSuave, cursor: "pointer", fontSize: letra.texto, whiteSpace: "nowrap", overflow: "hidden" }}>
          <span style={{ display: "flex", width: 22, justifyContent: "center", flexShrink: 0 }}><IconSearch size={16} /></span>
          {texto(<>{tr("Procurar…")}<span style={{ marginLeft: 70, fontSize: letra.legenda, color: cores.textoFraco, border: `1px solid ${cores.borda}`, borderRadius: 4, padding: "0 6px" }}>Ctrl K</span></>)}
        </button>

        {/* Ação mais frequente depois do treino */}
        <Link href="/upload" title={aberto ? undefined : tr("Importar GPS")}
          style={{ display: "flex", alignItems: "center", gap: 12, height: 34, padding: "0 12px", marginBottom: 12, borderRadius: 8, flexShrink: 0,
            border: `1px solid color-mix(in srgb, ${cores.acento} 45%, transparent)`, background: `color-mix(in srgb, ${cores.acento} 10%, transparent)`,
            color: cores.textoForte, fontSize: letra.texto, fontWeight: 600, textDecoration: "none", whiteSpace: "nowrap", overflow: "hidden" }}>
          <span style={{ display: "flex", width: 22, justifyContent: "center", flexShrink: 0, color: cores.acento }}><IconUpload size={16} /></span>
          {texto(tr("Importar GPS"))}
        </Link>

        {/* Navegação agrupada (scroll) */}
        <nav className="lm-nav-scroll" style={{ display: "flex", flexDirection: "column", gap: 2, flex: 1, minHeight: 0, overflowY: "auto", overflowX: "hidden" }}>
          {GRUPOS.map((g, i) => {
            const temAtivo = g.itens.some((it) => ativoEm(it.href));
            const visivel = !aberto || g.id === "dia" || abertos.includes(g.id) || temAtivo;
            return (
              <div key={g.id} style={{ display: "flex", flexDirection: "column", gap: 2, marginTop: i ? 6 : 0 }}>
                {aberto && i === 1 && (
                  <div style={{ fontSize: letra.legenda, fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase", color: cores.textoFraco,
                    padding: "12px 12px 2px", borderTop: `1px solid ${cores.borda}`, marginTop: 6 }}>{tr("Mais")}</div>
                )}
                {aberto ? (
                  g.id !== "dia" && (
                    <button onClick={() => alternarGrupo(g.id)} aria-expanded={visivel}
                      style={{ display: "flex", alignItems: "center", justifyContent: "space-between", height: 26, padding: "0 12px", border: "none", background: "transparent",
                        color: cores.textoSuave, fontSize: letra.pequeno, fontWeight: 600, cursor: "pointer", whiteSpace: "nowrap" }}>
                      {tr(g.titulo)}
                      <span style={{ display: "flex", transform: visivel ? "none" : "rotate(-90deg)", transition: "transform 0.15s" }}><IconChevronDown size={12} /></span>
                    </button>
                  )
                ) : i > 0 && <div style={{ height: 1, background: cores.borda, margin: "4px 8px" }} />}
                {visivel && g.itens.map(linha)}
              </div>
            );
          })}
        </nav>

        <div style={{ height: 1, background: cores.borda, margin: "8px 2px" }} />
        {linha(DEFINICOES)}

        {/* Preferências numa só linha: tema, idioma, modo privado, sair */}
        <div style={{ display: "flex", flexDirection: aberto ? "row" : "column", alignItems: aberto ? "center" : "flex-start", gap: 4, marginTop: 8 }}>
          <button onClick={() => definirTema(tema === "dark" ? "light" : "dark")} title={tema === "dark" ? tr("Mudar para claro") : tr("Mudar para escuro")} style={botaoIcone}>
            {tema === "dark" ? <IconMoon size={17} /> : <IconSun size={17} />}
          </button>
          <button onClick={() => mudarLingua(tr.lingua === "pt" ? "en" : "pt")} title={tr.lingua === "pt" ? "English" : "Português"} aria-label={tr("Idioma")}
            style={{ ...botaoIcone, fontSize: letra.pequeno, fontWeight: 700, letterSpacing: "0.04em" }}>
            {tr.lingua.toUpperCase()}
          </button>
          <button onClick={alternar} title={oculto ? tr("Modo privado (ativo)") : tr("Modo privado")} aria-pressed={oculto}
            style={{ ...botaoIcone, color: oculto ? cores.atencao : cores.textoSuave, background: oculto ? "rgb(245 158 11 / 0.12)" : "transparent" }}>
            {oculto ? <IconEyeOff size={17} /> : <IconEye size={17} />}
          </button>
          <button onClick={sair} title={tr("Terminar sessão") + (email ? ` · ${email}` : "")} aria-label={tr("Terminar sessão")} style={botaoIcone}>
            <IconLogOut size={17} />
          </button>
          <button onClick={alternarFixado} title={pinned ? tr("Recolher menu") : tr("Fixar menu")}
            style={{ ...botaoIcone, marginLeft: aberto ? "auto" : 0, color: pinned ? cores.textoSuave : AZUL }}>
            {aberto ? <span style={{ fontSize: letra.pequeno, fontWeight: 600, whiteSpace: "nowrap", padding: "0 4px" }}>{pinned ? tr("Recolher") : tr("Fixar")}</span> : <IconPin size={17} />}
          </button>
        </div>
        {aberto && oculto && <div style={{ fontSize: letra.legenda, color: cores.atencao, marginTop: 4, padding: "0 6px" }}>{tr("Modo privado ativo")}</div>}
      </aside>
    </div>
  );
}
