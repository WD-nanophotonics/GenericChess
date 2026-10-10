import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";
import fs from "node:fs";

async function start(
  page: Page,
  title: string,
  mode = "与 AI 对弈",
  human = "先手",
) {
  await page.goto("/");
  await page.getByRole("button", { name: "开始一局", exact: true }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: title, exact: true })
    .click();
  await page.getByLabel("对局方式").selectOption({ label: mode });
  if (mode === "与 AI 对弈")
    await page.getByLabel("我的位置").selectOption({ label: human });
  await page.getByRole("button", { name: "开始对局", exact: true }).click();
  await expect(page.getByRole("grid", { name: "棋盘" })).toBeVisible();
}
async function state(page: Page) {
  const id = await page.evaluate(() => localStorage.getItem("gc-last-game"));
  return (await page.request.get(`/api/games/${id}`)).json();
}
async function settled(page: Page) {
  await expect
    .poll(
      async () => {
        const s = await state(page);
        return s.actions.length > 0 && !s.ai.thinking && !s.ai.queued;
      },
      { timeout: 12000 },
    )
    .toBeTruthy();
  return state(page);
}
async function playOne(page: Page) {
  const s = await settled(page);
  const offer = s.actions.find(
    (o: any) => o.action.from && !o.action.promotion_target_id,
  );
  const coord = (p: number[]) => String.fromCharCode(97 + p[0]) + (p[1] + 1);
  await page.locator(`[data-square="${coord(offer.action.from)}"]`).click();
  await expect(page.locator(".selected-square")).toHaveCount(1);
  await page.locator(`[data-square="${coord(offer.action.to)}"]`).click();
  await expect.poll(async () => (await state(page)).ply).toBeGreaterThan(s.ply);
  return s.ply;
}

for (const title of ["国际象棋", "将棋", "生成棋", "混合生成棋"]) {
  test(`${title} real PVE, history, undo, save/resume, terminal`, async ({
    page,
  }, info) => {
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await start(page, title);
    await playOne(page);
    await settled(page);
    let s = await state(page);
    expect(s.ply).toBe(2);
    await page.getByRole("button", { name: "初始局面", exact: false }).click();
    await expect(page.getByText("回看第 0 步", { exact: true })).toBeVisible();
    await expect(page.locator(".legal-dot")).toHaveCount(0);
    await page
      .getByRole("button", { name: "返回当前棋局", exact: true })
      .click();
    await page.getByRole("button", { name: "悔棋", exact: true }).click();
    await expect.poll(async () => (await state(page)).ply).toBe(0);
    await playOne(page);
    await settled(page);
    s = await state(page);
    await page.getByRole("button", { name: "对局菜单", exact: true }).click();
    const downloading = page.waitForEvent("download");
    await page.getByRole("button", { name: "导出续局包", exact: true }).click();
    const download = await downloading;
    const exportPath = info.outputPath("saved-bundle.json");
    await download.saveAs(exportPath);
    expect(
      JSON.parse(fs.readFileSync(exportPath, "utf8")).record.actions.length,
    ).toBe(2);
    await page.reload();
    await page.getByRole("button", { name: /继续上次对局/ }).click();
    await expect(page.getByRole("grid", { name: "棋盘" })).toBeVisible();
    expect((await state(page)).ply).toBe(s.ply);
    await page.getByRole("button", { name: "对局菜单", exact: true }).click();
    await page.getByRole("button", { name: "导入续局包", exact: true }).click();
    await page.locator('input[type="file"]').setInputFiles(exportPath);
    await expect
      .poll(async () => (await state(page)).revision)
      .toBeGreaterThan(s.revision);
    page.once("dialog", (dialog) => dialog.accept());
    await page.getByRole("button", { name: "认输", exact: true }).click();
    await expect(
      page.getByText("后手获胜", { exact: true }).first(),
    ).toBeVisible();
    expect((await state(page)).result.status).toBe("resignation");
    await page.screenshot({
      path: info.outputPath(`${title}-terminal.png`),
      fullPage: true,
    });
    expect(errors).toEqual([]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
  });
}

test("human second, touch/keyboard, flip and reduced motion", async ({
  page,
}) => {
  await start(page, "国际象棋", "与 AI 对弈", "后手");
  await settled(page);
  expect((await state(page)).ply).toBe(1);
  const before = await page
    .locator('[role="gridcell"]')
    .first()
    .getAttribute("data-square");
  await page.getByRole("button", { name: "翻转棋盘", exact: true }).click();
  expect(
    await page.locator('[role="gridcell"]').first().getAttribute("data-square"),
  ).not.toBe(before);
  await page
    .getByRole("button", { name: "切换减少动态效果", exact: true })
    .click();
  await expect(page.locator(".app")).toHaveClass(/reduce-motion/);
  await page.locator('[role="gridcell"]').first().focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.locator('[role="gridcell"]').nth(1)).toBeFocused();
  await playOne(page);
  await settled(page);
  expect((await state(page)).ply).toBe(3);
});

test("same-screen two players and browser reconnect", async ({
  page,
  context,
}) => {
  await start(page, "国际象棋", "同屏双人");
  await playOne(page);
  await playOne(page);
  expect((await state(page)).ply).toBe(2);
  await context.setOffline(true);
  await expect(
    page.getByText("连接已断开，正在恢复。未确认的操作不会自动重发。"),
  ).toBeVisible();
  await context.setOffline(false);
  await expect(
    page.getByText("连接已断开，正在恢复。未确认的操作不会自动重发。"),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "悔棋", exact: true }).click();
  await expect.poll(async () => (await state(page)).ply).toBe(1);
});

test("desktop and narrow-screen visual baseline", async ({ page }, info) => {
  await page.goto("/");
  await page.screenshot({
    path: info.outputPath("landing.png"),
    fullPage: true,
  });
  await start(page, "生成棋", "同屏双人");
  await page.getByRole("tab", { name: "规则", exact: true }).click();
  await page.screenshot({ path: info.outputPath("board.png"), fullPage: true });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
});

test("promotion choices, cancel, and captured-piece drops", async ({
  page,
}) => {
  await start(page, "国际象棋", "同屏双人");
  async function importRules(path: string) {
    await page.getByRole("button", { name: "对局菜单", exact: true }).click();
    await page.getByRole("button", { name: "导入规则", exact: true }).click();
    await page.locator('input[type="file"]').setInputFiles(path);
  }
  await importRules("tests/fixtures/promotion.json");
  await expect
    .poll(async () => (await state(page)).types.H !== undefined)
    .toBeTruthy();
  await page.locator('[data-square="e7"]').click();
  await page.locator('[data-square="e8"]').click();
  await expect(
    page.getByRole("dialog", { name: "选择这一步的变化" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "取消行动选择" }).click();
  expect((await state(page)).ply).toBe(0);
  await page.locator('[data-square="e8"]').click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: /升变为/ })
    .click();
  await expect
    .poll(async () =>
      (await state(page)).squares.some((s: any) => s.piece?.promoted),
    )
    .toBeTruthy();
  await importRules("tests/fixtures/drop.json");
  await expect.poll(async () => (await state(page)).board_size).toBe(4);
  await page.locator('[data-square="a1"]').click();
  await page.locator('[data-square="a2"]').click();
  await expect(page.getByRole("button", { name: "选择持子 R" })).toBeVisible();
  await playOne(page);
  const s = await settled(page);
  const drop = s.actions.find(
    (o: any) => o.action.kind === "drop" || o.action.kind === "semantic_drop",
  );
  await page.getByRole("button", { name: "选择持子 R" }).click();
  const to =
    String.fromCharCode(97 + drop.action.to[0]) + (drop.action.to[1] + 1);
  await page.locator(`[data-square="${to}"]`).click();
  await expect.poll(async () => (await state(page)).hands[0].length).toBe(0);
});
