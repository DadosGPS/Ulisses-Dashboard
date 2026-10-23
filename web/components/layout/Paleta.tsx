"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { GRUPOS } from "@/components/layout/Sidebar";
import { IconSearch } from "@/components/icons/Icons";
import { pedidoApi } from "@/lib/api-cliente";
import { nomeOuOculto, usePrivacidade } from "@/lib/privacidade";
import { cores, raio, sombra } from "@/lib/theme";
import { useTr } from "@/lib/i18n/cliente";

type Opcao = { id: string; titulo: string; sub: string; href: string; tipo: "pagina" | "jogador" | "atleta" };

// Subpáginas que não estão no menu mas vale a pena encontrar pelo nome.
const SUBPAGINAS: { href: string; label: string; secao: string }[] = [
  { href: "/analise/epoca", label: "Época", secao: "Análise" },
  { href: "/analise/comparacao", label: "Comparar jogadores", secao: "Análise" },
  { href: "/analise/posicao", label: "Por posição", secao: "Análise" },
  { href: "/analise/tendencias", label: "Tendências", secao: "Análise" },
  { href: "/analise/combinada", label: "Externa × Interna", secao: "Análise" },
  { href: "/planeamento/semana", label: "Semana por jogador", secao: "Planeamento" },
  { href: "/planeamento/epoca", label: "Época (macrociclo)", secao: "Planeamento" },
  { href: "/planeamento/exercicios", label: "Biblioteca de exercícios", secao: "Planeamento" },
  { href: "/academia/comparar", label: "Comparar equipas", secao: "Academia" },
  { href: "/configuracoes/limites", label: "Limites e alertas", secao: "Definições" },
  { href: "/configuracoes/jogadores", label: "Jogadores", secao: "Definições" },
  { href: "/configuracoes/equipa", label: "Equipa técnica", secao: "Definições" },
  { href: "/configuracoes/academia", label: "Academia", secao: "Definições" },
];

export const normalizar = (s: string) => s.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** Ordena as opções pela pesquisa: todas as palavras têm de aparecer; as que
 * começam pela pesquisa vêm primeiro. */
export function filtrarOpcoes(opcoes: Opcao[], q: string): Opcao[] {
  const termos = normalizar(q).split(/\s+/).filter(Boolean);
  if (!termos.length) return opcoes.filter((o) => o.tipo === "pagina").slice(0, 12);
  return opcoes
    .map((o) => {
      const alvo = normalizar(`${o.titulo} ${o.sub}`);
      if (!termos.every((t) => alvo.includes(t))) return null;
      const titulo = normalizar(o.titulo);
      const pontos = (titulo.startsWith(termos[0]) ? 0 : titulo.includes(` ${termos[0]}`) ? 1 : 2) + (o.tipo === "pagina" ? 0 : 0.5);
      return { o, pontos };
    })
    .filter((x): x is { o: Opcao; pontos: number } => x !== null)
    .sort((a, b) => a.pontos - b.pontos || a.o.titulo.localeCompare(b.o.titulo))
    .slice(0, 12)
    .map((x) => x.o);
}

/** Pesquisa rápida (Ctrl+K / ⌘K): páginas, jogadores da equipa ativa e
 * fichas da academia. */
export function Paleta({ jogadores }: { jogadores: string[] }) {
  const tr = useTr();
  const router = useRouter();
  const { oculto } = usePrivacidade();
  const [aberta, setAberta] = useState(false);
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  const [atletas, setAtletas] = useState<{ atleta_id: string; nome: string; equipas: { escalao: string | null }[] }[] | null>(null);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setAberta((a) => !a); }
      else if (e.key === "Escape") setAberta(false);
    };
    const abrir = () => setAberta(true);
    window.addEventListener("keydown", tecla);
    window.addEventListener("lm-abrir-paleta", abrir);
    return () => { window.removeEventListener("keydown", tecla); window.removeEventListener("lm-abrir-paleta", abrir); };
  }, []);

  useEffect(() => {
    if (!aberta) return;
    setQ(""); setSel(0);
    setTimeout(() => input.current?.focus(), 0);
    if (atletas === null) {
      pedidoApi<{ atletas?: typeof atletas }>("/api/academia/atletas").then((d) => setAtletas(d.atletas ?? [])).catch(() => setAtletas([]));
    }
  }, [aberta, atletas]);

  const opcoes = useMemo<Opcao[]>(() => {
    const paginas: Opcao[] = [
      ...GRUPOS.flatMap((g) => g.itens.map((it) => ({ id: it.href, titulo: tr(it.label), sub: tr(g.titulo), href: it.href, tipo: "pagina" as const }))),
      { id: "/configuracoes", titulo: tr("Definições"), sub: "", href: "/configuracoes", tipo: "pagina" },
      ...SUBPAGINAS.map((p) => ({ id: p.href, titulo: tr(p.label), sub: tr(p.secao), href: p.href, tipo: "pagina" as const })),
    ];
    // Quem está no plantel ativo aparece uma vez (como jogador); a ficha da
    // academia só para os restantes.
    const daEquipa = new Set(jogadores.map(normalizar));
    return [
      ...paginas,
      ...jogadores.map((n) => ({ id: `j:${n}`, titulo: n, sub: tr("Jogador · carga e evolução"), href: `/jogadores?jogador=${encodeURIComponent(n)}`, tipo: "jogador" as const })),
      ...(atletas ?? []).filter((a) => !daEquipa.has(normalizar(a.nome))).map((a) => ({
        id: `a:${a.atleta_id}`, titulo: a.nome,
        sub: tr("Ficha da academia{0}", [a.equipas.length ? ` · ${a.equipas.map((e) => e.escalao).filter(Boolean).join(", ")}` : ""]),
        href: `/academia/atleta/${a.atleta_id}`, tipo: "atleta" as const,
      })),
    ];
  }, [jogadores, atletas, tr]);

  const lista = useMemo(() => filtrarOpcoes(opcoes, q), [opcoes, q]);
  useEffect(() => setSel(0), [q]);

  if (!aberta) return null;

  const ir = (o: Opcao | undefined) => {
    if (!o) return;
    setAberta(false);
    router.push(o.href);
  };

  return (
    <div role="dialog" aria-modal aria-label={tr("Procurar")} onMouseDown={() => setAberta(false)}
      style={{ position: "fixed", inset: 0, zIndex: 100, background: "rgb(0 0 0 / 0.45)", display: "flex", justifyContent: "center", alignItems: "flex-start", paddingTop: "12vh" }}>
      <div onMouseDown={(e) => e.stopPropagation()}
        style={{ width: "min(620px, calc(100vw - 32px))", background: cores.bgElevado, border: `1px solid ${cores.bordaForte}`, borderRadius: raio.md, boxShadow: sombra.elevado, overflow: "hidden" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "0 14px", borderBottom: `1px solid ${cores.borda}`, color: cores.textoSuave }}>
          <IconSearch size={18} />
          <input ref={input} value={q} onChange={(e) => setQ(e.target.value)} placeholder={tr("Procurar jogador ou página…")} aria-label={tr("Procurar jogador ou página…")}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") { e.preventDefault(); setSel((s) => Math.min(s + 1, lista.length - 1)); }
              else if (e.key === "ArrowUp") { e.preventDefault(); setSel((s) => Math.max(s - 1, 0)); }
              else if (e.key === "Enter") { e.preventDefault(); ir(lista[sel]); }
            }}
            style={{ flex: 1, height: 50, border: "none", outline: "none", background: "transparent", color: cores.textoForte, fontSize: "1rem" }} />
          <span style={{ fontSize: "0.7rem", border: `1px solid ${cores.borda}`, borderRadius: 4, padding: "1px 6px" }}>Esc</span>
        </div>
        <div role="listbox" style={{ maxHeight: 420, overflowY: "auto", padding: 6 }}>
          {lista.length === 0 && <div style={{ padding: 14, fontSize: "0.85rem", color: cores.textoSuave }}>{tr("Nada encontrado.")}</div>}
          {lista.map((o, i) => (
            <div key={o.id} role="option" aria-selected={i === sel} onMouseEnter={() => setSel(i)} onClick={() => ir(o)}
              style={{ display: "flex", alignItems: "center", gap: 10, padding: "9px 12px", borderRadius: 8, cursor: "pointer",
                background: i === sel ? cores.superficieHover : "transparent" }}>
              <span style={{ fontSize: "0.66rem", fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase", width: 64, flexShrink: 0,
                color: o.tipo === "pagina" ? cores.acento : o.tipo === "jogador" ? cores.sucesso : cores.textoSuave }}>
                {o.tipo === "pagina" ? tr("Página") : o.tipo === "jogador" ? tr("Jogador") : tr("Academia")}</span>
              <span style={{ fontSize: "0.9rem", color: cores.textoForte, fontWeight: 600 }}>{o.tipo === "pagina" ? o.titulo : nomeOuOculto(o.titulo, oculto)}</span>
              {o.sub && <span style={{ fontSize: "0.78rem", color: cores.textoSuave, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{o.sub}</span>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
