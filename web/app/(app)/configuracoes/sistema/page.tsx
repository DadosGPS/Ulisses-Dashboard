import { redirect } from "next/navigation";

/** Diagnóstico do sistema e estado dos dados vivem na página /sistema (real). */
export default function ConfigSistemaPage() {
  redirect("/sistema");
}
