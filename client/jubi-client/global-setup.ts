import { chromium, FullConfig } from "@playwright/test";
import fs from "fs";
import path from "path";

async function globalSetup(config: FullConfig) {
  const authDir = path.join(__dirname, "playwright/.auth");
  if (!fs.existsSync(authDir)) {
    fs.mkdirSync(authDir, { recursive: true });
  }

  const browser = await chromium.launch();
  const page = await browser.newPage();

  // If you have auth, do login here and save storageState
  // For now, just create empty auth file for unauthenticated tests
  await page.context().storageState({ path: path.join(authDir, "user.json") });
  await browser.close();
}

export default globalSetup;