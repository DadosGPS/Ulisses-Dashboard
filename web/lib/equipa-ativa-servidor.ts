import { cookies } from "next/headers";
import { COOKIE_EQUIPA, escolherEquipa } from "@/lib/equipa-ativa";

/** Lado do servidor (Server Components): equipa ativa pelo cookie. */
export async function obterEquipaAtiva(supabase: unknown, userId: string) {
  const jar = await cookies();
  return escolherEquipa(supabase, userId, jar.get(COOKIE_EQUIPA)?.value);
}
