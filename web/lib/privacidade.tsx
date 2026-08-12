"use client";

import { createContext, useContext, useEffect, useState } from "react";

const CHAVE = "loadmonitor.modoPrivado";

const PrivacidadeContext = createContext<{ oculto: boolean; alternar: () => void }>({
  oculto: false,
  alternar: () => {},
});

export function PrivacidadeProvider({ children }: { children: React.ReactNode }) {
  const [oculto, setOculto] = useState(false);

  useEffect(() => {
    setOculto(localStorage.getItem(CHAVE) === "1");
  }, []);

  function alternar() {
    setOculto((atual) => {
      const novo = !atual;
      localStorage.setItem(CHAVE, novo ? "1" : "0");
      return novo;
    });
  }

  return <PrivacidadeContext.Provider value={{ oculto, alternar }}>{children}</PrivacidadeContext.Provider>;
}

export function usePrivacidade() {
  return useContext(PrivacidadeContext);
}

/** Número estável derivado do nome — o mesmo jogador dá sempre o mesmo
 * "Atleta N" em todas as páginas, sem precisar de um registo partilhado. */
export function idAnonimo(nome: string): number {
  let h = 0;
  for (let i = 0; i < nome.length; i++) h = (Math.imul(h, 31) + nome.charCodeAt(i)) >>> 0;
  return (h % 99) + 1;
}

export function nomeOuOculto(nome: string, oculto: boolean): string {
  return oculto ? `Atleta ${idAnonimo(nome)}` : nome;
}
