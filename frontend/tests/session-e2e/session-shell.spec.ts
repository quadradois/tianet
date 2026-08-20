import { expect, test, type Page } from "@playwright/test";

async function login(page: Page, institution = "ACME") {
  await page.goto("/login");
  await page.getByRole("textbox", { name: "Instituicao" }).fill(institution);
  await page.getByRole("textbox", { name: "E-mail" }).fill("operador@example.test");
  await page.getByLabel("Senha").fill("segredo-e2e");
  await page.getByRole("button", { name: "Entrar" }).click();
}

test.beforeEach(async ({ page }, testInfo) => {
  page.on("console", (message) => {
    const expectedNotFound = testInfo.title.includes("404") && message.text().includes("status of 404");
    if (message.type() === "error" && !expectedNotFound) throw new Error(`console error: ${message.text()}`);
  });
  page.on("pageerror", (error) => { throw error; });
});

test("renderiza login governado sem reescrever evidencia historica", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Acesse sua operacao" })).toBeVisible();
  expect((await page.locator("main#conteudo-principal").screenshot({ animations: "disabled", caret: "initial" })).byteLength).toBeGreaterThan(0);
});

test("login, contexto proprio e logout nao expõem tokens ao browser", async ({ page, context }) => {
  const browserRequests: string[] = [];
  page.on("request", (request) => browserRequests.push(request.url()));
  await login(page);
  await expect(page).toHaveURL(/\/app\?data_referencia=\d{4}-\d{2}-\d{2}$/);
  await expect(page.getByRole("heading", { name: "Inicio" })).toBeVisible();
  await expect(page.getByText("Instituicao ACME")).toBeVisible();
  await expect(page.getByText("Carteira Centro")).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Navegacao principal" }).getByRole("link", { name: "Devedores" })).toHaveAttribute("href", "/app/devedores");
  await expect(page.getByRole("navigation", { name: "Navegacao principal" }).getByRole("link", { name: /Comercial|Contratos|Motor|Agenda|Cobranca/i })).toHaveCount(0);
  const html = await page.content();
  expect(html).not.toMatch(/access-(?:ok|old|new)|refresh-acme/);
  expect(await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length }))).toEqual({ local: 0, session: 0 });
  const cookies = await context.cookies();
  expect(cookies).toHaveLength(1);
  expect(cookies[0]?.httpOnly).toBe(true);
  expect(cookies[0]?.value).not.toContain("access-ok");
  expect(browserRequests.every((url) => !url.startsWith("http://127.0.0.1:3201"))).toBe(true);
  expect((await page.locator("div.min-h-screen").first().screenshot({ animations: "disabled", caret: "initial" })).byteLength).toBeGreaterThan(0);
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect.poll(async () => (await context.cookies()).length).toBe(0);
});

test("401 dispara um bootstrap controlado e recupera a sessao", async ({ page }) => {
  await login(page, "EXPIRADO");
  await expect(page).toHaveURL(/\/app\?data_referencia=\d{4}-\d{2}-\d{2}$/, { timeout: 15_000 });
  await expect(page.getByText("Carteira Centro")).toBeVisible();
});

test("401 repetido executa no maximo um bootstrap e retorna ao login", async ({ page }) => {
  const bootstraps: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/auth/bootstrap") bootstraps.push(request.url());
  });
  const firstBootstrap = page.waitForRequest((request) => new URL(request.url()).pathname === "/api/auth/bootstrap");
  await login(page, "LOOP");
  await firstBootstrap;
  await expect(page).toHaveURL(/\/login$/, { timeout: 15_000 });
  expect(bootstraps).toHaveLength(1);
});

test("409 nao fabrica Carteira alternativa", async ({ page }) => {
  await login(page, "SEM-CARTEIRA");
  await expect(page.getByRole("heading", { name: "Contexto operacional indisponivel" })).toBeVisible();
  await expect(page.getByText(/Nenhuma Carteira alternativa foi escolhida/)).toBeVisible();
  await expect(page.getByText("Carteira Centro")).toHaveCount(0);
});

test("5xx mostra estado seguro e correlation sem detalhe interno", async ({ page }) => {
  await login(page, "FALHA");
  await expect(page.getByRole("heading", { name: "Servico temporariamente indisponivel" })).toBeVisible();
  await expect(page.getByText(/^Correlation ID: .+/)).toBeVisible();
  await expect(page.getByText(/stack secreta/)).toHaveCount(0);
});

test("404 permanece neutro", async ({ page }) => {
  await page.goto("/recurso-inexistente-289");
  await expect(page.getByRole("heading", { name: "Conteudo indisponivel" })).toBeVisible();
  await expect(page.getByText(/nao foi encontrado ou nao esta disponivel/)).toBeVisible();
});
