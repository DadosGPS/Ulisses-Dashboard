/** Equipa ativa — a equipa (escalão × época) escolhida no seletor da barra
 * lateral, guardada num cookie para servidor e cliente lerem o mesmo valor.
 * Se o cookie não existir ou não for uma equipa do utilizador, usa a primeira. */
export const COOKIE_EQUIPA = "lm-equipa";

type Supa = {
  from: (t: string) => {
    select: (c: string) => { eq: (c: string, v: string) => PromiseLike<{ data: { team_id: string }[] | null }> };
  };
};

export async function escolherEquipa(supabase: unknown, userId: string, preferida: string | null | undefined) {
  const { data } = await (supabase as Supa).from("team_members").select("team_id").eq("user_id", userId);
  const ids = (data ?? []).map((r) => r.team_id);
  const team_id = preferida && ids.includes(preferida) ? preferida : ids[0];
  return { data: team_id ? { team_id } : null };
}

/** Lado do cliente (componentes "use client"). */
export async function obterEquipaAtivaCliente(supabase: unknown, userId: string) {
  const m = typeof document !== "undefined" ? document.cookie.match(new RegExp(`(?:^|; )${COOKIE_EQUIPA}=([^;]+)`)) : null;
  return escolherEquipa(supabase, userId, m ? decodeURIComponent(m[1]) : null);
}

export function definirEquipaAtiva(teamId: string) {
  document.cookie = `${COOKIE_EQUIPA}=${encodeURIComponent(teamId)}; path=/; max-age=${60 * 60 * 24 * 365}; samesite=lax`;
}
