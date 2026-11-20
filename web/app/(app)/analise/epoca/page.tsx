import { redirect } from "next/navigation";

/** Este separador passou da Análise (PSE) para a Carga externa. */
export default async function Page({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(await searchParams)) {
    for (const x of Array.isArray(v) ? v : v != null ? [v] : []) sp.append(k, x);
  }
  const q = sp.toString();
  redirect(`/carga-externa/epoca${q ? `?${q}` : ""}`);
}
