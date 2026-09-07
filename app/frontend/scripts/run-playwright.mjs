/**
 * Spawn Playwright after dropping NO_COLOR when FORCE_COLOR is set.
 * Node 22+ warns if both env vars exist (workers inherit the parent env).
 */
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

if (process.env.FORCE_COLOR) {
  delete process.env.NO_COLOR;
}

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const cli = path.join(root, "node_modules", "@playwright", "test", "cli.js");
const child = spawn(process.execPath, [cli, "test", ...process.argv.slice(2)], {
  cwd: root,
  stdio: "inherit",
  env: process.env,
});
child.on("exit", (code, signal) => {
  if (signal) {
    process.exit(1);
  }
  process.exit(code ?? 1);
});
