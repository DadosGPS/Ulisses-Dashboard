import Link from "next/link";
import { cores, espaco, raio, sombra } from "@/lib/theme";
import { IconCalendar, IconClock, IconUsers, IconActivity } from "@/components/icons/Icons";

const FUNCIONALIDADES = [
  {
    Icon: IconCalendar,
    titulo: "Análise de microciclo",
    descricao: "Carga semanal total, monotonia e strain da equipa.",
    href: "/analise",
  },
  {
    Icon: IconClock,
    titulo: "Análise por dia",
    descricao: "Filtra a carga e o PSE por dia do microciclo (MD-5 a MD).",
    href: "/analise",
  },
  {
    Icon: IconUsers,
    titulo: "Ranking de atletas",
    descricao: "Quem carrega mais e quem carrega menos, por semana ou por dia.",
    href: "/analise",
  },
  {
    Icon: IconActivity,
    titulo: "Gestão de risco (ACWR)",
    descricao: "Acompanha o rácio carga aguda/crónica de cada atleta.",
    href: "/equipa",
  },
];

export default function InicioPage() {
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
          width: 60,
          height: 60,
          borderRadius: raio.md,
          background: `linear-gradient(135deg, ${cores.cargaInterna}, ${cores.destaque})`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "1.6rem",
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

      <p style={{ fontSize: "0.95rem", color: cores.textoSuave, margin: `${espaco.md}px 0 0`, maxWidth: 460 }}>
        Monitorização da carga de treino de uma equipa de futebol.
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
          gap: espaco.md,
          maxWidth: 780,
          width: "100%",
          margin: `${espaco.xxl}px 0`,
        }}
      >
        {FUNCIONALIDADES.map(({ Icon, titulo, descricao, href }) => (
          <Link
            key={titulo}
            href={href}
            style={{
              display: "block",
              textAlign: "left",
              textDecoration: "none",
              background: cores.bgCartao,
              border: `1px solid ${cores.borda}`,
              borderRadius: raio.md,
              boxShadow: sombra.cartao,
              padding: espaco.lg,
            }}
          >
            <div style={{ color: cores.cargaInterna, width: 20 }}>
              <Icon size={20} />
            </div>
            <div
              className="font-display"
              style={{ fontSize: "0.86rem", fontWeight: 700, color: "white", margin: `${espaco.sm}px 0 4px` }}
            >
              {titulo}
            </div>
            <div style={{ fontSize: "0.76rem", color: cores.textoSuave, lineHeight: 1.4 }}>{descricao}</div>
          </Link>
        ))}
      </div>

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
