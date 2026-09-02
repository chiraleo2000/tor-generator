"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import {
  EMPTY_AI_SETTINGS,
  LOCAL_LLMS,
  RAG_SOURCE_OPTIONS,
  VECTOR_STORES,
  embedOptionsForMode,
  llmOptionsForMode,
  nextFormOnModeChange,
  saveSuccessMessage,
  showAzureFields,
  showBedrockFields,
  showCloudKeyFields,
  showCompatFields,
  showLocalServerFields,
  showSglangFields,
  type AiSettings,
} from "@/lib/ai-settings";
import { apiClient } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-error";
import { unwrapData } from "@/lib/api-unwrap";

export default function AdminAiSettingsPage() {
  const [form, setForm] = useState<AiSettings>(EMPTY_AI_SETTINGS);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const response = await apiClient.get("/admin/ai-settings");
    const payload = unwrapData<AiSettings>(response);
    setForm({ ...EMPTY_AI_SETTINGS, ...payload });
  }, []);

  useEffect(() => {
    load().catch(() => setError("โหลดการตั้งค่า AI ไม่สำเร็จ"));
  }, [load]);

  function patch<K extends keyof AiSettings>(key: K, value: AiSettings[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function save() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const response = await apiClient.put("/admin/ai-settings", form);
      const payload = unwrapData<AiSettings>(response);
      setForm({ ...EMPTY_AI_SETTINGS, ...payload });
      setMessage(saveSuccessMessage(Boolean(payload.reingest_required)));
    } catch (err: unknown) {
      setError(apiErrorMessage(err, "บันทึกไม่สำเร็จ"));
    } finally {
      setBusy(false);
    }
  }

  async function testConnection() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const response = await apiClient.post("/admin/ai-settings/test", {
        deployment_mode: form.deployment_mode,
        llm_provider: form.llm_provider,
        embedding_provider: form.embedding_provider,
        lm_studio_base_url: form.lm_studio_base_url,
        ollama_base_url: form.ollama_base_url,
        llama_cpp_base_url: form.llama_cpp_base_url,
        sglang_base_url: form.sglang_base_url,
        sglang_embedding_base_url: form.sglang_embedding_base_url,
        local_embedding_server: form.local_embedding_server,
        local_embedding_base_url: form.local_embedding_base_url,
        anthropic_api_key: form.anthropic_api_key,
        openai_api_key: form.openai_api_key,
        gemini_api_key: form.gemini_api_key,
        aws_access_key_id: form.aws_access_key_id,
        aws_secret_access_key: form.aws_secret_access_key,
        bedrock_region: form.bedrock_region,
        azure_foundry_endpoint: form.azure_foundry_endpoint,
        azure_foundry_api_key: form.azure_foundry_api_key,
        azure_foundry_api_version: form.azure_foundry_api_version,
        openai_compatible_base_url: form.openai_compatible_base_url,
        openai_compatible_api_key: form.openai_compatible_api_key,
        custom_rag_enabled: form.custom_rag_enabled,
        custom_rag_base_url: form.custom_rag_base_url,
        custom_rag_api_key: form.custom_rag_api_key,
        rag_sources: form.rag_sources,
      });
      const payload = unwrapData<{ message?: string }>(response);
      setMessage(payload.message || "เชื่อมต่อได้");
    } catch (err: unknown) {
      setError(apiErrorMessage(err, "ทดสอบไม่สำเร็จ"));
    } finally {
      setBusy(false);
    }
  }

  const showLocal = showLocalServerFields(
    form.deployment_mode,
    form.llm_provider,
    form.embedding_provider,
  );
  const showCloud = showCloudKeyFields(
    form.deployment_mode,
    form.llm_provider,
    form.embedding_provider,
  );

  return (
    <div className="max-w-3xl mx-auto space-y-6" data-testid="admin-ai-settings-page">
      <div className="gov-card">
        <h1 className="text-2xl font-extrabold text-navy">การตั้งค่า AI</h1>
        <p className="text-sm text-muted-foreground mt-1">
          ระบบนี้ใช้ PageIndex RAG จึงไม่ต้องใช้ embeddings หรือ vector store ของ TOR
          โมเดลแชทใช้สำหรับร่าง ตอบ และตรวจ TOR เท่านั้น การบันทึกมีผลทันที
          ไม่ต้องรีสตาร์ทส่วนหลังบ้าน
        </p>
      </div>

      {message ? (
        <output
          className="block text-sm rounded-md border bg-green-50 text-green-900 p-3"
          data-testid="ai-settings-status"
        >
          {message}
        </output>
      ) : null}
      {error ? (
        <p
          className="text-sm rounded-md border border-destructive/50 text-destructive p-3"
          role="alert"
          data-testid="ai-settings-error"
        >
          {error}
        </p>
      ) : null}

      <div className="gov-card space-y-4">
        <div>
          <Label htmlFor="ai-mode">โหมด</Label>
          <Select
            id="ai-mode"
            value={form.deployment_mode}
            onChange={(event) => setForm((prev) => nextFormOnModeChange(prev, event.target.value))}
            options={[
              { value: "on_prem", label: "รันในเครื่อง" },
              { value: "cloud", label: "คลาวด์ (API ภายนอก)" },
              { value: "hybrid", label: "ผสม — แนะนำเมื่อใช้คนละแหล่ง" },
            ]}
          />
        </div>

        <div>
          <Label htmlFor="ai-llm">โมเดลแชท</Label>
          <Select
            id="ai-llm"
            value={form.llm_provider}
            onChange={(event) => patch("llm_provider", event.target.value)}
            options={llmOptionsForMode(form.deployment_mode)}
          />
        </div>

        <div>
          <Label htmlFor="ai-embed">Embedding ของ TOR</Label>
          <Select
            id="ai-embed"
            value={form.embedding_provider}
            onChange={(event) => patch("embedding_provider", event.target.value)}
            options={embedOptionsForMode(form.deployment_mode)}
          />
        </div>

        {form.embedding_provider === "none" ? (
          <div className="rounded-md border border-border bg-muted/40 p-3 text-sm text-muted-foreground">
            PageIndex เป็นผู้ค้นเอกสาร จึงไม่สร้าง embedding และไม่ใช้ vector store ใน TOR
          </div>
        ) : (
          <div>
            <Label htmlFor="vector-store">คลังเวกเตอร์</Label>
            <Select
              id="vector-store"
              value={form.vector_store_provider}
              onChange={(event) => patch("vector_store_provider", event.target.value)}
              options={VECTOR_STORES}
            />
          </div>
        )}
      </div>

      {showLocal ? (
        <div className="gov-card space-y-3">
          <h2 className="font-semibold">เซิร์ฟเวอร์ในเครื่อง</h2>
          <div>
            <Label htmlFor="local-embed-server">เซิร์ฟเวอร์ฝังเวกเตอร์ในเครื่อง</Label>
            <Select
              id="local-embed-server"
              value={form.local_embedding_server || "lm_studio"}
              onChange={(event) => patch("local_embedding_server", event.target.value)}
              options={LOCAL_LLMS}
            />
          </div>
          <div>
            <Label htmlFor="local-embed-url">URL ฝังเวกเตอร์ (เว้นว่างใช้ URL ของเซิร์ฟเวอร์ด้านบน)</Label>
            <Input
              id="local-embed-url"
              value={form.local_embedding_base_url}
              onChange={(event) => patch("local_embedding_base_url", event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="lm-url">LM Studio URL</Label>
            <Input
              id="lm-url"
              value={form.lm_studio_base_url}
              onChange={(event) => patch("lm_studio_base_url", event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="ollama-url">Ollama URL</Label>
            <Input
              id="ollama-url"
              value={form.ollama_base_url}
              onChange={(event) => patch("ollama_base_url", event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="llama-url">llama.cpp / URL ที่กำหนดเอง</Label>
            <Input
              id="llama-url"
              value={form.llama_cpp_base_url}
              onChange={(event) => patch("llama_cpp_base_url", event.target.value)}
            />
          </div>
          {showSglangFields(form.llm_provider, form.local_embedding_server) ? (
            <>
              <div>
                <Label htmlFor="sglang-url">SGLang แชท URL</Label>
                <Input
                  id="sglang-url"
                  value={form.sglang_base_url}
                  onChange={(event) => patch("sglang_base_url", event.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="sglang-embed-url">SGLang embedding URL</Label>
                <Input
                  id="sglang-embed-url"
                  value={form.sglang_embedding_base_url}
                  onChange={(event) => patch("sglang_embedding_base_url", event.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="sglang-model">โมเดลแชท SGLang</Label>
                <Input
                  id="sglang-model"
                  value={form.sglang_model}
                  onChange={(event) => patch("sglang_model", event.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="sglang-embed-model">โมเดลฝังเวกเตอร์ SGLang</Label>
                <Input
                  id="sglang-embed-model"
                  value={form.sglang_embedding_model}
                  onChange={(event) => patch("sglang_embedding_model", event.target.value)}
                />
              </div>
            </>
          ) : null}
          <div>
            <Label htmlFor="chat-model">ชื่อโมเดลแชท (LM Studio / Ollama / llama.cpp)</Label>
            <Input
              id="chat-model"
              value={form.lm_studio_model}
              onChange={(event) => patch("lm_studio_model", event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="embed-model">ชื่อโมเดลฝังเวกเตอร์</Label>
            <Input
              id="embed-model"
              value={form.lm_studio_embedding_model}
              onChange={(event) => patch("lm_studio_embedding_model", event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="timeout">หมดเวลารอ (วินาที)</Label>
            <Input
              id="timeout"
              type="number"
              min={1}
              max={900}
              value={form.lm_studio_timeout}
              onChange={(event) =>
                patch("lm_studio_timeout", Number.parseFloat(event.target.value) || 600)
              }
            />
          </div>
        </div>
      ) : null}

      {showCloud ? (
        <div className="gov-card space-y-3">
          <h2 className="font-semibold">คีย์คลาวด์</h2>
          <div>
            <Label htmlFor="anthropic-key">Anthropic API key</Label>
            <Input
              id="anthropic-key"
              type="password"
              autoComplete="off"
              value={form.anthropic_api_key}
              onChange={(event) => patch("anthropic_api_key", event.target.value)}
              placeholder={form.anthropic_api_key_set ? "คงคีย์เดิมไว้ถ้าเว้นว่างแบบ ****" : ""}
            />
          </div>
          <div>
            <Label htmlFor="openai-key">OpenAI API key</Label>
            <Input
              id="openai-key"
              type="password"
              autoComplete="off"
              value={form.openai_api_key}
              onChange={(event) => patch("openai_api_key", event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="gemini-key">Gemini API key</Label>
            <Input
              id="gemini-key"
              type="password"
              autoComplete="off"
              value={form.gemini_api_key}
              onChange={(event) => patch("gemini_api_key", event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="openai-model">โมเดล OpenAI แชท</Label>
            <Input
              id="openai-model"
              value={form.openai_chat_model}
              onChange={(event) => patch("openai_chat_model", event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="openai-embed-model">โมเดลฝังเวกเตอร์ OpenAI</Label>
            <Input
              id="openai-embed-model"
              value={form.openai_embedding_model}
              onChange={(event) => patch("openai_embedding_model", event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="gemini-model">โมเดล Gemini</Label>
            <Input
              id="gemini-model"
              value={form.gemini_model}
              onChange={(event) => patch("gemini_model", event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="gemini-embed-model">โมเดลฝังเวกเตอร์ Gemini</Label>
            <Input
              id="gemini-embed-model"
              value={form.gemini_embedding_model}
              onChange={(event) => patch("gemini_embedding_model", event.target.value)}
            />
          </div>
        </div>
      ) : null}

      {showCloud && showBedrockFields(form.llm_provider, form.embedding_provider) ? (
        <div className="gov-card space-y-3">
          <h2 className="font-semibold">Amazon Bedrock (แนะนำ production)</h2>
          <p className="text-xs text-muted-foreground">
            Bedrock API key ตั้งผ่าน AWS_BEARER_TOKEN_BEDROCK ใน .env; บน EC2/ECS
            สามารถเว้น credentials ว่างเพื่อใช้ IAM role
          </p>
          <Label htmlFor="bedrock-region">ภูมิภาค</Label>
          <Input
            id="bedrock-region"
            value={form.bedrock_region}
            onChange={(event) => patch("bedrock_region", event.target.value)}
          />
          <Label htmlFor="bedrock-model">รหัสโมเดลแชท</Label>
          <Input
            id="bedrock-model"
            value={form.bedrock_model_id}
            onChange={(event) => patch("bedrock_model_id", event.target.value)}
          />
          <Label htmlFor="bedrock-embed-model">รหัสโมเดลฝังเวกเตอร์</Label>
          <Input
            id="bedrock-embed-model"
            value={form.bedrock_embedding_model_id}
            onChange={(event) => patch("bedrock_embedding_model_id", event.target.value)}
          />
          <Label htmlFor="aws-key">AWS access key (เว้นว่างได้ถ้าใช้ IAM role)</Label>
          <Input
            id="aws-key"
            value={form.aws_access_key_id}
            onChange={(event) => patch("aws_access_key_id", event.target.value)}
          />
          <Label htmlFor="aws-secret">AWS secret</Label>
          <Input
            id="aws-secret"
            type="password"
            value={form.aws_secret_access_key}
            onChange={(event) => patch("aws_secret_access_key", event.target.value)}
          />
        </div>
      ) : null}

      {showCloud && showAzureFields(form.llm_provider, form.embedding_provider) ? (
        <div className="gov-card space-y-3">
          <h2 className="font-semibold">Azure AI Foundry</h2>
          <Label htmlFor="azure-endpoint">Endpoint</Label>
          <Input
            id="azure-endpoint"
            value={form.azure_foundry_endpoint}
            onChange={(event) => patch("azure_foundry_endpoint", event.target.value)}
          />
          <Label htmlFor="azure-key">API key</Label>
          <Input
            id="azure-key"
            type="password"
            value={form.azure_foundry_api_key}
            onChange={(event) => patch("azure_foundry_api_key", event.target.value)}
          />
          <Label htmlFor="azure-deploy">Deployment (แชท)</Label>
          <Input
            id="azure-deploy"
            value={form.azure_foundry_deployment}
            onChange={(event) => patch("azure_foundry_deployment", event.target.value)}
          />
          {form.embedding_provider === "azure_foundry" ? (
            <>
              <Label htmlFor="azure-embed-deploy">ชื่อดีพลอยเมนต์ฝังเวกเตอร์</Label>
              <Input
                id="azure-embed-deploy"
                value={form.azure_foundry_embedding_deployment}
                onChange={(event) =>
                  patch("azure_foundry_embedding_deployment", event.target.value)
                }
              />
            </>
          ) : null}
        </div>
      ) : null}

      {showCloud && showCompatFields(form.llm_provider, form.embedding_provider) ? (
        <div className="gov-card space-y-3">
          <h2 className="font-semibold">OpenAI-compatible</h2>
          <Label htmlFor="compat-url">Base URL</Label>
          <Input
            id="compat-url"
            value={form.openai_compatible_base_url}
            onChange={(event) => patch("openai_compatible_base_url", event.target.value)}
          />
          <Label htmlFor="compat-key">API key</Label>
          <Input
            id="compat-key"
            type="password"
            value={form.openai_compatible_api_key}
            onChange={(event) => patch("openai_compatible_api_key", event.target.value)}
          />
          <Label htmlFor="compat-model">ชื่อโมเดลแชท</Label>
          <Input
            id="compat-model"
            value={form.openai_compatible_model}
            onChange={(event) => patch("openai_compatible_model", event.target.value)}
          />
          <Label htmlFor="compat-embed-model">ชื่อโมเดลฝังเวกเตอร์</Label>
          <Input
            id="compat-embed-model"
            value={form.openai_compatible_embedding_model}
            onChange={(event) =>
              patch("openai_compatible_embedding_model", event.target.value)
            }
          />
        </div>
      ) : null}

      <div className="gov-card space-y-3">
        <h2 className="font-semibold">PageIndex RAG (Knowledge-RAG)</h2>
        <p className="text-xs text-muted-foreground">
          ใช้ POST /api/search ของ Betimes Knowledge-RAG เป็นแหล่งทำความเข้าใจเอกสาร
          โดยเลือกใช้แทนหรือใช้ร่วมกับคลังเวกเตอร์เดิมได้
        </p>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={Boolean(form.custom_rag_enabled)}
            onChange={(event) => patch("custom_rag_enabled", event.target.checked)}
          />
          <span>เปิดใช้ PageIndex RAG</span>
        </label>
        <div>
          <Label htmlFor="custom-rag-url">Search endpoint URL</Label>
          <Input
            id="custom-rag-url"
            value={form.custom_rag_base_url}
            onChange={(event) => patch("custom_rag_base_url", event.target.value)}
            placeholder="https://knowledge-rag.example.com/api/search"
          />
        </div>
        <div>
          <Label htmlFor="custom-rag-key">Knowledge-RAG API key</Label>
          <Input
            id="custom-rag-key"
            type="password"
            value={form.custom_rag_api_key}
            onChange={(event) => patch("custom_rag_api_key", event.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="rag-sources">แหล่งดึงความรู้</Label>
          <Select
            id="rag-sources"
            value={form.rag_sources || "both"}
            onChange={(event) => patch("rag_sources", event.target.value)}
            options={RAG_SOURCE_OPTIONS}
          />
        </div>
        <div>
          <Label htmlFor="custom-rag-topk">top_k</Label>
          <Input
            id="custom-rag-topk"
            type="number"
            min={1}
            max={64}
            value={form.custom_rag_top_k}
            onChange={(event) =>
              patch("custom_rag_top_k", Number.parseInt(event.target.value, 10) || 24)
            }
          />
        </div>
        <div>
          <Label htmlFor="chat-rag-topk">ถาม-ตอบ top_k</Label>
          <Input
            id="chat-rag-topk"
            type="number"
            min={8}
            max={128}
            value={form.chat_rag_top_k}
            onChange={(event) =>
              patch("chat_rag_top_k", Number.parseInt(event.target.value, 10) || 96)
            }
          />
        </div>
        <div>
          <Label htmlFor="chat-max-chunks">ชิ้นบริบทสูงสุด</Label>
          <Input
            id="chat-max-chunks"
            type="number"
            min={16}
            max={128}
            value={form.chat_max_context_chunks}
            onChange={(event) =>
              patch(
                "chat_max_context_chunks",
                Number.parseInt(event.target.value, 10) || 96
              )
            }
          />
        </div>
        <div>
          <Label htmlFor="draft-rag-topk">ร่าง/ตรวจ TOR top_k</Label>
          <Input
            id="draft-rag-topk"
            type="number"
            min={8}
            max={96}
            value={form.draft_rag_top_k}
            onChange={(event) =>
              patch("draft_rag_top_k", Number.parseInt(event.target.value, 10) || 32)
            }
          />
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={testConnection}
          disabled={busy}
          data-testid="ai-settings-test"
        >
          ทดสอบการเชื่อมต่อ
        </Button>
        <Button type="button" onClick={save} disabled={busy} data-testid="ai-settings-save">
          {busy ? "กำลังทำงาน..." : "บันทึก"}
        </Button>
      </div>
    </div>
  );
}
