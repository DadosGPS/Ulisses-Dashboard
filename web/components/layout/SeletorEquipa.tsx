"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { definirEquipaAtiva } from "@/lib/equipa-ativa";
import { useStore } from "@/lib/store";
import { cores, raio } from "@/lib/theme";
import { useTr, linguaDoCookie } from "@/lib/i18n/cliente";

type Equipa = { team_id: string; rotulo: string; epoca: string | null };

/** Equipa ativa (escalão × época) e troca entre equipas. Com uma só equipa
 * mostra apenas o nome; com várias, um seletor agrupado por época. */
export function SeletorEquipa() {
  const tr = useTr();
  const teamId = useStore((s) => s.user.teamId);
  const setUser = useStore((s) => s.setUser);
  const [equipas, setEquipas] = useState<Equipa[]>([]);

  useEffect(() => {
    let vivo = true;
    (async () => {
      try {
        const { data: { session } } = await createClient().auth.getSession();
        if (!session) return;
        const r = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/academia`, { headers: { Authorization: `Bearer ${session.access_token}`, "X-Lingua": linguaDoCookie() } });
        if (r.ok && vivo) setEquipas((await r.json()).equipas ?? []);
      } catch {
        /* sem seletor se a API falhar — a app continua com a equipa atual */
      }
    })();
    return () => {
      vivo = false;
    };
  }, []);

  if (equipas.length === 0) return null;
  const atual = equipas.find((e) => e.team_id === teamId) ?? equipas[0];

  if (equipas.length === 1) {
    return <div style={{ ...caixa, color: cores.textoSuave }} title={tr("Equipa ativa")}>{atual.rotulo}</div>;
  }

  const epocas = [...new Set(equipas.map((e) => e.epoca ?? "Sem época"))];
  return (
    <select
      aria-label={tr("Equipa ativa")}
      value={atual.team_id}
      onChange={(e) => {
        definirEquipaAtiva(e.target.value);
        setUser({ teamId: e.target.value });
        // Numa página da equipa na Academia, passa para a mesma página da nova equipa.
        const m = window.location.pathname.match(/^\/academia\/equipa\/[^/]+(\/.*)?$/);
        if (m) window.location.href = `/academia/equipa/${e.target.value}${m[1] ?? ""}`;
        else window.location.reload();
      }}
      style={{ ...caixa, color: cores.textoForte, cursor: "pointer", appearance: "auto" }}
    >
      {epocas.map((ep) => (
        <optgroup key={ep} label={tr(ep)}>
          {equipas.filter((e) => (e.epoca ?? "Sem época") === ep).map((e) => (
            <option key={e.team_id} value={e.team_id}>{e.rotulo}</option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}

const caixa: React.CSSProperties = {
  width: "100%",
  height: 34,
  padding: "0 10px",
  borderRadius: raio.sm,
  border: `1px solid ${cores.borda}`,
  background: cores.superficie,
  fontSize: "0.82rem",
  fontWeight: 600,
  display: "flex",
  alignItems: "center",
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
};
