import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { cores, espaco, raio } from "@/lib/theme";

export default async function InicioPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const { data: perfil } = user
    ? await supabase.from("profiles").select("clube, nome").eq("id", user.id).single()
    : { data: null };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        padding: espaco.xxl,
      }}
    >
      <div
        style={{
          width: 64,
          height: 64,
          borderRadius: raio.md,
          background: `linear-gradient(135deg, ${cores.cargaInterna}, ${cores.destaque})`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "1.7rem",
          fontWeight: 800,
          color: "white",
          marginBottom: espaco.lg,
        }}
      >
        L
      </div>

      <h1 className="font-display" style={{ fontSize: "2.1rem", fontWeight: 700, color: "white", margin: 0, letterSpacing: "-0.01em" }}>
        LoadMonitor
      </h1>

      {perfil?.clube && (
        <p style={{ fontSize: "1rem", color: cores.textoSuave, margin: `${espaco.sm}px 0 0` }}>{perfil.clube}</p>
      )}

      <p style={{ fontSize: "0.85rem", color: cores.textoFraco, margin: `${espaco.md}px 0 ${espaco.xxl}px`, maxWidth: 420 }}>
        Monitorização de carga, ACWR e planeamento — tudo num único lugar.
      </p>

      <Link
        href="/analise"
        style={{
          display: "inline-block",
          padding: "12px 28px",
          background: cores.cargaInterna,
          borderRadius: raio.sm,
          color: "white",
          fontWeight: 700,
          fontSize: "0.9rem",
          textDecoration: "none",
        }}
      >
        Ver Análise →
      </Link>
    </div>
  );
}
