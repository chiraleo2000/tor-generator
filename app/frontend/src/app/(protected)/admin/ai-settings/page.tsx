"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import {
  EMPTY_AI_SETTINGS,
  VECTOR_STORES,
  embedOptionsForMode,
  llmOptionsForMode,
  nextFormOnModeChange,
  saveSuccessMessage,
  showCloudKeyFields,
  showLocalServerFields,
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
        anthropic_api_key: form.anthropic_api_key,
        openai_api_key: form.openai_api_key,
        gemini_api_key: form.gemini_api_key,
      });
      const payload = unwrapData<{ message?: string }>(response);
      setMessage(payload.message || "เชื่อมต่อได้");
    } catch (err: unknown) {
      setError(apiErrorMessage(err, "ทดสอบไม่สำเร็จ"));
    } finally {
      setBusy(false);
    }
  }

  const showLocal = showLocalServerFields(form.deployment_mode, form.llm_provider);
  const showCloud = showCloudKeyFields(form.deployment_mode, form.llm_provider);

  return (
    <div className="max-w-3xl mx-auto space-y-6" data-testid="admin-ai-settings-page">
      <div className="gov-card">
        <h1 className="text-2xl font-extrabold text-navy">การตั้งค่า AI</h1>
        <p className="text-sm text-muted-foreground mt-1">
          ค่าเริ่มต้นคือรันในเครื่องผ่าน LM Studio ที่พอร์ต 1234 (Gemma + EmbeddingGemma-300M)
          การบันทึกมีผลทันที ไม่ต้องรีสตาร์ท backend หากเปลี่ยนผู้ให้บริการหรือโมเดล embeddings
          ต้องประมวลผลฐานความรู้ใหม่ (`python -m app.seed_kb`)
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
              { value: "on_prem", label: "รันในเครื่อง (Local)" },
              { value: "cloud", label: "คลาวด์ (Cloud API)" },
              { value: "hybrid", label: "ผสม (Hybrid)" },
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
          <Label htmlFor="ai-embed">Embeddings</Label>
          <Select
            id="ai-embed"
            value={form.embedding_provider}
            onChange={(event) => patch("embedding_provider", event.target.value)}
            options={embedOptionsForMode(form.deployment_mode)}
          />
        </div>

        <div>
          <Label htmlFor="vector-store">คลังเวกเตอร์</Label>
          <Select
            id="vector-store"
            value={form.vector_store_provider}
            onChange={(event) => patch("vector_store_provider", event.target.value)}
            options={VECTOR_STORES}
          />
        </div>
      </div>

      {showLocal ? (
        <div className="gov-card space-y-3">
          <h2 className="font-semibold">เซิร์ฟเวอร์ในเครื่อง</h2>
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
            <Label htmlFor="llama-url">llama.cpp / custom URL</Label>
            <Input
              id="llama-url"
              value={form.llama_cpp_base_url}
              onChange={(event) => patch("llama_cpp_base_url", event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="chat-model">ชื่อโมเดลแชท</Label>
            <Input
              id="chat-model"
              value={form.lm_studio_model}
              onChange={(event) => patch("lm_studio_model", event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="embed-model">ชื่อโมเดล embeddings</Label>
            <Input
              id="embed-model"
              value={form.lm_studio_embedding_model}
              onChange={(event) => patch("lm_studio_embedding_model", event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="timeout">Timeout (วินาที)</Label>
            <Input
              id="timeout"
              type="number"
              min={1}
              max={300}
              value={form.lm_studio_timeout}
              onChange={(event) =>
                patch("lm_studio_timeout", Number.parseFloat(event.target.value) || 180)
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
            <Label htmlFor="openai-model">โมเดล OpenAI</Label>
            <Input
              id="openai-model"
              value={form.openai_chat_model}
              onChange={(event) => patch("openai_chat_model", event.target.value)}
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
            <Label htmlFor="gemini-embed-model">โมเดล Gemini embeddings</Label>
            <Input
              id="gemini-embed-model"
              value={form.gemini_embedding_model}
              onChange={(event) => patch("gemini_embedding_model", event.target.value)}
            />
          </div>
        </div>
      ) : null}

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
