"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { usePrivacidade } from "@/lib/privacidade";
import { useStore } from "@/lib/store";
import { cores } from "@/lib/theme";
import {
  IconHome,
  IconActivity,
  IconTarget,
  IconCalendar,
  IconUser,
  IconDumbbell,
  IconPlus,
  IconBarChart,
  IconClipboard,
  IconFileText,
  IconSparkles,
  IconSettings,
  IconUpload,
  IconHeart,
  IconTrendLine,
  IconEye,
  IconEyeOff,
  IconPin,
} from "@/components/icons/Icons";

type Item = { href: string; label: string; Icon: (p: { size?: number }) => React.ReactElement };

// Navegação principal (zona com scroll)
const NAV_MAIN: Item[] = [
  { href: "/dashboard", label: "Centro de Controlo", Icon: IconHome },
  { href: "/carga-externa", label: "Carga Externa", Icon: IconActivity },
  { href: "/match-benchmark", label: "Match Benchmark", Icon: IconTarget },
  { href: "/sessoes", label: "Sessões", Icon: IconCalendar },
  { href: "/jogadores", label: "Jogadores", Icon: IconUser },
  { href: "/perfil", label: "Perfil / Testes", Icon: IconDumbbell },
  { href: "/lesoes", label: "Lesões", Icon: IconPlus },
  { href: "/analise", label: "Análise", Icon: IconBarChart },
  { href: "/planeamento", label: "Planeamento", Icon: IconClipboard },
  { href: "/relatorio", label: "Relatórios", Icon: IconFileText },
  { href: "/assistente", label: "Assistente", Icon: IconSparkles },
  { href: "/upload", label: "Importar GPS", Icon: IconUpload },
  { href: "/bem-estar/questionario", label: "Questionário Bem-Estar", Icon: IconHeart },
];

// Itens fixos por baixo do separador
const NAV_FOOT: Item[] = [{ href: "/configuracoes", label: "Definições", Icon: IconSettings }];

const LARGURA = 264;
const LARGURA_RAIL = 76;
const AZUL = "#3b82f6";
const ATIVO_BG = "rgba(59,130,246,0.14)";

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
          gap: 14,
          height: 46,
          padding: "0 14px",
          borderRadius: 12,
          fontSize: "0.95rem",
          fontWeight: ativo ? 600 : 500,
          color: ativo ? "white" : "rgba(226,232,240,0.82)",
          background: ativo ? ATIVO_BG : undefined,
          textDecoration: "none",
          whiteSpace: "nowrap",
          overflow: "hidden",
          flexShrink: 0,
        }}
      >
        <span style={{ display: "flex", flexShrink: 0, width: 22, justifyContent: "center" }}>
          <Icon size={21} />
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
          background: "#0b1220",
          borderRight: `1px solid ${cores.borda}`,
          boxShadow: !pinned && hover ? "8px 0 24px rgba(0,0,0,0.45)" : "none",
          padding: "20px 12px 14px",
          overflow: "hidden",
          transition: "width 0.2s, box-shadow 0.2s",
        }}
      >
        {/* Marca */}
        <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "0 4px", marginBottom: 26, whiteSpace: "nowrap" }}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              background: "#14233a",
              border: "1px solid rgba(59,130,246,0.18)",
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
              <div className="font-display" style={{ fontSize: "1.15rem", fontWeight: 700, color: "white", lineHeight: 1.15 }}>
                LoadMonitor
              </div>
              <div style={{ fontSize: "0.62rem", fontWeight: 600, letterSpacing: "0.12em", color: "rgba(148,163,184,0.85)", marginTop: 2 }}>
                MONITORIZAÇÃO DE CARGA
              </div>
            </div>,
          )}
        </div>

        {/* Navegação principal (scroll) */}
        <nav className="lm-nav-scroll" style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1, minHeight: 0, overflowY: "auto", overflowX: "hidden" }}>
          {NAV_MAIN.map(linha)}
        </nav>

        <div style={{ height: 1, background: cores.borda, margin: "10px 2px" }} />

        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {NAV_FOOT.map(linha)}
        </div>

        {/* Modo privado — interruptor em pílula, como o seletor de tema da referência */}
        <button
          onClick={alternar}
          title={aberto ? undefined : oculto ? "Modo privado (ativo)" : "Modo privado"}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: aberto ? "center" : "flex-start",
            gap: 10,
            margin: "12px 0 14px",
            height: 40,
            padding: aberto ? "0 12px" : "0 15px",
            borderRadius: 12,
            border: `1px solid ${oculto ? "rgba(245,158,11,0.35)" : cores.borda}`,
            background: oculto ? "rgba(245,158,11,0.12)" : "rgba(255,255,255,0.03)",
            color: oculto ? cores.atencao : "rgba(226,232,240,0.82)",
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
            style={{ fontSize: "0.82rem", color: "rgba(226,232,240,0.85)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
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
              background: "rgba(255,255,255,0.04)",
              color: "white",
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
              color: pinned ? "rgba(226,232,240,0.85)" : AZUL,
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
