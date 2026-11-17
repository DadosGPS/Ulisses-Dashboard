"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { pedidoApi } from "@/lib/api-cliente";

const CHAVE = "lm-sync-fontes";
const INTERVALO_MS = 10 * 60 * 1000;

/** Ao abrir a app (e no máximo a cada 10 min), pede à API para voltar a ler as
 * folhas do Google Sheets (PSE e wellness) se a última leitura tiver mais de
 * 20 min. Se entrou algo novo, atualiza a página aberta. Não mostra nada. */
export function SincronizarFontes({ teamId }: { teamId: string }) {
  const router = useRouter();
  useEffect(() => {
    let ultima = 0;
    try { ultima = Number(sessionStorage.getItem(`${CHAVE}:${teamId}`) ?? 0); } catch { /* sem storage */ }
    if (Date.now() - ultima < INTERVALO_MS) return;
    try { sessionStorage.setItem(`${CHAVE}:${teamId}`, String(Date.now())); } catch { /* ignora */ }
    pedidoApi<{ sincronizadas: number }>(`/api/teams/${teamId}/google-sheets/sincronizar-se-preciso`, "POST")
      .then((r) => { if (r.sincronizadas > 0) router.refresh(); })
      .catch(() => { /* a página Importar mostra o erro */ });
  }, [teamId, router]);
  return null;
}
