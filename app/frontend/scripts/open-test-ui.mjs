/**
 * Open the Docker TOR UI in a dedicated Chrome profile/window.
 * Does not reuse the operator's everyday Chrome session.
 */
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const profile = path.resolve(here, "..", ".chrome-test-profile");
const url = process.env.E2E_BASE_URL || "http://localhost:3000/login";

const candidates = [
  process.env.E2E_CHROME_PATH,
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
].filter(Boolean);

const exe = candidates.find((item) => fs.existsSync(item));
if (!exe) {
  console.error("No Chrome/Edge binary found. Set E2E_CHROME_PATH.");
  process.exit(1);
}

fs.mkdirSync(profile, { recursive: true });

const child = spawn(
  exe,
  [
    `--user-data-dir=${profile}`,
    "--no-first-run",
    "--no-default-browser-check",
    "--new-window",
    "--window-position=80,80",
    "--window-size=1280,860",
    url,
  ],
  { detached: true, stdio: "ignore" }
);
child.unref();
console.log(`Opened ${url} in a separate test profile:\n  ${profile}`);
