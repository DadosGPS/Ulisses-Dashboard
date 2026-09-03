import { redirect } from "next/navigation";

/** Limiares de alerta configuráveis ainda não estão implementados (os alertas
 * usam limiares padrão). Encaminha para o hub de Definições até existir. */
export default function ConfigLimitesPage() {
  redirect("/configuracoes");
}
