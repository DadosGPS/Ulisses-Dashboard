"use client";

import { cores } from "@/lib/theme";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { loadUserTeam } from "@/lib/supabase/auth-utils";
import { useStore } from "@/lib/store";
import { useTr } from "@/lib/i18n/cliente";
import { TrocaLingua } from "@/components/layout/TrocaLingua";
import { LogoCompleto } from "@/components/layout/Logo";

export default function LoginPage() {
  const tr = useTr();
  const router = useRouter();
  const { setUser } = useStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [aCarregar, setACarregar] = useState(false);

  async function submeter(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    setACarregar(true);

    const supabase = createClient();
    const { error } = await supabase.auth.signInWithPassword({ email, password });

    setACarregar(false);
    if (error) {
      setErro(tr("Email ou password incorretos."));
      return;
    }

    // Load user's team ID after successful login
    const userData = await loadUserTeam();
    if (userData) {
      setUser({
        teamId: userData.teamId,
        email: userData.email,
        isLoading: false,
      });
    }

    // Depois de entrar: o destino pedido (ex.: um convite) ou um convite pendente.
    let destino = new URLSearchParams(window.location.search).get("next") || "";
    if (!destino.startsWith("/") || destino.startsWith("//")) destino = "";
    if (!destino) {
      try {
        const t = localStorage.getItem("lm-convite");
        if (t) destino = `/convite/${t}`;
      } catch {}
    }
    router.push(destino || "/inicio");
    router.refresh();
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
      }}
    >
      <TrocaLingua />
      <form
        onSubmit={submeter}
        style={{
          width: "100%",
          maxWidth: 380,
          background: "rgb(var(--ink) / 0.02)",
          border: "1px solid rgb(var(--ink) / 0.08)",
          borderRadius: 14,
          padding: 28,
        }}
      >
        <div style={{ marginBottom: 22 }}><LogoCompleto tamanho={38} /></div>
        <h1 style={{ fontSize: "1.3rem", fontWeight: 700, margin: "0 0 20px" }}>
          {tr("Entrar")}</h1>

        <label style={{ display: "block", fontSize: "0.78rem", color: "rgb(var(--ink) / 0.6)", marginBottom: 6 }}>
          {tr("Email")}</label>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={inputStyle}
        />

        <label style={{ display: "block", fontSize: "0.78rem", color: "rgb(var(--ink) / 0.6)", margin: "14px 0 6px" }}>
          {tr("Password")}</label>
        <input
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          style={inputStyle}
        />

        {erro && (
          <p style={{ color: "#ef4444", fontSize: "0.82rem", marginTop: 12 }}>{erro}</p>
        )}

        <button type="submit" disabled={aCarregar} style={botaoStyle}>
          {aCarregar ? tr("A entrar…") : tr("Entrar")}
        </button>

        <p style={{ fontSize: "0.8rem", color: "rgb(var(--ink) / 0.5)", marginTop: 18, textAlign: "center" }}>
          {tr("Ainda não tens conta?")}{" "}<Link href="/signup" style={{ color: "#e63946" }}>{tr("Criar conta")}</Link>
        </p>
      </form>
    </main>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "10px 12px",
  background: "rgb(var(--ink) / 0.04)",
  border: "1px solid rgb(var(--ink) / 0.12)",
  borderRadius: 8,
  color: cores.textoForte,
  fontSize: "0.9rem",
};

const botaoStyle: React.CSSProperties = {
  width: "100%",
  marginTop: 22,
  padding: "11px 0",
  background: cores.acento,
  border: "none",
  borderRadius: 8,
  color: cores.sobreAcento,
  fontWeight: 700,
  fontSize: "0.9rem",
  cursor: "pointer",
};
