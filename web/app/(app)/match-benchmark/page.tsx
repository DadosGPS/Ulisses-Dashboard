import { redirect } from "next/navigation";

/** O Match Benchmark passou a ser um separador do Planeamento. */
export default function MatchBenchmarkAntigo() {
  redirect("/planeamento/benchmark");
}
