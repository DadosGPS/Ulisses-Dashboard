import { redirect } from "next/navigation";

/** Página antiga (Z-score por posição), retirada — redireciona para a Análise. */
export default function AvancadoAntigo() {
  redirect("/analise");
}
