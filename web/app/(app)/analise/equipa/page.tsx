import { redirect } from "next/navigation";

/** Esta rota mostrava dados de equipa inventados, duplicando a página /equipa
 * (real). Redireciona para evitar informação repetida e falsa. */
export default function AnaliseEquipaPage() {
  redirect("/equipa");
}
