"use client";

import { createClient } from "@/lib/supabase/client";

/** Pedido autenticado à API a partir de um componente cliente. Lança um Error
 * com a mensagem da API (campo `detail`) quando a resposta não é 2xx. */
export async function pedidoApi<T = unknown>(caminho: string, metodo = "GET", corpo?: unknown): Promise<T> {
  const { data: { session } } = await createClient().auth.getSession();
  if (!session) throw new Error("Sessão expirada. Volta a entrar.");
  const r = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${caminho}`, {
    method: metodo,
    headers: { Authorization: `Bearer ${session.access_token}`, "Content-Type": "application/json" },
    body: corpo === undefined ? undefined : JSON.stringify(corpo),
  });
  const j = await r.json().catch(() => null);
  if (!r.ok) throw new Error(j?.detail ?? "Não foi possível concluir o pedido.");
  return j as T;
}
