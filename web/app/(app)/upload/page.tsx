"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { PageHeader } from "@/components/layout/PageHeader";

interface ResultadoIngest {
  status: string;
  upload_id?: string;
  jogadores?: number;
  sessoes_gravadas?: number;
  exercicios_gravados?: number;
}

export default function UploadPage() {
  const [teamId, setTeamId] = useState<string | null>(null);
  const [ficheiro, setFicheiro] = useState<File | null>(null);
  const [aEnviar, setAEnviar] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [resultado, setResultado] = useState<ResultadoIngest | null>(null);

  useEffect(() => {
    async function carregarEquipa() {
      const supabase = createClient();
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (!user) return;

      const { data } = await supabase
        .from("team_members")
        .select("team_id")
        .eq("user_id", user.id)
        .limit(1)
        .single();

      if (data) setTeamId(data.team_id);
    }
    carregarEquipa();
  }, []);

  async function submeter(e: React.FormEvent) {
    e.preventDefault();
    if (!ficheiro || !teamId) return;

    setAEnviar(true);
    setErro(null);
    setResultado(null);

    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (!session) {
      setErro("A tua sessão expirou — atualiza a página e entra outra vez.");
      setAEnviar(false);
      return;
    }

    const formData = new FormData();
    formData.append("team_id", teamId);
    formData.append("file", ficheiro);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/ingest`, {
        method: "POST",
        headers: { Authorization: `Bearer ${session.access_token}` },
        body: formData,
      });

      const dados = await res.json();
      if (!res.ok) {
        setErro(dados.detail || "Não foi possível processar o ficheiro.");
      } else {
        setResultado(dados);
      }
    } catch {
      setErro("Não foi possível ligar à API. Confirma que o serviço FastAPI está a correr.");
    } finally {
      setAEnviar(false);
    }
  }

  return (
    <div>
      <PageHeader titulo="Carregar dados" subtitulo='Excel ou CSV com a folha "BD_Carga" — mesmo formato usado na app anterior.' />
    <main style={{ maxWidth: 560, padding: "32px" }}>
      <form
        onSubmit={submeter}
        style={{
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: 14,
          padding: 24,
        }}
      >
        <input
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={(e) => setFicheiro(e.target.files?.[0] ?? null)}
          style={{ color: "rgba(255,255,255,0.85)", fontSize: "0.85rem" }}
        />

        <button
          type="submit"
          disabled={!ficheiro || aEnviar}
          style={{
            display: "block",
            marginTop: 20,
            padding: "11px 20px",
            background: !ficheiro || aEnviar ? "rgba(230,57,70,0.4)" : "#e63946",
            border: "none",
            borderRadius: 8,
            color: "white",
            fontWeight: 700,
            fontSize: "0.9rem",
            cursor: !ficheiro || aEnviar ? "default" : "pointer",
          }}
        >
          {aEnviar ? "A carregar…" : "Carregar ficheiro"}
        </button>
      </form>

      {erro && (
        <div
          style={{
            marginTop: 18,
            padding: "12px 16px",
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: 8,
            color: "#ef4444",
            fontSize: "0.85rem",
          }}
        >
          {erro}
        </div>
      )}

      {resultado && (
        <div
          style={{
            marginTop: 18,
            padding: "16px 18px",
            background: "rgba(34,197,94,0.08)",
            border: "1px solid rgba(34,197,94,0.3)",
            borderRadius: 10,
          }}
        >
          <p style={{ color: "#22c55e", fontWeight: 700, marginBottom: 8 }}>
            ✅ Ficheiro carregado com sucesso!
          </p>
          <p style={{ fontSize: "0.85rem", color: "rgba(255,255,255,0.75)" }}>
            {resultado.jogadores} jogadores · {resultado.sessoes_gravadas} sessões gravadas
            {resultado.exercicios_gravados ? ` · ${resultado.exercicios_gravados} exercícios` : ""}
          </p>
          <Link
            href="/dashboard"
            style={{ display: "inline-block", marginTop: 12, color: "#e63946", fontSize: "0.85rem" }}
          >
            Ver Dashboard →
          </Link>
        </div>
      )}
    </main>
    </div>
  );
}
