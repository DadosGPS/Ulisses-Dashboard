"use client";

import { createClient } from "@/lib/supabase/client";
import { linguaDoCookie } from "@/lib/i18n/cliente";

/** Pedido autenticado à API a partir de um componente cliente. Lança um Error
 * com a mensagem da API (campo `detail`) quando a resposta não é 2xx. */
export async function pedidoApi<T = unknown>(caminho: string, metodo = "GET", corpo?: unknown): Promise<T> {
  const { data: { session } } = await createClient().auth.getSession();
  if (!session) throw new Error(linguaDoCookie() === "en" ? "Session expired. Please sign in again." : "Sessão expirada. Volta a entrar.");
  const r = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${caminho}`, {
    method: metodo,
    headers: { Authorization: `Bearer ${session.access_token}`, "Content-Type": "application/json", "X-Lingua": linguaDoCookie() },
    body: corpo === undefined ? undefined : JSON.stringify(corpo),
  });
  const j = await r.json().catch(() => null);
  if (!r.ok) throw new Error(j?.detail ?? (linguaDoCookie() === "en" ? "The request could not be completed." : "Não foi possível concluir o pedido."));
  return j as T;
}
