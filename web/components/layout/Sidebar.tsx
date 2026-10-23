"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { usePrivacidade } from "@/lib/privacidade";
import { useStore } from "@/lib/store";
import { cores, sombra } from "@/lib/theme";
import { definirTema, useTema } from "@/lib/tema";
import { SeletorEquipa } from "@/components/layout/SeletorEquipa";
import { IconCalendar,
  IconHome,
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
  IconGauge,
  IconRoute,
  IconMessage,
  IconMoon,
  IconSun,
  IconCheckCircle,
  IconSearch,
  IconLogOut,
  IconChevronDown,
} from "@/components/icons/Icons";
import { mudarLingua, useTr } from "@/lib/i18n/cliente";
import { LogoMarca } from "@/components/layout/Logo";

type Item = { href: string; label: string; Icon: (p: { size?: number }) => React.ReactElement };

// Navegação agrupada pelo que o PF está a fazer. «Dia a dia» fica sempre
// aberto; os outros grupos abrem-se ao clicar (e o do ecrã atual abre sozinho).
type Grupo = { id: string; titulo: string; itens: Item[] };
export const GRUPOS: Grupo[] = [
  { id: "dia", titulo: "Dia a dia", itens: [
    { href: "/hoje", label: "Hoje", Icon: IconCheckCircle },
    { href: "/dashboard", label: "Centro de Controlo", Icon: IconHome },
    { href: "/prontidao", label: "Prontidão", Icon: IconGauge },
    { href: "/calendario", label: "Calendário", Icon: IconCalendar },
    { href: "/upload", label: "Importar GPS", Icon: IconUpload },
    { href: "/mensagens", label: "Mensagens aos Jogadores", Icon: IconMessage },
  ] },
  { id: "planear", titulo: "Planear e analisar", itens: [
    { href: "/planeamento", label: "Planeamento", Icon: IconClipboard },
    { href: "/carga-externa", label: "Carga Externa", Icon: IconActivity },
    { href: "/analise", label: "Análise", Icon: IconBarChart },
    { href: "/velocidade", label: "Limiares de Velocidade", Icon: IconTrendLine },
    { href: "/jogadores", label: "Jogadores", Icon: IconUser },
  ] },
  { id: "saude", titulo: "Saúde", itens: [
    { href: "/lesoes", label: "Lesões", Icon: IconPlus },
    { href: "/regresso", label: "Regresso ao Jogo", Icon: IconRoute },
  ] },
  { id: "academia", titulo: "Academia", itens: [
    { href: "/academia", label: "Academia", Icon: IconUsers },
    { href: "/perfil", label: "Perfil / Testes", Icon: IconDumbbell },
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
  const ativoEm = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

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
    const ativo = pathname === href || pathname.startsWith(`${href}/`);
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
          fontSize: "0.86rem",
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
          padding: "20px 12px 14px",
          overflow: "hidden",
          transition: "width 0.2s, box-shadow 0.2s",
        }}
      >
        {/* Marca */}
        <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "0 4px", marginBottom: 18, whiteSpace: "nowrap" }}>
          <div style={{ width: 44, height: 44, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <LogoMarca tamanho={36} />
          </div>
          {texto(
            <div>
              <div className="font-display" style={{ fontSize: "1.2rem", fontWeight: 700, color: cores.textoForte, lineHeight: 1.1, letterSpacing: "-0.02em" }}>
                LoadMonitor</div>
              <div className="font-display" style={{ fontSize: "0.6rem", fontWeight: 500, letterSpacing: "0.42em", color: cores.textoFraco, marginTop: 3 }}>
                SYSTEM</div>
            </div>,
          )}
        </div>

        {/* Equipa ativa (escalão × época) */}
        {aberto && (
          <div style={{ padding: "0 2px", marginBottom: 14 }}>
            <SeletorEquipa />
          </div>
        )}

        {/* Procurar (Ctrl+K) */}
        <button onClick={() => window.dispatchEvent(new Event("lm-abrir-paleta"))} title={aberto ? undefined : tr("Procurar (Ctrl+K)")}
          style={{ display: "flex", alignItems: "center", gap: 10, height: 34, padding: "0 12px", marginBottom: 10, borderRadius: 8, flexShrink: 0,
            border: `1px solid ${cores.borda}`, background: cores.superficie, color: cores.textoSuave, cursor: "pointer", fontSize: "0.82rem", whiteSpace: "nowrap", overflow: "hidden" }}>
          <span style={{ display: "flex", width: 22, justifyContent: "center", flexShrink: 0 }}><IconSearch size={16} /></span>
          {texto(<>{tr("Procurar…")}<span style={{ marginLeft: 70, fontSize: "0.7rem", color: cores.textoFraco, border: `1px solid ${cores.borda}`, borderRadius: 4, padding: "0 5px" }}>Ctrl K</span></>)}
        </button>

        {/* Navegação agrupada (scroll) */}
        <nav className="lm-nav-scroll" style={{ display: "flex", flexDirection: "column", gap: 2, flex: 1, minHeight: 0, overflowY: "auto", overflowX: "hidden" }}>
          {GRUPOS.map((g, i) => {
            const temAtivo = g.itens.some((it) => ativoEm(it.href));
            const visivel = !aberto || g.id === "dia" || abertos.includes(g.id) || temAtivo;
            return (
              <div key={g.id} style={{ display: "flex", flexDirection: "column", gap: 2, marginTop: i ? 6 : 0 }}>
                {aberto ? (
                  g.id !== "dia" && (
                    <button onClick={() => alternarGrupo(g.id)} aria-expanded={visivel}
                      style={{ display: "flex", alignItems: "center", justifyContent: "space-between", height: 26, padding: "0 12px", border: "none", background: "transparent",
                        color: cores.textoFraco, fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", cursor: "pointer", whiteSpace: "nowrap" }}>
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
            style={{ ...botaoIcone, fontSize: "0.72rem", fontWeight: 800, letterSpacing: "0.04em" }}>
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
            {aberto ? <span style={{ fontSize: "0.74rem", fontWeight: 600, whiteSpace: "nowrap", padding: "0 4px" }}>{pinned ? tr("Recolher") : tr("Fixar")}</span> : <IconPin size={17} />}
          </button>
        </div>
        {aberto && oculto && <div style={{ fontSize: "0.7rem", color: cores.atencao, marginTop: 4, padding: "0 6px" }}>{tr("Modo privado ativo")}</div>}
      </aside>
    </div>
  );
}
