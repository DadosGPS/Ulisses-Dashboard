import { AceitarConvite } from "@/components/ui/AceitarConvite";

export default async function ConvitePage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  return <AceitarConvite token={token} />;
}
