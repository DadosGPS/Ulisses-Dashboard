import { RespostaJogador } from "@/components/ui/RespostaJogador";

export const metadata = { title: "Resposta rápida", robots: { index: false, follow: false } };

export default async function RespostaPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  return <RespostaJogador token={token} />;
}
