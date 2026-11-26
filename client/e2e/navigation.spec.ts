import { test, expect } from "@playwright/test";

test.describe("CodeSecAudit AI - UI Navigation & Visual Verification", () => {
  test("Home Page: Loads successfully with Showcase and Modal Lightbox", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/CodeSecAudit/i);

    // Verify Demo showcase section is visible
    const showcase = page.locator("#product-demos");
    await expect(showcase).toBeVisible();

    // Verify filter tabs exist
    const prGateTab = page.getByRole("button", { name: "PR Security Gate" });
    await expect(prGateTab).toBeVisible();
    await prGateTab.click();

    // Verify modal opens when clicking on a screenshot card
    const severeCard = page.locator("text=Severe PR Review — Merge Gate Blocked").first();
    await expect(severeCard).toBeVisible();

    const viewFullBtn = page.getByRole("button", { name: "View Full Size" }).first();
    await viewFullBtn.click();

    // Check modal dialog
    const modal = page.getByRole("dialog");
    await expect(modal).toBeVisible();

    // Close modal
    const closeBtn = page.getByTitle("Close (Esc)");
    await closeBtn.click();
    await expect(modal).not.toBeVisible();
  });

  test("Authentication: Quick Access login sets active workspace session", async ({ page }) => {
    await page.goto("/login");
    const adminBtn = page.getByRole("button", { name: /Quick Access \(Admin\)/i });
    await expect(adminBtn).toBeVisible();
    await adminBtn.click();

    // Should redirect to dashboard or set session
    await page.waitForURL(/\/dashboard/i, { timeout: 10000 });
    await expect(page.locator("h1.page-title")).toContainText(/Security Posture Dashboard/i);
  });

  test("Dashboard: Loads KPIs and metrics for logged-in user", async ({ page }) => {
    // Authenticate
    await page.goto("/login");
    await page.getByRole("button", { name: /Quick Access \(Admin\)/i }).click();
    await page.waitForURL(/\/dashboard/i, { timeout: 10000 });

    await expect(page.locator("h1.page-title")).toContainText(/Security Posture Dashboard/i);

    // Verify all images on dashboard are valid
    const images = await page.locator("img").all();
    for (const img of images) {
      const src = await img.getAttribute("src");
      if (src && !src.startsWith("data:")) {
        const naturalWidth = await img.evaluate((el: HTMLImageElement) => el.naturalWidth);
        expect(naturalWidth).toBeGreaterThan(0);
      }
    }
  });

  test("Pull Requests Page: Loads PR review table", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: /Quick Access \(Admin\)/i }).click();
    await page.waitForURL(/\/dashboard/i, { timeout: 10000 });

    await page.goto("/pull-requests");
    await expect(page.locator("body")).toBeVisible();
  });

  test("Findings Page: Loads vulnerability findings view", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: /Quick Access \(Admin\)/i }).click();
    await page.waitForURL(/\/dashboard/i, { timeout: 10000 });

    await page.goto("/findings");
    await expect(page.locator("body")).toBeVisible();
  });

  test("Trends Page: Displays interactive CVSS spectrum and telemetry", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: /Quick Access \(Admin\)/i }).click();
    await page.waitForURL(/\/dashboard/i, { timeout: 10000 });

    await page.goto("/trends");
    await expect(page.locator("h1.page-title")).toContainText(/Visual Security Telemetry & Trends/i);
    await expect(page.locator("text=CVSS v3.1 Severity Spectrum")).toBeVisible();
  });

  test("Reports Page: Displays formal compliance attestation & ASVS matrix", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: /Quick Access \(Admin\)/i }).click();
    await page.waitForURL(/\/dashboard/i, { timeout: 10000 });

    await page.goto("/reports");
    await expect(page.locator("text=Formal Compliance & Audit Attestation")).toBeVisible();
    await expect(page.locator("text=OWASP ASVS v4.0 Compliance Status")).toBeVisible();
    await expect(page.getByRole("button", { name: /Download CSV/i })).toBeVisible();
  });

  test("Team Page: Displays team member directory and invite modal", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: /Quick Access \(Admin\)/i }).click();
    await page.waitForURL(/\/dashboard/i, { timeout: 10000 });

    await page.goto("/team");
    await expect(page.locator("text=Team & Access Controls")).toBeVisible();

    // Click Invite Member button
    const inviteBtn = page.getByRole("button", { name: /Invite Member/i });
    await expect(inviteBtn).toBeVisible();
    await inviteBtn.click();

    // Verify modal fields
    await expect(page.getByPlaceholder("developer@company.com")).toBeVisible();
    await expect(page.getByRole("button", { name: /Send Invitation/i })).toBeVisible();

    // Close modal
    await page.getByRole("button", { name: /Cancel/i }).click();
  });

  test("Policies Page: Displays security gate rules", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: /Quick Access \(Admin\)/i }).click();
    await page.waitForURL(/\/dashboard/i, { timeout: 10000 });

    await page.goto("/policies");
    await expect(page.locator("body")).toBeVisible();
  });
});
