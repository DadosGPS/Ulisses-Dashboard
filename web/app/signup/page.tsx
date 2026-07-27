"use client";

import { useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";

export default function SignupPage() {
  const [nome, setNome] = useState("");
  const [clube, setClube] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [sucesso, setSucesso] = useState(false);
  const [aCarregar, setACarregar] = useState(false);

  async function submeter(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);

    if (password.length < 8) {
      setErro("A password deve ter pelo menos 8 caracteres.");
      return;
    }

    setACarregar(true);
    const supabase = createClient();
    // O trigger on_auth_user_created (supabase/migrations/0001_init.sql) cria
    // automaticamente profiles + teams + team_members a partir destes metadados.
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { nome, clube } },
    });

    setACarregar(false);
    if (error) {
      setErro(error.message);
      return;
    }
    setSucesso(true);
  }

  if (sucesso) {
    return (
      <main style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
        <div style={{ maxWidth: 380, textAlign: "center" }}>
          <h1 style={{ fontSize: "1.2rem", marginBottom: 12 }}>Verifica o teu email</h1>
          <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.9rem" }}>
            Enviámos um link de confirmação para <b>{email}</b>.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
      <form
        onSubmit={submeter}
        style={{
          width: "100%",
          maxWidth: 380,
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: 14,
          padding: 28,
        }}
      >
        <h1 style={{ fontSize: "1.3rem", fontWeight: 700, margin: "0 0 20px" }}>Criar conta</h1>

        <Campo label="Nome" value={nome} onChange={setNome} required />
        <Campo label="Clube" value={clube} onChange={setClube} />
        <Campo label="Email" value={email} onChange={setEmail} type="email" required />
        <Campo label="Password (mín. 8 caracteres)" value={password} onChange={setPassword} type="password" required />

        {erro && <p style={{ color: "#ef4444", fontSize: "0.82rem", marginTop: 12 }}>{erro}</p>}

        <button type="submit" disabled={aCarregar} style={botaoStyle}>
          {aCarregar ? "A criar…" : "Criar conta"}
        </button>

        <p style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.5)", marginTop: 18, textAlign: "center" }}>
          Já tens conta? <Link href="/login" style={{ color: "#e63946" }}>Entrar</Link>
        </p>
      </form>
    </main>
  );
}

function Campo({
  label,
  value,
  onChange,
  type = "text",
  required = false,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  required?: boolean;
}) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{ display: "block", fontSize: "0.78rem", color: "rgba(255,255,255,0.6)", marginBottom: 6 }}>
        {label}
      </label>
      <input
        type={type}
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{
          width: "100%",
          padding: "10px 12px",
          background: "rgba(255,255,255,0.04)",
          border: "1px solid rgba(255,255,255,0.12)",
          borderRadius: 8,
          color: "white",
          fontSize: "0.9rem",
        }}
      />
    </div>
  );
}

const botaoStyle: React.CSSProperties = {
  width: "100%",
  marginTop: 8,
  padding: "11px 0",
  background: "#e63946",
  border: "none",
  borderRadius: 8,
  color: "white",
  fontWeight: 700,
  fontSize: "0.9rem",
  cursor: "pointer",
};
