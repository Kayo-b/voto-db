#!/usr/bin/env node

const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");
const { chromium, firefox, webkit } = require("playwright");

function parseBoolean(raw, fallback) {
  if (raw === undefined || raw === null || raw === "") return fallback;
  return ["1", "true", "yes", "on"].includes(String(raw).trim().toLowerCase());
}

function resolvePath(value, fallbackPath) {
  if (!value || !String(value).trim()) {
    return fallbackPath;
  }
  const candidate = String(value).trim();
  return path.isAbsolute(candidate) ? candidate : path.resolve(process.cwd(), candidate);
}

function sameSiteFromFirefox(rawValue) {
  const n = Number(rawValue);
  if (n === 2) return "Strict";
  if (n === 1) return "Lax";
  return "None";
}

function normalizeExpiry(rawValue) {
  const n = Number(rawValue || 0);
  if (!Number.isFinite(n) || n <= 0) return undefined;
  return n > 100000000000 ? Math.floor(n / 1000) : Math.floor(n);
}

function loadCookiesFromFirefoxProfile(profileDir) {
  const cookiesDb = path.join(profileDir, "cookies.sqlite");
  if (!fs.existsSync(cookiesDb)) {
    throw new Error(`Firefox cookies DB not found: ${cookiesDb}`);
  }

  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "twitter-cookies-"));
  const tmpDb = path.join(tmpDir, "cookies.sqlite");
  const tmpWal = path.join(tmpDir, "cookies.sqlite-wal");
  const tmpShm = path.join(tmpDir, "cookies.sqlite-shm");

  try {
    fs.copyFileSync(cookiesDb, tmpDb);
    const srcWal = path.join(profileDir, "cookies.sqlite-wal");
    const srcShm = path.join(profileDir, "cookies.sqlite-shm");
    if (fs.existsSync(srcWal)) fs.copyFileSync(srcWal, tmpWal);
    if (fs.existsSync(srcShm)) fs.copyFileSync(srcShm, tmpShm);

    const query = [
      "select host, name, value, path, expiry, isSecure, isHttpOnly, sameSite",
      "from moz_cookies",
      "where host in ('x.com','.x.com','twitter.com','.twitter.com')",
      "or host like '%.x.com'",
      "or host like '%.twitter.com'",
      "order by host, name",
    ].join(" ");

    const rawJson = execFileSync("sqlite3", ["-json", tmpDb, query], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    }).trim();
    const rows = rawJson ? JSON.parse(rawJson) : [];

    return rows
      .filter((r) => r && r.host && r.name)
      .map((r) => {
        const cookie = {
          name: String(r.name),
          value: String(r.value || ""),
          domain: String(r.host),
          path: String(r.path || "/"),
          secure: Number(r.isSecure || 0) === 1,
          httpOnly: Number(r.isHttpOnly || 0) === 1,
          sameSite: sameSiteFromFirefox(r.sameSite),
        };
        const expiry = normalizeExpiry(r.expiry);
        if (expiry) cookie.expires = expiry;
        return cookie;
      });
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
}

async function waitForAnyVisible(page, selectors, timeoutMs) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    for (const selector of selectors) {
      const locator = page.locator(selector).first();
      const visible = await locator.isVisible().catch(() => false);
      if (visible) return locator;
    }
    await page.waitForTimeout(200);
  }
  throw new Error(`None of selectors became visible: ${selectors.join(", ")}`);
}

async function firstVisibleLocator(page, selectors) {
  for (const selector of selectors) {
    const locator = page.locator(selector);
    const count = await locator.count().catch(() => 0);
    for (let i = 0; i < count; i += 1) {
      const candidate = locator.nth(i);
      const visible = await candidate.isVisible().catch(() => false);
      if (visible) return candidate;
    }
  }
  return null;
}

async function recoverTransientErrorScreen(page, maxAttempts = 3) {
  for (let i = 0; i < maxAttempts; i += 1) {
    const errorMessage = page.getByText(/something went wrong/i).first();
    const retryButton = page.getByRole("button", { name: /retry/i }).first();
    const hasError = await errorMessage.isVisible().catch(() => false);
    if (!hasError) {
      return;
    }

    const canRetry = await retryButton.isVisible().catch(() => false);
    if (canRetry) {
      await retryButton.click();
    } else {
      await page.reload({ waitUntil: "domcontentloaded" }).catch(() => {});
    }
    await page.waitForTimeout(2000);
  }
}

async function gotoWithRecovery(page, url) {
  await page.goto(url, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1200);
  await recoverTransientErrorScreen(page, 4);
}

async function composeReady(page) {
  const composeSelectors = [
    '[data-testid="tweetTextarea_0"]',
    'div[role="textbox"][data-testid*="tweetTextarea"]',
  ];
  for (const selector of composeSelectors) {
    const visible = await page.locator(selector).first().isVisible().catch(() => false);
    if (visible) return true;
  }
  return false;
}

async function waitForPostButtonEnabled(button, timeoutMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const ariaDisabled = await button.getAttribute("aria-disabled").catch(() => null);
    const disabled = await button.isDisabled().catch(() => false);
    if (ariaDisabled !== "true" && !disabled) {
      return true;
    }
    await button.page().waitForTimeout(250);
  }
  return false;
}

async function findVisiblePostButton(page) {
  const candidates = [
    page.getByRole("dialog").getByRole("button", { name: /^(post|tweet|publicar|postar)$/i }).first(),
    page.getByRole("button", { name: /^(post|tweet|publicar|postar)$/i }).first(),
    page.locator('[data-testid="tweetButtonInline"]').first(),
    page.locator('[data-testid="tweetButton"]').first(),
  ];

  for (const locator of candidates) {
    const visible = await locator.isVisible().catch(() => false);
    if (visible) return locator;
  }
  return null;
}

async function waitForPostButton(page, timeoutMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const button = await findVisiblePostButton(page);
    if (button) return button;
    await page.waitForTimeout(250);
  }
  throw new Error("Post button was not found");
}

async function runLoginFlow(page, baseUrl) {
  const username = (process.env.TWITTER_USERNAME || "").trim();
  const password = (process.env.TWITTER_PASSWORD || "").trim();
  const challengeValue = (
    process.env.TWITTER_EMAIL ||
    process.env.TWITTER_PHONE ||
    process.env.TWITTER_USERNAME_CONFIRM ||
    ""
  ).trim();

  if (!username || !password) {
    throw new Error(
      "Missing TWITTER_USERNAME/TWITTER_PASSWORD. Set credentials or provide TWITTER_STORAGE_STATE_PATH with a logged-in session."
    );
  }

  const debug = parseBoolean(process.env.TWITTER_BOT_DEBUG, false);
  await gotoWithRecovery(page, `${baseUrl}/i/flow/login`);
  const usernameInput = await waitForAnyVisible(
    page,
    [
      'input[autocomplete="username"][name="text"]',
      'input[autocomplete="username"]',
      'input[placeholder*="Phone, email"]',
      'input[name="text"]',
    ],
    30000
  );
  if (debug) {
    const prePath = `${process.env.TWITTER_BOT_ARTIFACT_DIR || "output/playwright"}/twitter-login-before-fill-${Date.now()}.png`;
    await page.screenshot({ path: prePath, fullPage: true }).catch(() => {});
    console.log(`debug:before_fill:${prePath}`);
  }
  await usernameInput.click({ force: true });
  await usernameInput.fill(username);
  const enteredValue = await usernameInput.inputValue().catch(() => "");
  if (!enteredValue) {
    await usernameInput.type(username, { delay: 50 });
  }
  if (debug) {
    const enteredValue2 = await usernameInput.inputValue().catch(() => "");
    console.log(`debug:username_entered_len:${enteredValue2.length}`);
    const postPath = `${process.env.TWITTER_BOT_ARTIFACT_DIR || "output/playwright"}/twitter-login-after-fill-${Date.now()}.png`;
    await page.screenshot({ path: postPath, fullPage: true }).catch(() => {});
    console.log(`debug:after_fill:${postPath}`);
  }

  let advanced = false;
  const nextSelectors = [
    '[data-testid="ocfEnterTextNextButton"]',
    '[data-testid="LoginForm_Login_Button"]',
  ];
  const nextLocator = await firstVisibleLocator(page, nextSelectors);
  if (nextLocator) {
    await nextLocator.click({ force: true, noWaitAfter: true, timeout: 8000 });
    advanced = true;
  } else {
    const nextButton = page.getByRole("button", { name: /^(next|avancar|avançar|weiter)$/i }).first();
    const nextVisible = await nextButton.isVisible().catch(() => false);
    if (nextVisible) {
      await nextButton.click({ force: true, noWaitAfter: true, timeout: 8000 });
      advanced = true;
    }
  }
  if (!advanced) {
    await usernameInput.press("Enter");
  }

  await page.waitForTimeout(1800);

  const passwordInput = page.locator('input[name="password"]').first();
  let passwordVisible = await passwordInput.isVisible({ timeout: 8000 }).catch(() => false);
  if (!passwordVisible && challengeValue) {
    const challengeInput = await waitForAnyVisible(
      page,
      ['input[data-testid="ocfEnterTextTextInput"]', 'input[name="text"]'],
      10000
    );
    await challengeInput.fill(challengeValue);
    const challengeNextButton = page
      .locator('[data-testid="ocfEnterTextNextButton"]')
      .first();
    const challengeNextVisible = await challengeNextButton.isVisible().catch(() => false);
    if (challengeNextVisible) {
      await challengeNextButton.click();
    } else {
      await challengeInput.press("Enter");
    }
    await page.waitForTimeout(1500);
    passwordVisible = await passwordInput.isVisible({ timeout: 12000 }).catch(() => false);
  }

  if (!passwordVisible) {
    // Retry one more advance click in case step transition was missed.
    const nextRetry = await firstVisibleLocator(page, nextSelectors);
    if (nextRetry) {
      await nextRetry.click({ force: true });
      await page.waitForTimeout(1500);
      passwordVisible = await passwordInput.isVisible({ timeout: 8000 }).catch(() => false);
    }
  }

  await passwordInput.waitFor({ state: "visible", timeout: 30000 });
  await passwordInput.fill(password);
  const loginButton = page
    .getByRole("button", { name: /^(log in|entrar|anmelden)$/i })
    .first();
  const loginButtonVisible = await loginButton.isVisible().catch(() => false);
  if (loginButtonVisible) {
    await loginButton.click();
  } else {
    await passwordInput.press("Enter");
  }
  await page.waitForTimeout(3000);
}

async function main() {
  const postText = (process.env.TWITTER_POST_TEXT || "").trim();
  if (!postText) {
    throw new Error("TWITTER_POST_TEXT is required");
  }
  if (postText.length > 280) {
    throw new Error(`TWITTER_POST_TEXT has ${postText.length} chars; max is 280`);
  }

  const headless = parseBoolean(process.env.TWITTER_BOT_HEADLESS, true);
  const saveState = parseBoolean(process.env.TWITTER_BOT_SAVE_STATE, true);
  const baseUrl = (process.env.TWITTER_BASE_URL || "https://x.com").trim().replace(/\/+$/, "");
  const browserName = (process.env.TWITTER_BOT_BROWSER || "chromium").trim().toLowerCase();
  const browserTypes = { chromium, firefox, webkit };
  const browserType = browserTypes[browserName];
  if (!browserType) {
    throw new Error(`Unsupported TWITTER_BOT_BROWSER="${browserName}". Use chromium, firefox, or webkit.`);
  }
  const browserExecutablePath = (process.env.TWITTER_BOT_BROWSER_EXECUTABLE || "").trim() || undefined;
  const userDataDir = resolvePath(
    process.env.TWITTER_BOT_USER_DATA_DIR,
    path.resolve(process.cwd(), "playwright", ".auth", "twitter-bot-profile")
  );
  const usePersistentProfile = parseBoolean(process.env.TWITTER_BOT_USE_PERSISTENT_PROFILE, true);
  const importCookiesFromFirefox = parseBoolean(process.env.TWITTER_IMPORT_COOKIES_FROM_FIREFOX, false);
  const firefoxProfileDir = resolvePath(
    process.env.TWITTER_FIREFOX_PROFILE_DIR,
    path.resolve(process.env.HOME || "", ".mozilla", "firefox", "vz23un1e.default-release")
  );

  const storageStatePath = resolvePath(
    process.env.TWITTER_STORAGE_STATE_PATH,
    path.resolve(process.cwd(), "playwright", ".auth", "twitter-bot.json")
  );
  const artifactDir = resolvePath(
    process.env.TWITTER_BOT_ARTIFACT_DIR,
    path.resolve(process.cwd(), "output", "playwright")
  );

  fs.mkdirSync(path.dirname(storageStatePath), { recursive: true });
  fs.mkdirSync(artifactDir, { recursive: true });
  fs.mkdirSync(userDataDir, { recursive: true });

  const launchOptions = { headless };
  if (browserExecutablePath) {
    launchOptions.executablePath = browserExecutablePath;
  }

  let browser = null;
  let context = null;

  if (usePersistentProfile) {
    context = await browserType.launchPersistentContext(userDataDir, launchOptions);
  } else {
    browser = await browserType.launch(launchOptions);
    const contextOptions = {};
    if (fs.existsSync(storageStatePath)) {
      contextOptions.storageState = storageStatePath;
    }
    context = await browser.newContext(contextOptions);
  }

  if (importCookiesFromFirefox) {
    const importedCookies = loadCookiesFromFirefoxProfile(firefoxProfileDir);
    if (importedCookies.length > 0) {
      await context.addCookies(importedCookies);
      console.log(`imported_cookies:${importedCookies.length}`);
    } else {
      console.log("imported_cookies:0");
    }
  }

  const page = context.pages()[0] || (await context.newPage());

  try {
    await gotoWithRecovery(page, `${baseUrl}/compose/post`);

    if (!(await composeReady(page))) {
      await runLoginFlow(page, baseUrl);
      await gotoWithRecovery(page, `${baseUrl}/compose/post`);
    }

    const composer = await waitForAnyVisible(
      page,
      ['[data-testid="tweetTextarea_0"]', 'div[role="textbox"][data-testid*="tweetTextarea"]'],
      25000
    );
    await composer.click();
    // Type like a user to trigger compose state updates reliably.
    await page.keyboard.type(postText, { delay: 12 });
    await page.waitForTimeout(400);
    const composerText = await composer.innerText().catch(() => "");
    if ((composerText || "").trim().length === 0) {
      await composer.fill(postText);
      await page.waitForTimeout(400);
    }

    // Prefer role-based button lookup in compose dialog (user-confirmed working path).
    const postButton = await waitForPostButton(page, 15000);
    const enabled = await waitForPostButtonEnabled(postButton, 15000);
    if (!enabled) {
      const finalComposerText = await composer.innerText().catch(() => "");
      const alertText = await page.locator('div[role="alert"]').allInnerTexts().catch(() => []);
      const buttonAria = await postButton.getAttribute("aria-disabled").catch(() => null);
      console.error(
        `post_debug:composer_len=${(finalComposerText || "").length} button_aria_disabled=${buttonAria} alerts=${JSON.stringify(alertText)}`
      );
      throw new Error("Tweet button is disabled after filling text");
    }

    await postButton.click({ force: true, noWaitAfter: true });
    await page.waitForTimeout(4000);

    if (saveState) {
      await context.storageState({ path: storageStatePath });
    }

    const screenshotPath = path.join(artifactDir, `twitter-post-${Date.now()}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: false });
    console.log(`posted:${screenshotPath}`);
  } catch (error) {
    const errorShotPath = path.join(artifactDir, `twitter-post-error-${Date.now()}.png`);
    await page.screenshot({ path: errorShotPath, fullPage: true }).catch(() => {});
    throw error;
  } finally {
    await context.close();
    if (browser) {
      await browser.close();
    }
  }
}

main().catch((error) => {
  const message = error && error.stack ? error.stack : String(error);
  console.error(message);
  process.exit(1);
});
