import { redirect } from "next/navigation";

/** O assistente de importação anterior era uma maqueta. O importador real
 * (upload de CSV/XLSX → /api/ingest) está em /upload. */
export default function SessoesImportarPage() {
  redirect("/upload");
}
