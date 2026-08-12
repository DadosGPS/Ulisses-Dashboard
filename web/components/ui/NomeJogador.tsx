"use client";

import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";

/** Mostra o nome real ou "Atleta N" consoante o Modo Privado (ver Sidebar). */
export function NomeJogador({ nome }: { nome: string }) {
  const { oculto } = usePrivacidade();
  return <>{nomeOuOculto(nome, oculto)}</>;
}
