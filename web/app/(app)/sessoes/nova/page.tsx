import { redirect } from "next/navigation";

/** A criação manual de sessão não está implementada (não gravava). Os dados
 * entram por importação de GPS em /upload. */
export default function SessoesNovaPage() {
  redirect("/upload");
}
