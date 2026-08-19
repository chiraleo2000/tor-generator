export interface AiSettings {
  deployment_mode: string;
  llm_provider: string;
  embedding_provider: string;
  local_embedding_server: string;
  local_embedding_base_url: string;
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
  aws_access_key_id: string;
  aws_secret_access_key: string;
  aws_secret_access_key_set?: boolean;
  azure_foundry_api_key: string;
  azure_foundry_api_key_set?: boolean;
  openai_compatible_api_key: string;
  openai_compatible_api_key_set?: boolean;
  openai_chat_model: string;
  openai_embedding_model: string;
  gemini_model: string;
  gemini_embedding_model: string;
  vector_store_provider: string;
  bedrock_region: string;
  bedrock_model_id: string;
  bedrock_embedding_model_id: string;
  azure_foundry_endpoint: string;
  azure_foundry_deployment: string;
  azure_foundry_embedding_deployment: string;
  azure_foundry_api_version: string;
  openai_compatible_base_url: string;
  openai_compatible_model: string;
  openai_compatible_embedding_model: string;
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
  { value: "bedrock", label: "Amazon Bedrock" },
  { value: "azure_foundry", label: "Azure AI Foundry" },
  { value: "openai_compatible", label: "อื่น ๆ (OpenAI-compatible)" },
];

export const LOCAL_EMBEDS = [
  { value: "local", label: "ในเครื่อง (OpenAI-compatible)" },
  { value: "qwen3", label: "ในเครื่อง (alias เดิม qwen3)" },
];

export const CLOUD_EMBEDS = [
  { value: "openai", label: "OpenAI embeddings" },
  { value: "gemini", label: "Gemini embeddings" },
  { value: "bedrock", label: "Bedrock (Titan)" },
  { value: "azure_foundry", label: "Azure Foundry embeddings" },
  { value: "openai_compatible", label: "OpenAI-compatible embeddings" },
];

export const VECTOR_STORES = [
  { value: "pgvector", label: "pgvector" },
  { value: "qdrant", label: "Qdrant" },
];

export const EMPTY_AI_SETTINGS: AiSettings = {
  deployment_mode: "on_prem",
  llm_provider: "lm_studio",
  embedding_provider: "local",
  local_embedding_server: "lm_studio",
  local_embedding_base_url: "",
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
  openai_embedding_model: "text-embedding-3-small",
  gemini_model: "gemini-2.0-flash",
  gemini_embedding_model: "text-embedding-004",
  vector_store_provider: "pgvector",
  aws_access_key_id: "",
  aws_secret_access_key: "",
  azure_foundry_api_key: "",
  openai_compatible_api_key: "",
  bedrock_region: "ap-southeast-1",
  bedrock_model_id: "anthropic.claude-3-5-sonnet-20241022-v2:0",
  bedrock_embedding_model_id: "amazon.titan-embed-text-v2:0",
  azure_foundry_endpoint: "",
  azure_foundry_deployment: "",
  azure_foundry_embedding_deployment: "",
  azure_foundry_api_version: "2024-10-21",
  openai_compatible_base_url: "",
  openai_compatible_model: "",
  openai_compatible_embedding_model: "text-embedding-3-small",
};

export function llmOptionsForMode(mode: string) {
  if (mode === "cloud") {
    return [...CLOUD_LLMS, ...LOCAL_LLMS];
  }
  return [...LOCAL_LLMS, ...CLOUD_LLMS];
}

export function embedOptionsForMode(mode: string) {
  if (mode === "cloud") {
    return [...CLOUD_EMBEDS, ...LOCAL_EMBEDS];
  }
  return [...LOCAL_EMBEDS, ...CLOUD_EMBEDS];
}

export function showLocalServerFields(
  _mode: string,
  llmProvider: string,
  embedProvider = "",
): boolean {
  return hasValue(LOCAL_LLMS, llmProvider) || hasValue(LOCAL_EMBEDS, embedProvider);
}

export function showCloudKeyFields(
  _mode: string,
  llmProvider: string,
  embedProvider = "",
): boolean {
  return hasValue(CLOUD_LLMS, llmProvider) || hasValue(CLOUD_EMBEDS, embedProvider);
}

function hasValue(options: { value: string }[], value: string): boolean {
  return options.some((item) => item.value === value);
}

export function nextFormOnModeChange(prev: AiSettings, mode: string): AiSettings {
  return { ...prev, deployment_mode: mode };
}

export function saveSuccessMessage(reingestRequired: boolean): string {
  if (reingestRequired) {
    return "บันทึกแล้ว — มีผลทันที เปลี่ยน embeddings แล้ว ต้องรัน python -m app.seed_raw_docs เพื่อฝังเวกเตอร์ใหม่";
  }
  return "บันทึกแล้ว — มีผลทันที ไม่ต้องรีสตาร์ท backend";
}

export function showBedrockFields(llmProvider: string, embedProvider: string): boolean {
  return llmProvider === "bedrock" || embedProvider === "bedrock";
}

export function showAzureFields(llmProvider: string, embedProvider: string): boolean {
  return llmProvider === "azure_foundry" || embedProvider === "azure_foundry";
}

export function showCompatFields(llmProvider: string, embedProvider: string): boolean {
  return llmProvider === "openai_compatible" || embedProvider === "openai_compatible";
}

export function isMaskedSecret(value: string | undefined): boolean {
  return value?.startsWith("****") === true;
}
