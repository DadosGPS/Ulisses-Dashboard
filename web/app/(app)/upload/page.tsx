"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { PageHeader } from "@/components/layout/PageHeader";
import { ImportadorRobusto } from "@/components/upload/ImportadorRobusto";
import { cores, espaco } from "@/lib/theme";

export default function UploadPage() {
  const [teamId, setTeamId] = useState<string | null>(null);
  const [carregado, setCarregado] = useState(false);

  useEffect(() => {
    async function carregarEquipa() {
      const supabase = createClient();
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        const { data } = await supabase
          .from("team_members")
          .select("team_id")
          .eq("user_id", user.id)
          .limit(1)
          .single();
        if (data) setTeamId(data.team_id);
      }
      setCarregado(true);
    }
    carregarEquipa();
  }, []);

  return (
    <div>
      <PageHeader
        titulo="Importar dados GPS"
        subtitulo="Analisa as colunas, revê o que foi detetado e só depois grava."
      />
      <main style={{ maxWidth: 900, padding: espaco.xxl }}>
        {!carregado ? (
          <p style={{ color: cores.textoSuave, fontSize: "0.85rem" }}>A carregar…</p>
        ) : !teamId ? (
          <p style={{ color: cores.textoSuave, fontSize: "0.85rem" }}>
            Ainda não estás associado a nenhuma equipa.
          </p>
        ) : (
          <ImportadorRobusto teamId={teamId} />
        )}
      </main>
    </div>
  );
}
