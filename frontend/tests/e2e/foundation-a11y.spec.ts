import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

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
});

test.afterEach(async ({ page }) => {
  expect(browserFailures.get(page)).toEqual({ consoleErrors: [], pageErrors: [] });
});

for (const theme of ["light", "dark"] as const) {
  test(`axe não encontra violações críticas ou sérias no tema ${theme}`, async ({ page }) => {
    await page.goto("/");
    if (theme === "dark") {
      await page.evaluate(() => document.documentElement.classList.add("dark"));
    }

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    const blocking = results.violations.filter(({ impact }) => impact === "critical" || impact === "serious");
    const uncertainContrast = results.incomplete.filter(({ id }) => id === "color-contrast");

    expect(blocking).toEqual([]);
    expect(uncertainContrast).toEqual([]);
  });
}
