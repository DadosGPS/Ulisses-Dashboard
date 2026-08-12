"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
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
} from "@/components/icons/Icons";

const NAV = [
  { href: "/inicio", label: "Início", Icon: IconHome },
  { href: "/analise", label: "Análise", Icon: IconGrid },
  { href: "/equipa", label: "Equipa", Icon: IconUsers },
  { href: "/jogadores", label: "Jogadores", Icon: IconUser },
  { href: "/planeamento", label: "Planeamento", Icon: IconCalendar },
  { href: "/avancado", label: "Avançado", Icon: IconActivity },
  { href: "/relatorio", label: "Relatório", Icon: IconFileText },
  { href: "/sistema", label: "Sistema", Icon: IconSettings },
];

export function Sidebar({ email, clube }: { email: string; clube?: string | null }) {
  const pathname = usePathname();
  const router = useRouter();

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
          {clube && (
            <div style={{ fontSize: "0.68rem", color: cores.textoSuave, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {clube}
            </div>
          )}
        </div>
      </div>

      {/* Navegação */}
      <nav style={{ display: "flex", flexDirection: "column", gap: 2, flex: 1 }}>
        {NAV.map(({ href, label, Icon }) => {
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
              <Icon size={17} className={ativo ? "" : ""} />
              {label}
            </Link>
          );
        })}

        <div style={{ height: 1, background: cores.borda, margin: `${espaco.md}px ${espaco.sm}px` }} />

        <Link
          href="/upload"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: `${espaco.sm}px ${espaco.md}px`,
            borderRadius: raio.sm,
            fontSize: "0.83rem",
            fontWeight: 600,
            color: cores.sucesso,
            background: "rgba(34,197,94,0.08)",
            textDecoration: "none",
          }}
        >
          <IconUpload size={17} />
          Carregar dados
        </Link>
      </nav>

      {/* Utilizador */}
      <div style={{ borderTop: `1px solid ${cores.borda}`, paddingTop: espaco.md, marginTop: espaco.md }}>
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
