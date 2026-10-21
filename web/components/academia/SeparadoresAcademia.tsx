"use client";

import { useEffect, useState } from "react";
import { pedidoApi } from "@/lib/api-cliente";
import { Separadores } from "@/components/layout/Separadores";

const ORDEM = ["Sub-15", "Sub-16", "Sub-17", "Sub-19"];

/** Separadores da Academia: Jogadores + um por equipa (época atual, se houver). */
export function SeparadoresAcademia() {
  const [tabs, setTabs] = useState([{ href: "/academia", label: "Jogadores" }]);
  useEffect(() => {
    pedidoApi<{ disponivel: boolean; epoca_atual: string; academias: { equipas: { team_id: string; escalao: string | null; epoca: string | null; rotulo: string }[] }[] }>("/api/academia")
      .then((d) => {
        const todas = (d.academias?.[0]?.equipas ?? []).filter((e) => e.escalao);
        const atuais = todas.filter((e) => e.epoca === d.epoca_atual);
        const lista = (atuais.length ? atuais : todas)
          .sort((a, b) => ORDEM.indexOf(a.escalao ?? "") - ORDEM.indexOf(b.escalao ?? ""));
        setTabs([{ href: "/academia", label: "Jogadores" },
          ...lista.map((e) => ({ href: `/academia/equipa/${e.team_id}`, label: atuais.length ? e.escalao! : e.rotulo }))]);
      })
      .catch(() => {});
  }, []);
  return <Separadores tabs={tabs} />;
}
