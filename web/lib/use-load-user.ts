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
    // Confirma sempre a equipa ativa (cookie do seletor): a equipa guardada no
    // browser pode ser de outra sessão ou de outro dispositivo. Só mostra
    // "a carregar" quando ainda não há nenhuma equipa conhecida.
    if (!user.teamId) setUser({ isLoading: true });
    loadUserTeam().then((userData) => {
      if (userData) {
        if (userData.teamId !== useStore.getState().user.teamId || useStore.getState().user.isLoading) {
          setUser({ teamId: userData.teamId, email: userData.email, isLoading: false });
        }
      } else {
        setUser({ isLoading: false });
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return user;
}
