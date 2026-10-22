"use client";

import { useEffect, useState } from "react";
import { useStore } from "./store";
import { loadUserTeam } from "./supabase/auth-utils";

/**
 * Hook que carrega os dados do utilizador (teamId, email) ao montar.
 * Chamado em layouts e páginas protegidas.
 */
export function useLoadUser() {
  const { user, setUser } = useStore();
  // Até a primeira confirmação terminar, conta como "a carregar": sem isto, num
  // browser sem equipa guardada (ex.: logo após aceitar um convite) a página
  // via teamId vazio e mandava para o login antes de a equipa chegar.
  const [confirmado, setConfirmado] = useState(false);

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
      setConfirmado(true);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return confirmado || user.teamId ? user : { ...user, isLoading: true };
}
