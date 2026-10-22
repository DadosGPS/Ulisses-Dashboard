import { test, expect, type Page, type BrowserContext } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

/**
 * Abre cada página principal com sessão iniciada e dados fictícios
 * (e2e/semear.py) e falha se: a página redirecionar para o login, houver um
 * erro de JavaScript, a API responder 401/403/5xx, ou aparecer um erro no ecrã.
 */
const RAIZ = path.resolve(__dirname, "../../e2e");
const sessao = JSON.parse(fs.readFileSync(path.join(RAIZ, "sessao.json"), "utf8")) as { cookie: string };
const dados = JSON.parse(fs.readFileSync(path.join(RAIZ, "dados.json"), "utf8")) as { equipas: Record<string, string> };
const SUPABASE = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "http://127.0.0.1:54321";
const COOKIE_SESSAO = `sb-${new URL(SUPABASE).hostname.split(".")[0]}-auth-token`;
const EQ = dados.equipas["Sub-15"];

const PAGINAS: [string, RegExp][] = [
  ["/dashboard", /Centro de Controlo/],
  ["/prontidao", /Prontidão/],
  ["/planeamento", /Planeamento/],
  ["/calendario", /Calendário/],
  ["/carga-externa", /Carga Externa/],
  ["/analise", /Análise/],
  ["/analise/epoca", /Época/],
  ["/analise/comparacao", /Comparação de Jogadores/],
  ["/analise/posicao", /Comparação por Posição/],
  ["/analise/tendencias", /Tendências/],
  ["/analise/combinada", /Carga Externa × Interna/],
  ["/velocidade", /Limiares de Velocidade/],
  ["/lesoes", /Lesões e Disponibilidade/],
  ["/regresso", /Regresso ao Jogo/],
  ["/perfil", /Perfil dos Jogadores/],
  ["/jogadores", /Jogador/],
  ["/academia", /Academia · Jogadores/],
  ["/academia/comparar", /Comparar equipas/],
  [`/academia/equipa/${EQ}`, /Academia/],
  [`/academia/equipa/${EQ}/jogos`, /Academia/],
  [`/academia/equipa/${EQ}/relatorio`, /Academia/],
  ["/upload", /Importar dados GPS/],
  ["/mensagens", /Mensagens/],
  ["/configuracoes", /Definições/],
  ["/configuracoes/academia", /Definições · Academia/],
  ["/configuracoes/equipa", /Definições · Equipa/],
  ["/configuracoes/jogadores", /Definições · Jogadores/],
  ["/configuracoes/limites", /Definições · Limites e Alertas/],
  ["/sistema", /Sistema/],
];

const ERROS_NO_ECRA = /Application error|Unhandled Runtime Error|Não foi possível ligar à API|Could not connect to the API|Internal Server Error/;

async function entrar(context: BrowserContext, baseURL: string, lingua = "pt") {
  await context.addCookies([
    { name: COOKIE_SESSAO, value: sessao.cookie, url: baseURL },
    { name: "lm-lingua", value: lingua, url: baseURL },
  ]);
}

/** Vigia a página: erros de JavaScript e respostas falhadas da API. */
function vigiar(page: Page) {
  const problemas: string[] = [];
  page.on("pageerror", (e) => problemas.push(`Erro de JavaScript: ${e.message}`));
  page.on("response", (r) => {
    const s = r.status();
    if (r.url().includes("/api/") && (s === 401 || s === 403 || s >= 500)) problemas.push(`API ${s}: ${r.request().method()} ${r.url()}`);
  });
  return problemas;
}

for (const [rota, titulo] of PAGINAS) {
  test(`abre ${rota}`, async ({ page, context, baseURL }) => {
    await entrar(context, baseURL!);
    const problemas = vigiar(page);
    const resp = await page.goto(rota, { waitUntil: "networkidle" });
    expect(resp?.status(), "estado HTTP da página").toBeLessThan(400);
    expect(new URL(page.url()).pathname, "não deve voltar ao login").not.toBe("/login");
    await expect(page.locator("h1").first()).toContainText(titulo);
    await page.waitForTimeout(500); // pedidos feitos depois do primeiro desenho
    await expect(page.locator("body")).not.toContainText(ERROS_NO_ECRA);
    expect(problemas, problemas.join("\n")).toEqual([]);
  });
}

test("sem sessão vai para o login", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login/);
  await expect(page.locator("h1")).toContainText("LoadMonitorSystem");
});

test("em inglês", async ({ page, context, baseURL }) => {
  await entrar(context, baseURL!, "en");
  const problemas = vigiar(page);
  await page.goto("/dashboard", { waitUntil: "networkidle" });
  await expect(page.locator("h1").first()).toContainText("Control Centre");
  await page.goto("/academia/comparar", { waitUntil: "networkidle" });
  await expect(page.locator("h1").first()).toContainText("Compare teams");
  expect(problemas, problemas.join("\n")).toEqual([]);
});

test("adicionar um jogador à academia", async ({ page, context, baseURL }) => {
  await entrar(context, baseURL!);
  const problemas = vigiar(page);
  await page.goto("/academia", { waitUntil: "networkidle" });
  const nome = `Jogador E2E ${Date.now() % 100000}`;
  await page.getByPlaceholder("Nome e apelido").fill(nome);
  await page.locator('input[type="date"]').first().fill("2012-03-14");
  await page.getByRole("checkbox", { name: /Sub-15/ }).first().check();
  await page.getByRole("button", { name: "Adicionar jogador" }).click();
  await expect(page.getByText(`${nome} adicionado.`)).toBeVisible();
  await expect(page.getByRole("link", { name: nome })).toBeVisible();
  expect(problemas, problemas.join("\n")).toEqual([]);
});
