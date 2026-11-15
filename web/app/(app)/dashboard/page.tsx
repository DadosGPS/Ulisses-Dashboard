import { redirect } from "next/navigation";

/** O Centro de Controlo foi integrado no Hoje (para agir), nos relatórios de
 * treino e na Semana (exposição vs jogo). Ligações antigas vão para o Hoje. */
export default function DashboardPage() {
  redirect("/hoje");
}
