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
} from "@/components/icons/Icons";

type Item = { href: string; label: string; Icon: (p: { size?: number }) => React.ReactElement };

// Navegação principal (zona com scroll)
// Por ordem de importância no dia a dia.
const NAV_MAIN: Item[] = [
  { href: "/dashboard", label: "Centro de Controlo", Icon: IconHome },
  { href: "/prontidao", label: "Prontidão", Icon: IconGauge },
  { href: "/planeamento", label: "Planeamento", Icon: IconClipboard },
  { href: "/calendario", label: "Calendário", Icon: IconCalendar },
  { href: "/carga-externa", label: "Carga Externa", Icon: IconActivity },
  { href: "/analise", label: "Análise", Icon: IconBarChart },
  { href: "/velocidade", label: "Limiares de Velocidade", Icon: IconTrendLine },
  { href: "/lesoes", label: "Lesões", Icon: IconPlus },
  { href: "/regresso", label: "Regresso ao Jogo", Icon: IconRoute },
  { href: "/perfil", label: "Perfil / Testes", Icon: IconDumbbell },
  { href: "/jogadores", label: "Jogadores", Icon: IconUser },
  { href: "/academia", label: "Academia", Icon: IconUsers },
];

// Dados e configuração — à parte, no fundo.
const NAV_FOOT: Item[] = [
  { href: "/upload", label: "Importar GPS", Icon: IconUpload },
  { href: "/mensagens", label: "Mensagens aos Jogadores", Icon: IconMessage },
  { href: "/configuracoes", label: "Definições", Icon: IconSettings },
];

const LARGURA = 264;
const LARGURA_RAIL = 76;
const AZUL = cores.acento;
const ATIVO_BG = cores.superficieHover;

export function Sidebar({ email }: { email: string }) {
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
        title={aberto ? undefined : label}
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
        <span style={{ opacity: aberto ? 1 : 0, transition: "opacity 0.15s" }}>{label}</span>
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
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              background: cores.acentoSuave,
              border: `1px solid ${cores.borda}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: AZUL,
              flexShrink: 0,
            }}
          >
            <IconTrendLine size={22} />
          </div>
          {texto(
            <div>
              <div className="font-display" style={{ fontSize: "1.15rem", fontWeight: 700, color: cores.textoForte, lineHeight: 1.15 }}>
                LoadMonitor
              </div>
              <div style={{ fontSize: "0.62rem", fontWeight: 600, letterSpacing: "0.12em", color: cores.textoFraco, marginTop: 2 }}>
                MONITORIZAÇÃO DE CARGA
              </div>
            </div>,
          )}
        </div>

        {/* Equipa ativa (escalão × época) */}
        {aberto && (
          <div style={{ padding: "0 2px", marginBottom: 14 }}>
            <SeletorEquipa />
          </div>
        )}

        {/* Navegação principal (scroll) */}
        <nav className="lm-nav-scroll" style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1, minHeight: 0, overflowY: "auto", overflowX: "hidden" }}>
          {NAV_MAIN.map(linha)}
        </nav>

        <div style={{ height: 1, background: cores.borda, margin: "10px 2px" }} />

        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {NAV_FOOT.map(linha)}
        </div>

        {/* Tema: Escuro / Claro (no menu recolhido, um só botão que alterna) */}
        {aberto ? (
          <div role="group" aria-label="Tema" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4, padding: 3, marginTop: 12, borderRadius: 10, background: cores.superficie, border: `1px solid ${cores.borda}` }}>
            {(["dark", "light"] as const).map((t) => {
              const ativo = tema === t;
              return (
                <button key={t} onClick={() => definirTema(t)} aria-pressed={ativo}
                  style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6, height: 30, borderRadius: 7, border: "none", cursor: "pointer",
                    fontSize: "0.8rem", fontWeight: 600, whiteSpace: "nowrap",
                    background: ativo ? cores.bgCartao : "transparent", color: ativo ? cores.textoForte : cores.textoSuave,
                    boxShadow: ativo ? "0 1px 2px rgb(0 0 0 / 0.12)" : "none" }}>
                  {t === "dark" ? <IconMoon size={14} /> : <IconSun size={14} />}
                  {t === "dark" ? "Escuro" : "Claro"}
                </button>
              );
            })}
          </div>
        ) : (
          <button onClick={() => definirTema(tema === "dark" ? "light" : "dark")} title={tema === "dark" ? "Mudar para claro" : "Mudar para escuro"}
            style={{ display: "flex", alignItems: "center", justifyContent: "flex-start", height: 36, marginTop: 12, padding: "0 16px", border: "none", background: "transparent", color: cores.textoSuave, cursor: "pointer" }}>
            {tema === "dark" ? <IconMoon size={18} /> : <IconSun size={18} />}
          </button>
        )}

        {/* Modo privado */}
        <button
          onClick={alternar}
          title={aberto ? undefined : oculto ? "Modo privado (ativo)" : "Modo privado"}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: aberto ? "center" : "flex-start",
            gap: 10,
            margin: "8px 0 14px",
            height: 40,
            padding: aberto ? "0 12px" : "0 15px",
            borderRadius: 12,
            border: `1px solid ${oculto ? "rgb(245 158 11 / 0.35)" : cores.borda}`,
            background: oculto ? "rgb(245 158 11 / 0.12)" : "transparent",
            color: oculto ? cores.atencao : cores.textoSuave,
            fontSize: "0.85rem",
            fontWeight: 600,
            cursor: "pointer",
            whiteSpace: "nowrap",
            overflow: "hidden",
            flexShrink: 0,
          }}
        >
          <span style={{ display: "flex", flexShrink: 0 }}>{oculto ? <IconEyeOff size={18} /> : <IconEye size={18} />}</span>
          {texto(oculto ? "Modo privado ativo" : "Modo privado")}
        </button>

        {/* Utilizador */}
        <div style={{ padding: "0 4px", opacity: aberto ? 1 : 0, transition: "opacity 0.15s", minHeight: 22 }}>
          <div
            title={email}
            style={{ fontSize: "0.82rem", color: cores.textoSuave, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
          >
            {email}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, marginTop: 12, whiteSpace: "nowrap" }}>
          <button
            onClick={sair}
            style={{
              height: 38,
              padding: "0 14px",
              borderRadius: 10,
              border: `1px solid ${cores.bordaForte}`,
              background: "transparent",
              color: cores.textoForte,
              fontSize: "0.85rem",
              fontWeight: 600,
              cursor: "pointer",
              flexShrink: 0,
              display: aberto ? "block" : "none",
            }}
          >
            Terminar sessão
          </button>
          <button
            onClick={alternarFixado}
            title={pinned ? "Recolher menu" : "Fixar menu"}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              height: 38,
              padding: aberto ? "0 6px" : "0 15px",
              border: "none",
              background: "transparent",
              color: pinned ? cores.textoSuave : AZUL,
              fontSize: "0.82rem",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            {aberto ? (pinned ? "Recolher menu" : "Fixar menu") : <IconPin size={18} />}
          </button>
        </div>
      </aside>
    </div>
  );
}
