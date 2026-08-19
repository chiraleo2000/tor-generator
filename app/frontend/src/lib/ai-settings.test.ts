import { describe, expect, it } from "vitest";
import {
  CLOUD_LLMS,
  EMPTY_AI_SETTINGS,
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
  it("lists local and cloud chat options in every mode", () => {
    expect(llmOptionsForMode("on_prem").map((item) => item.value)).toContain("lm_studio");
    expect(llmOptionsForMode("on_prem").map((item) => item.value)).toContain("claude");
    expect(llmOptionsForMode("cloud").map((item) => item.value)).toEqual([
      "claude",
      "openai",
      "gemini",
      "bedrock",
      "azure_foundry",
      "openai_compatible",
      "lm_studio",
      "ollama",
      "llama_cpp",
    ]);
    expect(llmOptionsForMode("hybrid").map((item) => item.value)).toContain("lm_studio");
    expect(llmOptionsForMode("hybrid").map((item) => item.value)).toContain("claude");
  });

  it("lists local and cloud embeddings in every mode", () => {
    expect(embedOptionsForMode("on_prem").map((item) => item.value)).toContain("local");
    expect(embedOptionsForMode("on_prem").map((item) => item.value)).toContain("openai");
    expect(embedOptionsForMode("cloud").map((item) => item.value)).toContain("gemini");
    expect(embedOptionsForMode("cloud").map((item) => item.value)).toContain("local");
    expect(embedOptionsForMode("hybrid").map((item) => item.value)).toContain("gemini");
    expect(embedOptionsForMode("hybrid").map((item) => item.value)).toContain("local");
  });

  it("shows local URLs and cloud keys from the selected providers, not the mode", () => {
    expect(showLocalServerFields("on_prem", "lm_studio", "local")).toBe(true);
    expect(showLocalServerFields("cloud", "claude", "local")).toBe(true);
    expect(showLocalServerFields("cloud", "claude", "openai")).toBe(false);
    expect(showLocalServerFields("hybrid", "openai", "openai")).toBe(false);
    expect(showCloudKeyFields("on_prem", "lm_studio", "local")).toBe(false);
    expect(showCloudKeyFields("on_prem", "claude", "local")).toBe(true);
    expect(showCloudKeyFields("cloud", "claude", "openai")).toBe(true);
    expect(showCloudKeyFields("hybrid", "lm_studio", "openai")).toBe(true);
  });

  it("includes pgvector and qdrant vector stores", () => {
    expect(VECTOR_STORES.map((item) => item.value)).toEqual(["pgvector", "qdrant"]);
  });

  it("keeps chat and embeddings unchanged when switching mode", () => {
    const next = nextFormOnModeChange(EMPTY_AI_SETTINGS, "cloud");
    expect(next.deployment_mode).toBe("cloud");
    expect(next.llm_provider).toBe("lm_studio");
    expect(next.embedding_provider).toBe("local");
  });

  it("does not swap providers when returning to on_prem", () => {
    const mixed = nextFormOnModeChange(
      { ...EMPTY_AI_SETTINGS, llm_provider: "claude", embedding_provider: "local" },
      "cloud"
    );
    const local = nextFormOnModeChange(mixed, "on_prem");
    expect(local.llm_provider).toBe("claude");
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
    expect(saveSuccessMessage(true)).toContain("seed_raw_docs");
  });

  it("detects masked secrets", () => {
    expect(isMaskedSecret("****abcd")).toBe(true);
    expect(isMaskedSecret("sk-live")).toBe(false);
    expect(CLOUD_LLMS.map((item) => item.value)).toEqual([
      "claude",
      "openai",
      "gemini",
      "bedrock",
      "azure_foundry",
      "openai_compatible",
    ]);
  });
});
