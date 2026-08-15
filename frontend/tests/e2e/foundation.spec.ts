import { expect, test, type Page } from "@playwright/test";

const governedViewports = {
  "desktop-chromium": { height: 900, width: 1440 },
  "mobile-chromium": { height: 844, width: 390 },
} as const;

type BrowserFailures = Readonly<{
  consoleErrors: string[];
  pageErrors: string[];
}>;

const browserFailures = new WeakMap<Page, BrowserFailures>();

test.beforeEach(async ({ page }) => {
  const failures: BrowserFailures = { consoleErrors: [], pageErrors: [] };
  browserFailures.set(page, failures);
  page.on("console", (message) => {
    if (message.type() === "error") failures.consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => failures.pageErrors.push(error.message));
  await page.goto("/");
});

test.afterEach(async ({ page }) => {
  expect(browserFailures.get(page)).toEqual({ consoleErrors: [], pageErrors: [] });
});

test("captura a foundation como artifact diagnóstico", async ({ page }, testInfo) => {
  const expectedViewport = governedViewports[testInfo.project.name as keyof typeof governedViewports];
  expect(page.viewportSize()).toEqual(expectedViewport);
  await expect(page.getByRole("heading", { level: 1, name: "Frontend MVP" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Estados estruturais" })).toBeVisible();

  const documentWidth = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(documentWidth.scroll).toBeLessThanOrEqual(documentWidth.client);

  await testInfo.attach(`foundation-${testInfo.project.name}`, {
    body: await page.screenshot({ animations: "disabled", fullPage: true }),
    contentType: "image/png",
  });
});

test("percorre foco, diálogo e retorno ao acionador por teclado", async ({ page }) => {
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Pular para o conteudo" })).toBeFocused();

  const trigger = page.getByRole("button", { name: "Revisar ação destrutiva" });
  for (let step = 0; step < 8 && !(await trigger.evaluate((element) => element === document.activeElement)); step += 1) {
    await page.keyboard.press("Tab");
  }
  await expect(trigger).toBeFocused();
  await page.keyboard.press("Enter");

  const dialog = page.getByRole("dialog", { name: "Confirmar intenção" });
  await expect(dialog).toBeVisible();
  await expect(dialog.locator(":focus")).toBeVisible();
  for (let step = 0; step < 6; step += 1) {
    await page.keyboard.press("Tab");
    expect(await dialog.evaluate((element) => element.contains(document.activeElement))).toBe(true);
  }
  await page.keyboard.press("Shift+Tab");
  expect(await dialog.evaluate((element) => element.contains(document.activeElement))).toBe(true);
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(trigger).toBeFocused();

  await expect(page.getByRole("button", { name: "Indisponível" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Processando exemplo…" })).toHaveAttribute("aria-busy", "true");
});

test("mantém foco visível, overflow contido e motion reduzido", async ({ page }) => {
  const primary = page.getByRole("button", { name: "Ação principal" });
  await primary.focus();
  const focusStyle = await primary.evaluate((element) => {
    const style = getComputedStyle(element);
    return { style: style.outlineStyle, width: Number.parseFloat(style.outlineWidth) };
  });
  expect(focusStyle.style).not.toBe("none");
  expect(focusStyle.width).toBeGreaterThanOrEqual(3);

  await page.emulateMedia({ reducedMotion: "reduce" });
  const motionSample = page.locator("[data-motion-sample]");
  const duration = await motionSample.evaluate((element) => getComputedStyle(element).transitionDuration);
  expect(Number.parseFloat(duration)).toBeLessThanOrEqual(0.001);

  const trigger = page.getByRole("button", { name: "Revisar ação destrutiva" });
  const dialog = page.getByRole("dialog", { name: "Confirmar intenção" });
  await trigger.click();
  for (const slot of ["dialog-overlay", "dialog-content"]) {
    const animationDuration = await page.locator(`[data-slot="${slot}"]`).evaluate(
      (element) => Number.parseFloat(getComputedStyle(element).animationDuration),
    );
    expect(animationDuration).toBeLessThanOrEqual(0.001);
  }
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(trigger).toBeFocused();

  const overflow = page.getByRole("region", { name: "Mapa de tokens da foundation" });
  await overflow.focus();
  await expect(overflow).toBeFocused();
  if (page.viewportSize()?.width === 390) {
    const dimensions = await overflow.evaluate((element) => ({
      client: element.clientWidth,
      scroll: element.scrollWidth,
    }));
    expect(dimensions.scroll).toBeGreaterThan(dimensions.client);
    await page.keyboard.press("ArrowRight");
    await expect.poll(() => overflow.evaluate((element) => element.scrollLeft)).toBeGreaterThan(0);
  }
});
