"use client";

import Link from "next/link";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";

/** Mostra o nome real ou "Atleta N" consoante o Modo Privado (ver Sidebar).
 * Com `ficha`, o nome abre a ficha do jogador (carga, wellness, testes). */
export function NomeJogador({ nome, ficha = false }: { nome: string; ficha?: boolean }) {
  const { oculto } = usePrivacidade();
  const texto = nomeOuOculto(nome, oculto);
  if (!ficha) return <>{texto}</>;
  return (
    <Link href={`/jogadores?jogador=${encodeURIComponent(nome)}`} title={oculto ? undefined : `Ficha de ${nome}`}
      className="link-ficha" style={{ color: "inherit", textDecoration: "none" }}>
      {texto}
    </Link>
  );
}
