import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { Sidebar } from "@/components/layout/Sidebar";
import { FiltroGlobal } from "@/components/layout/FiltroGlobal";
import { PrivacidadeProvider } from "@/lib/privacidade";
import { cores } from "@/lib/theme";

interface Filtros {
  jogadores: string[];
  microciclos: number[];
  dias_md: string[];
}

async function obterFiltros(teamId: string, accessToken: string): Promise<Filtros> {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/filtros`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      cache: "no-store",
    });
    if (!res.ok) return { jogadores: [], microciclos: [], dias_md: [] };
    return res.json();
  } catch {
    return { jogadores: [], microciclos: [], dias_md: [] };
  }
}

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  // Opções do filtro global (jogadores, microciclos, dias) para a barra
  // partilhada. Falha graciosamente para uma barra vazia se algo correr mal.
  let filtros: Filtros = { jogadores: [], microciclos: [], dias_md: [] };
  const { data: { session } } = await supabase.auth.getSession();
  if (session) {
    const { data: membro } = await supabase
      .from("team_members")
      .select("team_id")
      .eq("user_id", session.user.id)
      .limit(1)
      .single();
    if (membro) {
      filtros = await obterFiltros(membro.team_id, session.access_token);
    }
  }

  return (
    <PrivacidadeProvider>
      <div style={{ display: "flex", minHeight: "100vh", background: cores.bg }}>
        <Sidebar email={user.email ?? ""} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <FiltroGlobal jogadores={filtros.jogadores} microciclos={filtros.microciclos} diasMd={filtros.dias_md} />
          {children}
        </div>
      </div>
    </PrivacidadeProvider>
  );
}
