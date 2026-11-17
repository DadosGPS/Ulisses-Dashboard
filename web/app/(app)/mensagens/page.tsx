import { redirect } from "next/navigation";

// O separador «Mensagens aos Jogadores» foi retirado: o wellness e a PSE
// chegam agora pelos formulários/folhas do Google (página Importar GPS).
// Links antigos vão para o Hoje.
export default function MensagensPage() {
  redirect("/hoje");
}
