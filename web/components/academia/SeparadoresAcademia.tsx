"use client";

import { useEffect, useState } from "react";
import { pedidoApi } from "@/lib/api-cliente";
import { Separadores } from "@/components/layout/Separadores";
import { useTr } from "@/lib/i18n/cliente";

const ORDEM = ["Sub-15", "Sub-16", "Sub-17", "Sub-19"];

/** Separadores da Academia: Jogadores, um por equipa (época atual, se houver)
 * e, com mais de uma equipa, Comparar equipas. */
export function SeparadoresAcademia() {
  const tr = useTr();
  const comparar = { href: "/academia/comparar", label: tr("Comparar equipas") };
  const [tabs, setTabs] = useState<{ href: string; label: string; prefixo?: boolean }[]>([{ href: "/academia", label: tr("Jogadores") }, comparar]);
  useEffect(() => {
    pedidoApi<{ disponivel: boolean; epoca_atual: string; academias: { equipas: { team_id: string; escalao: string | null; epoca: string | null; rotulo: string }[] }[] }>("/api/academia")
      .then((d) => {
        const todas = (d.academias?.[0]?.equipas ?? []).filter((e) => e.escalao);
        const atuais = todas.filter((e) => e.epoca === d.epoca_atual);
        const lista = (atuais.length ? atuais : todas)
          .sort((a, b) => ORDEM.indexOf(a.escalao ?? "") - ORDEM.indexOf(b.escalao ?? ""));
        setTabs([{ href: "/academia", label: tr("Jogadores") },
          ...lista.map((e) => ({ href: `/academia/equipa/${e.team_id}`, label: atuais.length ? e.escalao! : e.rotulo, prefixo: true })),
          ...(lista.length > 1 ? [comparar] : [])]);
      })
      .catch(() => {});
  }, []);
  return <Separadores tabs={tabs} />;
}
