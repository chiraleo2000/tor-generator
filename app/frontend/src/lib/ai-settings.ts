export interface AiSettings {
  deployment_mode: string;
  llm_provider: string;
  embedding_provider: string;
  lm_studio_base_url: string;
  lm_studio_model: string;
  lm_studio_embedding_model: string;
  lm_studio_timeout: number;
  ollama_base_url: string;
  llama_cpp_base_url: string;
  anthropic_api_key: string;
  openai_api_key: string;
  gemini_api_key: string;
  anthropic_api_key_set?: boolean;
  openai_api_key_set?: boolean;
  gemini_api_key_set?: boolean;
  openai_chat_model: string;
  gemini_model: string;
  gemini_embedding_model: string;
  vector_store_provider: string;
  restart_required?: boolean;
  reingest_required?: boolean;
  default_chat_model?: string;
  default_embedding_model?: string;
}

export const LOCAL_LLMS = [
  { value: "lm_studio", label: "LM Studio" },
  { value: "ollama", label: "Ollama" },
  { value: "llama_cpp", label: "llama.cpp / เซิร์ฟเวอร์กำหนดเอง" },
];

export const CLOUD_LLMS = [
  { value: "claude", label: "Claude (Anthropic)" },
  { value: "openai", label: "OpenAI" },
  { value: "gemini", label: "Gemini (Google)" },
];

export const LOCAL_EMBEDS = [
  { value: "local", label: "ในเครื่อง (OpenAI-compatible)" },
  { value: "qwen3", label: "ในเครื่อง (alias เดิม qwen3)" },
];

export const CLOUD_EMBEDS = [
  { value: "openai", label: "OpenAI embeddings" },
  { value: "gemini", label: "Gemini embeddings" },
];

export const VECTOR_STORES = [
  { value: "pgvector", label: "pgvector" },
  { value: "qdrant", label: "Qdrant" },
];

export const EMPTY_AI_SETTINGS: AiSettings = {
  deployment_mode: "on_prem",
  llm_provider: "lm_studio",
  embedding_provider: "local",
  lm_studio_base_url: "http://host.docker.internal:1234/v1",
  lm_studio_model: "google/gemma-4-e4b",
  lm_studio_embedding_model: "text-embedding-embeddinggemma-300m",
  lm_studio_timeout: 180,
  ollama_base_url: "http://host.docker.internal:11434/v1",
  llama_cpp_base_url: "http://host.docker.internal:8080/v1",
  anthropic_api_key: "",
  openai_api_key: "",
  gemini_api_key: "",
  openai_chat_model: "gpt-4o-mini",
  gemini_model: "gemini-2.0-flash",
  gemini_embedding_model: "text-embedding-004",
  vector_store_provider: "pgvector",
};

export function llmOptionsForMode(mode: string) {
  if (mode === "on_prem") {
    return LOCAL_LLMS;
  }
  if (mode === "cloud") {
    return CLOUD_LLMS;
  }
  return [...CLOUD_LLMS, ...LOCAL_LLMS];
}

export function embedOptionsForMode(mode: string) {
  if (mode === "on_prem") {
    return LOCAL_EMBEDS;
  }
  if (mode === "cloud") {
    return CLOUD_EMBEDS;
  }
  return [...CLOUD_EMBEDS, ...LOCAL_EMBEDS];
}

export function showLocalServerFields(mode: string, llmProvider: string): boolean {
  return mode === "on_prem" || mode === "hybrid" || hasValue(LOCAL_LLMS, llmProvider);
}

export function showCloudKeyFields(mode: string, llmProvider: string): boolean {
  return mode === "cloud" || mode === "hybrid" || hasValue(CLOUD_LLMS, llmProvider);
}

function hasValue(options: { value: string }[], value: string): boolean {
  return options.some((item) => item.value === value);
}

export function nextFormOnModeChange(prev: AiSettings, mode: string): AiSettings {
  if (mode === "on_prem") {
    return {
      ...prev,
      deployment_mode: mode,
      llm_provider: hasValue(LOCAL_LLMS, prev.llm_provider)
        ? prev.llm_provider
        : "lm_studio",
      embedding_provider: "local",
    };
  }
  if (mode === "hybrid") {
    return { ...prev, deployment_mode: mode };
  }
  return {
    ...prev,
    deployment_mode: mode,
    llm_provider: hasValue(CLOUD_LLMS, prev.llm_provider) ? prev.llm_provider : "claude",
    embedding_provider: hasValue(CLOUD_EMBEDS, prev.embedding_provider)
      ? prev.embedding_provider
      : "openai",
  };
}

export function saveSuccessMessage(reingestRequired: boolean): string {
  if (reingestRequired) {
    return "บันทึกแล้ว — มีผลทันที เปลี่ยน embeddings แล้ว ต้องรัน python -m app.seed_kb เพื่อฝังเวกเตอร์ใหม่";
  }
  return "บันทึกแล้ว — มีผลทันที ไม่ต้องรีสตาร์ท backend";
}

export function isMaskedSecret(value: string | undefined): boolean {
  return value?.startsWith("****") === true;
}
