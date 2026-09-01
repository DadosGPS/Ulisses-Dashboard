"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { usePrivacidade } from "@/lib/privacidade";
import { cores, espaco, raio } from "@/lib/theme";
import {
  IconGrid,
  IconUsers,
  IconUser,
  IconCalendar,
  IconActivity,
  IconSettings,
  IconUpload,
  IconFileText,
  IconLogOut,
  IconHome,
  IconEye,
  IconEyeOff,
} from "@/components/icons/Icons";

// Main navigation sections (5 core areas)
const NAV_MAIN = [
  { href: "/dashboard", label: "🏠 Dashboard", Icon: IconHome },
  { href: "/sessoes", label: "📅 Sessões", Icon: IconCalendar },
  { href: "/jogadores", label: "👤 Jogadores", Icon: IconUser },
  { href: "/analise", label: "📊 Análise", Icon: IconGrid },
  { href: "/configuracoes", label: "⚙️ Definições", Icon: IconSettings },
];

// Quick actions (grouped separately)
const NAV_ACTIONS = [
  { href: "/sessoes/importar", label: "Importar GPS", Icon: IconUpload, color: "#22c55e" },
  { href: "/bem-estar/questionario", label: "Questionário Bem-Estar", Icon: IconUser, color: "#3b82f6" },
];

export function Sidebar({ email }: { email: string }) {
  const pathname = usePathname();
  const router = useRouter();
  const { oculto, alternar } = usePrivacidade();

  async function sair() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  return (
    <aside
      style={{
        width: 232,
        flexShrink: 0,
        height: "100vh",
        position: "sticky",
        top: 0,
        display: "flex",
        flexDirection: "column",
        background: cores.bgElevado,
        borderRight: `1px solid ${cores.borda}`,
        padding: `${espaco.lg}px ${espaco.md}px`,
      }}
    >
      {/* Marca */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: `0 ${espaco.sm}px`, marginBottom: espaco.xl }}>
        <div
          style={{
            width: 30,
            height: 30,
            borderRadius: raio.sm,
            background: `linear-gradient(135deg, ${cores.cargaInterna}, ${cores.destaque})`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "0.85rem",
            fontWeight: 800,
            color: "white",
            flexShrink: 0,
          }}
        >
          L
        </div>
        <div style={{ minWidth: 0 }}>
          <div className="font-display" style={{ fontSize: "0.86rem", fontWeight: 700, color: "white", lineHeight: 1.1 }}>
            LoadMonitor
          </div>
        </div>
      </div>

      {/* Navegação Principal */}
      <nav style={{ display: "flex", flexDirection: "column", gap: 2, flex: 1 }}>
        {NAV_MAIN.map(({ href, label, Icon }) => {
          const ativo = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: `${espaco.sm}px ${espaco.md}px`,
                borderRadius: raio.sm,
                fontSize: "0.83rem",
                fontWeight: ativo ? 600 : 500,
                color: ativo ? "white" : cores.textoSuave,
                background: ativo ? "rgba(230,57,70,0.12)" : "transparent",
                borderLeft: ativo ? `2px solid ${cores.cargaInterna}` : "2px solid transparent",
                textDecoration: "none",
                transition: "background 0.12s, color 0.12s",
              }}
            >
              {label}
            </Link>
          );
        })}

        <div style={{ height: 1, background: cores.borda, margin: `${espaco.md}px ${espaco.sm}px` }} />

        {/* Ações Rápidas */}
        {NAV_ACTIONS.map(({ href, label, Icon, color }) => {
          const ativo = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: `${espaco.sm}px ${espaco.md}px`,
                borderRadius: raio.sm,
                fontSize: "0.83rem",
                fontWeight: 600,
                color: color,
                background: `color-mix(in srgb, ${color} 8%, transparent)`,
                textDecoration: "none",
                transition: "all 0.12s",
              }}
            >
              <Icon size={17} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Utilizador */}
      <div style={{ borderTop: `1px solid ${cores.borda}`, paddingTop: espaco.md, marginTop: espaco.md }}>
        <button
          onClick={alternar}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            width: "100%",
            padding: `${espaco.sm}px ${espaco.md}px`,
            borderRadius: raio.sm,
            fontSize: "0.8rem",
            fontWeight: 600,
            color: oculto ? cores.atencao : cores.textoSuave,
            background: oculto ? "rgba(245,158,11,0.1)" : "transparent",
            border: "none",
            cursor: "pointer",
            textAlign: "left",
            marginBottom: espaco.sm,
          }}
        >
          {oculto ? <IconEyeOff size={16} /> : <IconEye size={16} />}
          {oculto ? "Modo privado (ativo)" : "Modo privado"}
        </button>
        <div
          style={{
            fontSize: "0.72rem",
            color: cores.textoSuave,
            marginBottom: espaco.sm,
            padding: `0 ${espaco.sm}px`,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
          title={email}
        >
          {email}
        </div>
        <button
          onClick={sair}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            width: "100%",
            padding: `${espaco.sm}px ${espaco.md}px`,
            borderRadius: raio.sm,
            fontSize: "0.8rem",
            fontWeight: 500,
            color: cores.textoSuave,
            background: "transparent",
            border: "none",
            cursor: "pointer",
            textAlign: "left",
          }}
        >
          <IconLogOut size={16} />
          Sair
        </button>
      </div>
    </aside>
  );
}
