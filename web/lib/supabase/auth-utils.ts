"use client";

import { createClient } from "./client";

import { obterEquipaAtivaCliente } from "@/lib/equipa-ativa";
/**
 * Carrega os dados do utilizador autenticado e a sua equipa.
 * Chama-se após login ou ao carregar a aplicação.
 */
export async function loadUserTeam() {
  const supabase = createClient();
  
  try {
    // Get authenticated user
    const {
      data: { user },
      error: userError,
    } = await supabase.auth.getUser();

    if (userError || !user) {
      return null;
    }

    // Equipa ativa (a escolhida no seletor, ou a primeira do utilizador)
    const { data: teamMembers } = await obterEquipaAtivaCliente(supabase, user.id);

    if (!teamMembers) {
      console.error("Erro ao carregar equipa: utilizador sem equipa");
      return null;
    }

    return {
      userId: user.id,
      email: user.email,
      teamId: teamMembers.team_id,
    };
  } catch (error) {
    console.error("Erro ao carregar utilizador e equipa:", error);
    return null;
  }
}
