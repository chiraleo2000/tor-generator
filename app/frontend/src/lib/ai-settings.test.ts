import { describe, expect, it } from "vitest";
import {
  CLOUD_LLMS,
  EMPTY_AI_SETTINGS,
  LOCAL_LLMS,
  VECTOR_STORES,
  embedOptionsForMode,
  isMaskedSecret,
  llmOptionsForMode,
  nextFormOnModeChange,
  saveSuccessMessage,
  showCloudKeyFields,
  showLocalServerFields,
} from "./ai-settings";

describe("ai-settings helpers", () => {
  it("lists local chat options on on_prem, cloud-only on cloud, and both on hybrid", () => {
    expect(llmOptionsForMode("on_prem")).toEqual(LOCAL_LLMS);
    expect(llmOptionsForMode("cloud").map((item) => item.value)).toEqual([
      "claude",
      "openai",
      "gemini",
    ]);
    expect(llmOptionsForMode("hybrid").map((item) => item.value)).toContain("lm_studio");
    expect(llmOptionsForMode("hybrid").map((item) => item.value)).toContain("claude");
  });

  it("lists cloud embeddings only in cloud mode", () => {
    expect(embedOptionsForMode("on_prem").map((item) => item.value)).toEqual([
      "local",
      "qwen3",
    ]);
    expect(embedOptionsForMode("cloud").map((item) => item.value)).toEqual([
      "openai",
      "gemini",
    ]);
    expect(embedOptionsForMode("hybrid").map((item) => item.value)).toContain("gemini");
    expect(embedOptionsForMode("hybrid").map((item) => item.value)).toContain("local");
  });

  it("shows local URLs on on_prem/hybrid and cloud keys on cloud/hybrid", () => {
    expect(showLocalServerFields("on_prem", "lm_studio")).toBe(true);
    expect(showLocalServerFields("cloud", "claude")).toBe(false);
    expect(showLocalServerFields("hybrid", "openai")).toBe(true);
    expect(showCloudKeyFields("on_prem", "lm_studio")).toBe(false);
    expect(showCloudKeyFields("cloud", "claude")).toBe(true);
    expect(showCloudKeyFields("hybrid", "lm_studio")).toBe(true);
  });

  it("includes pgvector and qdrant vector stores", () => {
    expect(VECTOR_STORES.map((item) => item.value)).toEqual(["pgvector", "qdrant"]);
  });

  it("switches cloud defaults when leaving local mode", () => {
    const next = nextFormOnModeChange(EMPTY_AI_SETTINGS, "cloud");
    expect(next.deployment_mode).toBe("cloud");
    expect(next.llm_provider).toBe("claude");
    expect(next.embedding_provider).toBe("openai");
  });

  it("restores local providers when returning to on_prem", () => {
    const cloud = nextFormOnModeChange(EMPTY_AI_SETTINGS, "cloud");
    const local = nextFormOnModeChange(cloud, "on_prem");
    expect(local.llm_provider).toBe("lm_studio");
    expect(local.embedding_provider).toBe("local");
  });

  it("keeps hybrid providers unchanged", () => {
    const hybrid = nextFormOnModeChange(
      { ...EMPTY_AI_SETTINGS, llm_provider: "openai" },
      "hybrid"
    );
    expect(hybrid.deployment_mode).toBe("hybrid");
    expect(hybrid.llm_provider).toBe("openai");
  });

  it("explains immediate apply vs re-ingest", () => {
    expect(saveSuccessMessage(false)).toContain("มีผลทันที");
    expect(saveSuccessMessage(false)).toContain("ไม่ต้องรีสตาร์ท");
    expect(saveSuccessMessage(true)).toContain("seed_kb");
  });

  it("detects masked secrets", () => {
    expect(isMaskedSecret("****abcd")).toBe(true);
    expect(isMaskedSecret("sk-live")).toBe(false);
    expect(CLOUD_LLMS.map((item) => item.value)).toEqual(["claude", "openai", "gemini"]);
  });
});
