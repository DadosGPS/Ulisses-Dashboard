import { test, type BrowserContext } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

/**
 * Capturas de ecrã de todas as páginas, em tema claro e escuro, para rever o
 * aspeto da app de uma vez (coerência de letra, cores e espaços). Só corre com
 * CAPTURAS=1 (o CI liga-o e guarda as imagens como artefacto «capturas»).
 */
const RAIZ = path.resolve(__dirname, "../../e2e");
const SAIDA = path.resolve(__dirname, "../capturas");
const sessao = JSON.parse(fs.readFileSync(path.join(RAIZ, "sessao.json"), "utf8")) as { cookie: string };
const dados = JSON.parse(fs.readFileSync(path.join(RAIZ, "dados.json"), "utf8")) as { equipas: Record<string, string> };
const SUPABASE = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "http://127.0.0.1:54321";
const COOKIE_SESSAO = `sb-${new URL(SUPABASE).hostname.split(".")[0]}-auth-token`;
const EQ = dados.equipas["Sub-15"];

const PAGINAS: [string, string][] = [
  ["hoje", "/hoje"],
  ["prontidao", "/hoje/prontidao"],
  ["treino", "/relatorios/treino"],
  ["jogo", "/relatorios/jogo"],
  ["semana", "/planeamento/semana"],
  ["calendario", "/planeamento/calendario"],
  ["planeamento-epoca", "/planeamento/epoca"],
  ["exercicios", "/planeamento/exercicios"],
  ["pse", "/analise"],
  ["carga-externa", "/carga-externa"],
  ["ce-epoca", "/carga-externa/epoca"],
  ["ce-comparacao", "/carga-externa/comparacao"],
  ["ce-posicao", "/carga-externa/posicao"],
  ["ce-tendencias", "/carga-externa/tendencias"],
  ["ce-combinada", "/carga-externa/combinada"],
  ["ce-velocidade", "/carga-externa/velocidade"],
  ["jogador", "/jogadores"],
  ["lesoes", "/lesoes"],
  ["regresso", "/regresso"],
  ["perfil", "/perfil"],
  ["academia", "/academia"],
  ["academia-equipa", `/academia/equipa/${EQ}`],
  ["academia-testes", `/academia/equipa/${EQ}/testes`],
  ["upload", "/upload"],
  ["verificacao", "/relatorios/verificacao"],
  ["definicoes", "/configuracoes"],
  ["limites", "/configuracoes/limites"],
];

async function entrar(context: BrowserContext, baseURL: string, tema: "light" | "dark") {
  await context.addCookies([
    { name: COOKIE_SESSAO, value: sessao.cookie, url: baseURL },
    { name: "lm-lingua", value: "pt", url: baseURL },
  ]);
  await context.addInitScript((t) => { try { localStorage.setItem("lm-tema", t); } catch { /* */ } }, tema);
}

test.describe("capturas", () => {
  test.skip(!process.env.CAPTURAS, "só com CAPTURAS=1");
  for (const tema of ["light", "dark"] as const) {
    for (const [nome, rota] of PAGINAS) {
      test(`${nome} · ${tema}`, async ({ page, context, baseURL }) => {
        await entrar(context, baseURL!, tema);
        await page.goto(rota, { waitUntil: "networkidle" });
        await page.waitForTimeout(1200); // gráficos e pedidos feitos depois do primeiro desenho
        fs.mkdirSync(SAIDA, { recursive: true });
        await page.screenshot({ path: path.join(SAIDA, `${nome}-${tema}.png`), fullPage: true });
      });
    }
  }
});
