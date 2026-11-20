"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { PageHeader } from "@/components/layout/PageHeader";
import { ImportadorRobusto } from "@/components/upload/ImportadorRobusto";
import { LigacaoGoogleSheets } from "@/components/upload/LigacaoGoogleSheets";
import { cores, espaco, letra } from "@/lib/theme";

import { obterEquipaAtivaCliente } from "@/lib/equipa-ativa";
import { useTr } from "@/lib/i18n/cliente";
import { Carregando } from "@/components/ui/Esqueleto";
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
          <Carregando cartoes={0} linhas={4} padding={false} />
        ) : !teamId ? (
          <p style={{ color: cores.textoSuave, fontSize: letra.texto }}>
            {tr("Ainda não estás associado a nenhuma equipa.")}</p>
        ) : (
          <>
            <LigacaoGoogleSheets teamId={teamId} tipo="pse" />
            <LigacaoGoogleSheets teamId={teamId} tipo="wellness" />
            <ImportadorRobusto teamId={teamId} />
          </>
        )}
      </main>
    </div>
  );
}
