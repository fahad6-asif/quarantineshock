// Screenshot helper (not a test): npx tsx tests/e2e/shots.ts <outdir>
import { chromium } from "@playwright/test";

const out = process.argv[2] || ".";
const API = "http://localhost:8000";

(async () => {
  await fetch(`${API}/api/settings/provider`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mode: "replay" }) });
  await fetch(`${API}/api/demo/reset`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ fast_forward_to: "2026-06-16_spring-valley-established" }) });
  for (;;) {
    const s = await (await fetch(`${API}/api/demo/status`)).json();
    if (!s.running) break;
    await new Promise((r) => setTimeout(r, 300));
  }
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1366, height: 768 } });
  await page.goto("http://localhost:3000/");
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${out}/1_story.png` });
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.waitForTimeout(2800);
  await page.screenshot({ path: `${out}/2_story_acres.png` });
  await page.goto("http://localhost:3000/app");
  await page.waitForTimeout(4000);
  await page.keyboard.press("n");
  await page.waitForTimeout(3500);
  await page.screenshot({ path: `${out}/3_running.png` });
  await page.getByTestId("flag-counter").and(page.locator('[data-value="4"]')).waitFor({ timeout: 60000 });
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${out}/4_after_jun18.png` });
  await page.getByText("Hass avos 40lb x 120").first().click();
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${out}/5_drawer.png` });
  await page.keyboard.press("Escape");
  await page.getByRole("tab", { name: "Ask" }).click();
  await page.getByLabel("Question").fill("Can I ship frozen avocado pulp from El Cajon?");
  await page.getByRole("button", { name: "Send" }).click();
  await page.getByTestId("chat-answer").last().and(page.locator('[data-done="true"]')).waitFor({ timeout: 60000 });
  await page.screenshot({ path: `${out}/6_chat.png` });
  await browser.close();
  await fetch(`${API}/api/settings/provider`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mode: "auto" }) });
})();
