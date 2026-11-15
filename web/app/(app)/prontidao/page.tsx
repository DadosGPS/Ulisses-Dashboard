import { redirect } from "next/navigation";

/** A Prontidão passou a ser um separador do Hoje. */
export default function ProntidaoPage() {
  redirect("/hoje/prontidao");
}
