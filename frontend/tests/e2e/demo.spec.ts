import { expect, test } from "@playwright/test";

// E2E_BASE_URL tests a deployed/combined server (site + API on one address), e.g. http://127.0.0.1:7860
const API = process.env.E2E_BASE_URL || "http://localhost:8000";
const APR2 = "2026-04-02_la-mesa-expanded-da-2026-16";

test.beforeAll(async ({ request }) => {
  // replay mode: every LLM answer comes from the warmed cache, no network
  await request.post(`${API}/api/settings/provider`, { data: { mode: "replay" } });
  await request.post(`${API}/api/demo/reset`, { data: { fast_forward_to: APR2 } });
  await expect
    .poll(async () => (await (await request.get(`${API}/api/demo/status`)).json()).running, { timeout: 60_000 })
    .toBe(false);
});

test.afterAll(async ({ request }) => {
  await request.post(`${API}/api/settings/provider`, { data: { mode: "auto" } });
});

test("demo path: story -> Jun 16 -> Jun 18 -> avocado truck -> hold -> chat", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error" && !/hmr|WebSocket|tiles|basemaps|Failed to load resource/i.test(m.text())) errors.push(m.text());
  });

  // Story screen
  await page.goto("/");
  await expect(page.getByText("no commercial agriculture")).toBeVisible();
  const next = page.getByRole("button", { name: "Next", exact: true });
  await next.click();
  await expect(page.getByText("acres", { exact: true })).toBeVisible();
  await next.click();
  await expect(page.getByText(/read by hand/)).toBeVisible();
  await next.click();
  await page.getByRole("link", { name: /Launch Command Center/ }).click();
  await expect(page).toHaveURL(/\/app\/?$/);

  const counter = page.getByTestId("flag-counter");

  // Process the June 16 notice
  await expect(page.getByRole("button", { name: /New notice received/ })).toBeVisible();
  await page.keyboard.press("n");
  await expect(counter).toHaveAttribute("data-value", "3", { timeout: 90_000 });
  const afterJun16 = Number(await counter.getAttribute("data-value"));

  // Process the June 18 notice: counter increases
  await page.keyboard.press("n");
  await expect(counter).toHaveAttribute("data-value", "4", { timeout: 90_000 });
  expect(4).toBeGreaterThan(afterJun16);

  // SR-1007 shows Needs review
  await page.getByRole("tab", { name: "Loads" }).click();
  const row = page.getByTestId("row-SR-1007");
  await expect(row).toContainText("Needs review");
  await expect(row).toContainText("New");

  // Drawer: verified quote, then Hold
  await row.click();
  const drawer = page.getByRole("dialog");
  await expect(drawer.getByText(/Hass/).first()).toBeVisible();
  await drawer.getByText(/Rule evidence/).click();
  await expect(drawer.getByText("verified", { exact: true }).first()).toBeVisible();
  await drawer.getByRole("button", { name: "Hold shipment" }).click();
  await expect(page.getByText("SR-1007: Shipment on hold")).toBeVisible();
  await page.keyboard.press("Escape");

  // Chat: frozen pulp question -> citation chip, no certainty claim
  await page.getByRole("tab", { name: "Ask" }).click();
  await page.getByLabel("Question").fill("Can I ship frozen avocado pulp from El Cajon?");
  await page.getByRole("button", { name: "Send" }).click();
  const answer = page.getByTestId("chat-answer").last();
  await expect(answer).toHaveAttribute("data-done", "true", { timeout: 60_000 });
  await expect(answer.getByTestId("cite-chip").first()).toBeVisible();
  await expect(answer).toContainText(/don't settle|confirm/i);
  await expect(answer).not.toContainText(/\b(cleared|approved for shipment|safe to ship)\b/i);

  expect(errors, errors.join("\n")).toEqual([]);
});
