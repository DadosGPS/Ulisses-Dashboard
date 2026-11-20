"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { pedidoApi } from "@/lib/api-cliente";

const CHAVE = "lm-sync-fontes";
const INTERVALO_MS = 2 * 60 * 1000;

/** Ao abrir a app e sempre que se volta a ela (ex.: depois de escrever na
 * folha noutro separador), no máximo a cada 2 min, pede à API para voltar a
 * ler as folhas do Google Sheets (PSE e wellness) cuja última leitura tenha
 * mais de 2 min. Se leu alguma, atualiza a página aberta. Não mostra nada. */
export function SincronizarFontes({ teamId }: { teamId: string }) {
  const router = useRouter();
  useEffect(() => {
    const talvezSincronizar = () => {
      if (document.visibilityState === "hidden") return;
      let ultima = 0;
      try { ultima = Number(sessionStorage.getItem(`${CHAVE}:${teamId}`) ?? 0); } catch { /* sem storage */ }
      if (Date.now() - ultima < INTERVALO_MS) return;
      try { sessionStorage.setItem(`${CHAVE}:${teamId}`, String(Date.now())); } catch { /* ignora */ }
      pedidoApi<{ sincronizadas: number }>(`/api/teams/${teamId}/google-sheets/sincronizar-se-preciso`, "POST")
        .then((r) => { if (r.sincronizadas > 0) router.refresh(); })
        .catch(() => { /* a página Importar mostra o erro */ });
    };
    talvezSincronizar();
    window.addEventListener("focus", talvezSincronizar);
    document.addEventListener("visibilitychange", talvezSincronizar);
    return () => {
      window.removeEventListener("focus", talvezSincronizar);
      document.removeEventListener("visibilitychange", talvezSincronizar);
    };
  }, [teamId, router]);
  return null;
}
