const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const appDir = path.join(__dirname, "../src/app");

const requiredRoutes = [
  "health/route.ts",
  "version/route.ts",
  "dashboard/page.tsx",
  "pull-requests/page.tsx",
  "pull-requests/[id]/page.tsx",
  "findings/page.tsx",
  "findings/[id]/page.tsx",
  "repositories/page.tsx",
  "repositories/[id]/page.tsx",
  "trends/page.tsx",
  "policies/page.tsx",
  "reports/page.tsx",
  "team/page.tsx",
  "integrations/page.tsx",
  "settings/page.tsx",
  "admin/logs/page.tsx",
  "login/page.tsx",
];

for (const route of requiredRoutes) {
  test(`SaaS Route exists: ${route}`, () => {
    const routePath = path.join(appDir, route);
    assert.strictEqual(fs.existsSync(routePath), true, `Route ${route} should exist`);
  });
}
