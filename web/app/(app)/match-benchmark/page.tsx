import { redirect } from "next/navigation";

/** Página antiga — o planeamento passou a ser feito por microciclos e no calendário. */
export default function MatchBenchmarkAntigo() {
  redirect("/planeamento");
}
