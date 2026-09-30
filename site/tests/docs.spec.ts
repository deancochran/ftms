import { expect, test } from "@playwright/test";

test("landing, quickstarts and generated API work beneath /ftms", async ({ page }) => {
  const failures: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  page.on("response", (response) => {
    if (response.url().startsWith("http://127.0.0.1:4322") && response.status() >= 400) {
      failures.push(`${response.status()} ${response.url()}`);
    }
  });
  await page.goto("/ftms/");
  await expect(
    page.getByRole("heading", { name: "FTMS Protocol Libraries", exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Get started", exact: true }).click();
  await expect(page).toHaveURL(/\/ftms\/start\/typescript\/$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("TypeScript / JavaScript");
  await expect(page.getByText("speedMps=10 cadenceRpm=90", { exact: false })).toBeVisible();
  await page.goto("/ftms/start/c/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("C / C++");
  await page.goto("/ftms/start/dart/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Dart / Flutter");
  await page.goto("/ftms/start/go/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Go");
  await page.goto("/ftms/start/csharp/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("C# / .NET (alpha)");
  await page.goto("/ftms/project/releasing/");
  await expect(
    page.getByRole("heading", { name: "Coordinated release checklist", exact: true }),
  ).toBeVisible();
  await page.goto("/ftms/reference/api/");
  await page.getByRole("link", { name: "Open the generated TypeScript API reference" }).click();
  await expect(page).toHaveURL(/\/ftms\/api\/typescript\/$/);
  await expect(
    page.getByRole("heading", { name: "FTMS TypeScript API", exact: true }),
  ).toBeVisible();
  expect(failures).toEqual([]);
});

test("production search loads and finds a canonical guide", async ({ page }) => {
  await page.goto("/ftms/");
  await page.getByRole("button", { name: /Search/ }).click();
  await page.getByRole("textbox", { name: "Search", exact: true }).fill("troubleshooting");
  const result = page
    .locator(".pagefind-ui__result-link")
    .filter({ hasText: "Troubleshooting" })
    .first();
  await expect(result).toBeVisible();
  await result.click();
  await expect(page).toHaveURL(/\/ftms\/integration\/troubleshooting\//);
});

test("theme, navigation and narrow layout retain usable controls", async ({ page, isMobile }) => {
  await page.goto("/ftms/integration/cookbook/");
  if (isMobile) await page.getByRole("button", { name: "Menu", exact: true }).click();
  const theme = page.getByRole("combobox", { name: "Select theme" });
  await theme.selectOption("dark");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await theme.selectOption("light");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.getByRole("link", { name: "Transport recipes", exact: true }).first().click();
  await expect(page).toHaveURL(/\/ftms\/integration\/transports\/$/);
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(overflow).toBe(false);
});
