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
import {
  IconEye,
  IconEyeOff,
  IconPin,
  IconMoon,
  IconSun,
  IconSearch,
  IconLogOut,
} from "@/components/icons/Icons";
import { AREAS, UTILITARIOS, hrefArea, localizar } from "@/components/layout/navegacao";
import { mudarLingua, useTr } from "@/lib/i18n/cliente";
import { LogoMarca } from "@/components/layout/Logo";

type Item = { href: string; label: string; Icon: (p: { size?: number }) => React.ReactElement };

// O menu tem uma entrada por área de trabalho (ver navegacao.tsx); as páginas
// de cada área são separadores no topo do ecrã.
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

  const areaAtual = localizar(pathname)?.area.id;

  const tema = useTema();
  const pinned = !montado || fixado;
  const aberto = pinned || hover;

  async function sair() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  function linha({ href, label, Icon }: Item, ativo = pathname === href || pathname.startsWith(`${href}/`)) {
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

        {/* Áreas de trabalho */}
        <nav className="lm-nav-scroll" style={{ display: "flex", flexDirection: "column", gap: 2, flex: 1, minHeight: 0, overflowY: "auto", overflowX: "hidden" }}>
          {AREAS.map((a) => linha({ href: hrefArea(a), label: a.titulo, Icon: a.Icon }, a.id === areaAtual))}
        </nav>

        <div style={{ height: 1, background: cores.borda, margin: "8px 2px" }} />
        {UTILITARIOS.map((u) => linha(u))}

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
