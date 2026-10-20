"use client";

import Link from "next/link";
import { cores, espaco, raio, sombra } from "@/lib/theme";
import { PageHeader } from "@/components/layout/PageHeader";
import { IconActivity, IconCalendar, IconSettings, IconUser, IconUsers } from "@/components/icons/Icons";

const SECCOES = [
  { href: "/configuracoes/academia", titulo: "Academia", texto: "Escalões e épocas, criar a época seguinte e trocar de equipa", Icon: IconCalendar },
  { href: "/configuracoes/equipa", titulo: "Equipa", texto: "Nome e desporto da equipa ativa", Icon: IconUsers },
  { href: "/configuracoes/jogadores", titulo: "Jogadores", texto: "Adicionar, editar e gerir o plantel e a disponibilidade", Icon: IconUser },
  { href: "/configuracoes/limites", titulo: "Limites e alertas", texto: "Limiares que disparam os alertas e a prontidão", Icon: IconSettings },
  { href: "/sistema", titulo: "Dados e sistema", texto: "Histórico de importações e qualidade dos dados", Icon: IconActivity },
];

export default function SettingsPage() {
  return (
    <div>
      <PageHeader titulo="Definições" subtitulo="Academia, equipa, jogadores, limites e dados" />
      <div style={{ padding: `${espaco.xl}px ${espaco.xxl}px ${espaco.xxl * 2}px`, maxWidth: 1100 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: espaco.md }}>
          {SECCOES.map(({ href, titulo, texto, Icon }) => (
            <Link key={href} href={href} className="lm-cartao-link"
              style={{ display: "block", textDecoration: "none", background: cores.bgCartao, border: `1px solid ${cores.borda}`, borderRadius: raio.md, boxShadow: sombra.cartao, padding: espaco.lg }}>
              <span style={{ display: "flex", color: cores.textoSuave, marginBottom: espaco.md }}><Icon size={20} /></span>
              <span style={{ display: "block", fontSize: "0.92rem", fontWeight: 600, color: cores.textoForte, marginBottom: 4 }}>{titulo}</span>
              <span style={{ display: "block", fontSize: "0.8rem", color: cores.textoSuave, lineHeight: 1.45 }}>{texto}</span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
