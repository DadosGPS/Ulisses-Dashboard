import { createClient } from "@/lib/supabase/server";
import { obterEquipaAtiva } from "@/lib/equipa-ativa-servidor";
import { obterLingua } from "@/lib/i18n/servidor";

/** Sessão + equipa ativa para uma página do servidor (null se faltar alguma). */
export async function contextoEquipa(): Promise<{ teamId: string; token: string } | null | "sem_equipa"> {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return null;
  const { data: membro } = await obterEquipaAtiva(supabase, session.user.id);
  if (!membro) return "sem_equipa";
  return { teamId: membro.team_id, token: session.access_token };
}

/** GET autenticado à API a partir do servidor. Lança Error se não for 2xx. */
export async function getApi<T>(caminho: string, token: string, params: Record<string, string | undefined> = {}): Promise<T> {
  const url = new URL(`${process.env.NEXT_PUBLIC_API_URL}${caminho}`);
  for (const [k, v] of Object.entries(params)) if (v) url.searchParams.set(k, v);
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}`, "X-Lingua": await obterLingua() }, cache: "no-store" });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}
