"use client";

import { useEffect } from "react";
import { useStore } from "./store";
import { loadUserTeam } from "./supabase/auth-utils";

/**
 * Hook que carrega os dados do utilizador (teamId, email) ao montar.
 * Chamado em layouts e páginas protegidas.
 */
export function useLoadUser() {
  const { user, setUser } = useStore();

  useEffect(() => {
    if (!user.teamId) {
      setUser({ isLoading: true });
      loadUserTeam().then((userData) => {
        if (userData) {
          setUser({
            teamId: userData.teamId,
            email: userData.email,
            isLoading: false,
          });
        } else {
          setUser({ isLoading: false });
        }
      });
    }
  }, [user.teamId, setUser]);

  return user;
}
