import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    exclude: ["e2e/**", "node_modules/**", ".next/**"],
    pool: "threads",
    maxWorkers: 1,
    fileParallelism: false,
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
      reportsDirectory: "./coverage",
      include: [
        "src/lib/**/*.ts",
        "src/lib/**/*.tsx",
        "src/stores/**/*.ts",
        "src/components/draft/**/*.tsx",
        "src/app/**/review/page.tsx",
        "src/app/**/admin/ai-settings/page.tsx",
        "src/app/**/knowledge-base/page.tsx",
      ],
      exclude: [
        "src/app/**/admin/knowledge-base/page.tsx",
        "src/components/draft/draft-workspace.tsx",
      ],
    },
  },
});
