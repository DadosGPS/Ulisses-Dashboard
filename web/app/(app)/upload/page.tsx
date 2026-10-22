"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { PageHeader } from "@/components/layout/PageHeader";
import { ImportadorRobusto } from "@/components/upload/ImportadorRobusto";
import { cores, espaco } from "@/lib/theme";

import { obterEquipaAtivaCliente } from "@/lib/equipa-ativa";
import { useTr } from "@/lib/i18n/cliente";
export default function UploadPage() {
  const tr = useTr();
  const [teamId, setTeamId] = useState<string | null>(null);
  const [carregado, setCarregado] = useState(false);

  useEffect(() => {
    async function carregarEquipa() {
      const supabase = createClient();
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        const { data } = await obterEquipaAtivaCliente(supabase, user.id);
        if (data) setTeamId(data.team_id);
      }
      setCarregado(true);
    }
    carregarEquipa();
  }, []);

  return (
    <div>
      <PageHeader
        titulo={tr("Importar dados GPS")}
        subtitulo={tr("Analisa as colunas, revê o que foi detetado e só depois grava.")}
      />
      <main style={{ maxWidth: 900, padding: espaco.xxl }}>
        {!carregado ? (
          <p style={{ color: cores.textoSuave, fontSize: "0.85rem" }}>{tr("A carregar…")}</p>
        ) : !teamId ? (
          <p style={{ color: cores.textoSuave, fontSize: "0.85rem" }}>
            {tr("Ainda não estás associado a nenhuma equipa.")}</p>
        ) : (
          <ImportadorRobusto teamId={teamId} />
        )}
      </main>
    </div>
  );
}
