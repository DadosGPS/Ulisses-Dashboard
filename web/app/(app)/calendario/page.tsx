import { redirect } from "next/navigation";

/** O Calendário passou a ser um separador de Planear. */
export default async function CalendarioRedirect({ searchParams }: { searchParams: Promise<Record<string, string>> }) {
  const q = new URLSearchParams(await searchParams).toString();
  redirect(`/planeamento/calendario${q ? `?${q}` : ""}`);
}
