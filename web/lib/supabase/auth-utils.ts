"use client";

import { createClient } from "./client";

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

    // Get user's team from team_members table
    const { data: teamMembers, error: teamError } = await supabase
      .from("team_members")
      .select("team_id")
      .eq("user_id", user.id)
      .single();

    if (teamError || !teamMembers) {
      console.error("Erro ao carregar equipa:", teamError);
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
