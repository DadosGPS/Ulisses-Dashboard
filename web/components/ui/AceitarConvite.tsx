"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { pedidoApi } from "@/lib/api-cliente";
import { definirEquipaAtiva } from "@/lib/equipa-ativa";
import { cores, espaco, raio } from "@/lib/theme";
import { estiloBotao } from "@/components/ui/base";
import { useTr } from "@/lib/i18n/cliente";
import { TrocaLingua } from "@/components/layout/TrocaLingua";

interface Convite {
  academia: string; papel: string; papel_rotulo: string; equipas: string[]; email: string | null;
  convidado_por: string; expira_em: string; estado: "valido" | "aceite" | "expirado" | "revogado"; nome: string | null;
}

/** Página pública do link de convite: mostra o convite e deixa entrar/criar conta e aceitar. */
export function AceitarConvite({ token }: { token: string }) {
  const tr = useTr();
  const [convite, setConvite] = useState<Convite | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null | undefined>(undefined);
  const [aAceitar, setAAceitar] = useState(false);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/convites/${token}`)
      .then(async (r) => { const j = await r.json().catch(() => null); if (!r.ok) throw new Error(j?.detail ?? tr("Convite inválido.")); return j; })
      .then(setConvite).catch((e) => setErro(e.message));
    createClient().auth.getSession().then(({ data }) => setEmail(data.session?.user.email ?? null));
    try { localStorage.setItem("lm-convite", token); } catch {}
  }, [token]);

  async function aceitar() {
    setErro(null);
    setAAceitar(true);
    try {
      const r = await pedidoApi<{ team_id: string | null }>(`/api/convites/${token}/aceitar`, "POST");
      try { localStorage.removeItem("lm-convite"); } catch {}
      if (r.team_id) definirEquipaAtiva(r.team_id);
      window.location.href = "/dashboard";
    } catch (e) {
      setErro(e instanceof Error ? e.message : tr("Não foi possível aceitar."));
      setAAceitar(false);
    }
  }

  const estados: Record<string, string> = { aceite: "Este convite já foi usado.", expirado: "Este convite expirou — pede um novo a quem te convidou.", revogado: "Este convite foi cancelado." };

  return (
    <main style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: 24, background: cores.bg }}>
      <TrocaLingua />
      <div style={{ width: "100%", maxWidth: 420, background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.lg, padding: 28 }}>
        <div style={{ fontSize: "0.7rem", fontWeight: 700, color: cores.acento, letterSpacing: "0.08em", textTransform: "uppercase" }}>{tr("Convite")}</div>
        {!convite && !erro && <p style={{ color: cores.textoSuave }}>{tr("A carregar…")}</p>}
        {convite && (
          <>
            <h1 style={{ fontSize: "1.25rem", margin: "6px 0 4px", color: cores.textoForte }}>{convite.academia}</h1>
            <p style={{ fontSize: "0.88rem", color: cores.texto, lineHeight: 1.5, margin: 0 }}>
              {convite.convidado_por} {tr("convidou-te")}{convite.nome ? `, ${convite.nome},` : ""} {tr("como")}{" "}<strong>{convite.papel_rotulo}</strong>.
            </p>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", margin: `${espaco.md}px 0` }}>
              {convite.equipas.map((e) => <span key={e} style={{ fontSize: "0.78rem", border: `1px solid ${cores.bordaForte}`, borderRadius: 999, padding: "2px 10px", color: cores.texto }}>{e}</span>)}
            </div>
            {convite.estado !== "valido" ? (
              <p style={{ color: cores.perigo, fontSize: "0.86rem" }}>{tr(estados[convite.estado] ?? "")}</p>
            ) : email === undefined ? null : email ? (
              <>
                <p style={{ fontSize: "0.82rem", color: cores.textoSuave }}>{tr("Entraste como")}{" "}<strong style={{ color: cores.texto }}>{email}</strong>.</p>
                <button style={{ ...estiloBotao.primario, width: "100%", padding: "10px 0" }} disabled={aAceitar} onClick={aceitar}>
                  {aAceitar ? tr("A entrar na equipa…") : tr("Aceitar convite")}
                </button>
                <button style={{ ...estiloBotao.ligacao, marginTop: espaco.sm }} onClick={async () => { await createClient().auth.signOut(); setEmail(null); }}>
                  {tr("Não és tu? Terminar sessão")}</button>
              </>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: espaco.sm }}>
                <Link href={`/signup?convite=${token}`} style={{ ...estiloBotao.primario, textAlign: "center", textDecoration: "none", padding: "10px 0" }}>{tr("Criar conta")}</Link>
                <Link href={`/login?next=/convite/${token}`} style={{ ...estiloBotao.secundario, textAlign: "center", textDecoration: "none", padding: "10px 0" }}>{tr("Já tenho conta — entrar")}</Link>
                {convite.email && <p style={{ fontSize: "0.76rem", color: cores.textoSuave, margin: 0 }}>{tr("Usa o email")}{" "}{convite.email}.</p>}
              </div>
            )}
          </>
        )}
        {erro && <p style={{ color: cores.perigo, fontSize: "0.86rem", marginTop: espaco.md }}>{erro}</p>}
      </div>
    </main>
  );
}
