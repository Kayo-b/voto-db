#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const readline = require("readline");
const { chromium, firefox, webkit } = require("playwright");

function resolvePath(value, fallbackPath) {
  if (!value || !String(value).trim()) {
    return fallbackPath;
  }
  const candidate = String(value).trim();
  return path.isAbsolute(candidate) ? candidate : path.resolve(process.cwd(), candidate);
}

function waitForEnter(message) {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });
  return new Promise((resolve) => {
    rl.question(message, () => {
      rl.close();
      resolve();
    });
  });
}

async function main() {
  const browserName = (process.env.TWITTER_BOT_BROWSER || "chromium").trim().toLowerCase();
  const browserTypes = { chromium, firefox, webkit };
  const browserType = browserTypes[browserName];
  if (!browserType) {
    throw new Error(`Unsupported TWITTER_BOT_BROWSER="${browserName}". Use chromium, firefox, or webkit.`);
  }
  const browserExecutablePath = (process.env.TWITTER_BOT_BROWSER_EXECUTABLE || "").trim() || undefined;

  const storageStatePath = resolvePath(
    process.env.TWITTER_STORAGE_STATE_PATH,
    path.resolve(process.cwd(), "playwright", ".auth", "twitter-bot.json")
  );
  const userDataDir = resolvePath(
    process.env.TWITTER_BOT_USER_DATA_DIR,
    path.resolve(process.cwd(), "playwright", ".auth", "twitter-bot-profile")
  );
  fs.mkdirSync(path.dirname(storageStatePath), { recursive: true });
  fs.mkdirSync(userDataDir, { recursive: true });

  const launchOptions = { headless: false };
  if (browserExecutablePath) {
    launchOptions.executablePath = browserExecutablePath;
  }

  const context = await browserType.launchPersistentContext(userDataDir, launchOptions);
  const page = context.pages()[0] || (await context.newPage());
  try {
    await page.goto("https://x.com/login", {
      waitUntil: "domcontentloaded",
      timeout: 30000,
    });
  } catch (error) {
    console.warn(`Login page navigation timeout, continuing anyway: ${String(error)}`);
  }

  console.log("Complete login in the opened browser window.");
  console.log("If asked for 2FA/challenges, finish them there.");
  await waitForEnter("Press ENTER here once you are fully logged in on x.com/home...");

  await context.storageState({ path: storageStatePath });
  console.log(`Saved authenticated session to: ${storageStatePath}`);
  console.log(`Persistent profile in use: ${userDataDir}`);

  await context.close();
}

main().catch((error) => {
  const message = error && error.stack ? error.stack : String(error);
  console.error(message);
  process.exit(1);
});
