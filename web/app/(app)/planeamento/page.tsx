import { redirect } from "next/navigation";

/** Planear abre no Calendário; links antigos com ?mc= (microciclos) vão para a Época. */
export default async function PlaneamentoRedirect({ searchParams }: { searchParams: Promise<Record<string, string>> }) {
  const params = await searchParams;
  const q = new URLSearchParams(params).toString();
  redirect(params.mc ? `/planeamento/epoca?${q}` : `/planeamento/calendario${q ? `?${q}` : ""}`);
}
