import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import AdminAiSettingsPage from "./page";
import { apiClient } from "@/lib/api-client";
import { EMPTY_AI_SETTINGS } from "@/lib/ai-settings";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    put: vi.fn(),
    post: vi.fn(),
  },
}));

const loaded = {
  ...EMPTY_AI_SETTINGS,
  llm_provider: "lm_studio",
  embedding_provider: "local",
};

describe("AdminAiSettingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.get).mockResolvedValue({ data: { ok: true, data: loaded } });
  });

  it("loads local defaults then keeps them when switching mode; mix Claude + local embed", async () => {
    render(<AdminAiSettingsPage />);
    expect(await screen.findByTestId("admin-ai-settings-page")).toBeInTheDocument();
    expect(screen.getByLabelText("โหมด")).toHaveValue("on_prem");
    expect(screen.getByLabelText("LM Studio URL")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("โมเดลแชท"), { target: { value: "ollama" } });
    fireEvent.change(screen.getByLabelText("คลังเวกเตอร์"), { target: { value: "qdrant" } });
    fireEvent.change(screen.getByLabelText("LM Studio URL"), {
      target: { value: "http://127.0.0.1:1234/v1" },
    });
    fireEvent.change(screen.getByLabelText("Ollama URL"), {
      target: { value: "http://127.0.0.1:11434/v1" },
    });
    fireEvent.change(screen.getByLabelText("llama.cpp / URL ที่กำหนดเอง"), {
      target: { value: "http://127.0.0.1:8080/v1" },
    });
    fireEvent.change(screen.getByLabelText("ชื่อโมเดลแชท (LM Studio / Ollama / llama.cpp)"), {
      target: { value: "google/gemma-4-e4b" },
    });
    fireEvent.change(screen.getByLabelText("หมดเวลารอ (วินาที)"), { target: { value: "120" } });

    fireEvent.change(screen.getByLabelText("โหมด"), { target: { value: "cloud" } });
    expect(screen.getByLabelText("โมเดลแชท")).toHaveValue("ollama");
    expect(screen.getByLabelText("LM Studio URL")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("โมเดลแชท"), { target: { value: "claude" } });
    expect(screen.getByLabelText("Anthropic API key")).toBeInTheDocument();
    expect(screen.getByLabelText("ฝังเวกเตอร์")).toHaveValue("local");
    expect(screen.getByLabelText("LM Studio URL")).toBeInTheDocument();
    expect(screen.getByLabelText("โมเดลแชท").querySelector("option[value='lm_studio']")).not.toBeNull();
    fireEvent.change(screen.getByLabelText("Anthropic API key"), { target: { value: "sk-ant" } });
  });

  it("saves and tests the connection", async () => {
    vi.mocked(apiClient.put).mockResolvedValue({
      data: { ok: true, data: { ...loaded, reingest_required: false } },
    });
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { ok: true, data: { message: "เชื่อมต่อเซิร์ฟเวอร์ในเครื่องได้" } },
    });
    render(<AdminAiSettingsPage />);
    await screen.findByTestId("ai-settings-save");

    fireEvent.click(screen.getByTestId("ai-settings-save"));
    expect(await screen.findByTestId("ai-settings-status")).toHaveTextContent("มีผลทันที");

    fireEvent.click(screen.getByTestId("ai-settings-test"));
    expect(await screen.findByTestId("ai-settings-status")).toHaveTextContent("เชื่อมต่อ");
  });

  it("shows an error when save fails", async () => {
    vi.mocked(apiClient.put).mockRejectedValue({
      response: { data: { error: { message: "บันทึกไม่สำเร็จ" } } },
    });
    render(<AdminAiSettingsPage />);
    await screen.findByTestId("ai-settings-save");
    fireEvent.click(screen.getByTestId("ai-settings-save"));
    expect(await screen.findByTestId("ai-settings-error")).toBeInTheDocument();
  });

  it("shows an error when the connection test fails", async () => {
    vi.mocked(apiClient.post).mockRejectedValue({
      response: { data: { error: { message: "ทดสอบไม่สำเร็จ" } } },
    });
    render(<AdminAiSettingsPage />);
    await screen.findByTestId("ai-settings-test");
    fireEvent.click(screen.getByTestId("ai-settings-test"));
    expect(await screen.findByTestId("ai-settings-error")).toBeInTheDocument();
  });

  it("shows a load error when GET fails", async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error("down"));
    render(<AdminAiSettingsPage />);
    expect(await screen.findByTestId("ai-settings-error")).toHaveTextContent(
      "โหลดการตั้งค่า AI ไม่สำเร็จ"
    );
  });

  it("mentions re-ingest when save reports it", async () => {
    vi.mocked(apiClient.put).mockResolvedValue({
      data: { ok: true, data: { ...loaded, reingest_required: true } },
    });
    render(<AdminAiSettingsPage />);
    await screen.findByTestId("ai-settings-save");
    fireEvent.click(screen.getByTestId("ai-settings-save"));
    expect(await screen.findByTestId("ai-settings-status")).toHaveTextContent("ฝังเวกเตอร์ใหม่");
  });

  it("reveals Gemini, Bedrock, and Azure fields from the selected providers", async () => {
    render(<AdminAiSettingsPage />);
    await screen.findByTestId("admin-ai-settings-page");
    fireEvent.change(screen.getByLabelText("โหมด"), { target: { value: "cloud" } });
    fireEvent.change(screen.getByLabelText("โมเดลแชท"), { target: { value: "gemini" } });
    fireEvent.change(screen.getByLabelText("ฝังเวกเตอร์"), { target: { value: "gemini" } });
    expect(screen.getByLabelText("Gemini API key")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Gemini API key"), { target: { value: "gem-key" } });
    fireEvent.change(screen.getByLabelText("โมเดล Gemini"), { target: { value: "gemini-2.0-flash" } });

    fireEvent.change(screen.getByLabelText("โมเดลแชท"), { target: { value: "bedrock" } });
    fireEvent.change(screen.getByLabelText("ฝังเวกเตอร์"), { target: { value: "bedrock" } });
    expect(screen.getByLabelText("ภูมิภาค")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("ภูมิภาค"), { target: { value: "ap-southeast-1" } });
    fireEvent.change(screen.getByLabelText("รหัสโมเดลแชท"), {
      target: { value: "anthropic.claude-sonnet" },
    });

    fireEvent.change(screen.getByLabelText("โมเดลแชท"), { target: { value: "azure_foundry" } });
    fireEvent.change(screen.getByLabelText("ฝังเวกเตอร์"), { target: { value: "azure_foundry" } });
    expect(screen.getByLabelText("Endpoint")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Endpoint"), {
      target: { value: "https://example.openai.azure.com" },
    });
    fireEvent.change(document.getElementById("azure-key") as HTMLInputElement, {
      target: { value: "az-key" },
    });

    fireEvent.change(screen.getByLabelText("โหมด"), { target: { value: "hybrid" } });
    expect(screen.getByLabelText("โหมด")).toHaveValue("hybrid");
    fireEvent.change(screen.getByLabelText("แหล่งดึงความรู้"), { target: { value: "local" } });
    fireEvent.change(screen.getByLabelText("top_k"), { target: { value: "12" } });
    fireEvent.change(screen.getByLabelText("ถาม-ตอบ top_k"), { target: { value: "32" } });
    fireEvent.change(screen.getByLabelText("ชิ้นบริบทสูงสุด"), { target: { value: "48" } });
    fireEvent.change(screen.getByLabelText("ร่าง/ตรวจ TOR top_k"), { target: { value: "16" } });
  });

  it("fills SGLang, OpenAI-compatible, Custom RAG, and empty numeric fallbacks", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { ok: true, data: {} },
    });
    render(<AdminAiSettingsPage />);
    await screen.findByTestId("admin-ai-settings-page");

    fireEvent.change(screen.getByLabelText("โมเดลแชท"), { target: { value: "sglang" } });
    fireEvent.change(screen.getByLabelText("เซิร์ฟเวอร์ฝังเวกเตอร์ในเครื่อง"), {
      target: { value: "sglang" },
    });
    fireEvent.change(screen.getByLabelText("URL ฝังเวกเตอร์ (เว้นว่างใช้ URL ของเซิร์ฟเวอร์ด้านบน)"), {
      target: { value: "http://127.0.0.1:30001/v1" },
    });
    fireEvent.change(screen.getByLabelText("SGLang แชท URL"), {
      target: { value: "http://127.0.0.1:30000/v1" },
    });
    fireEvent.change(screen.getByLabelText("SGLang embedding URL"), {
      target: { value: "http://127.0.0.1:30001/v1" },
    });
    fireEvent.change(screen.getByLabelText("โมเดลแชท SGLang"), { target: { value: "gemma" } });
    fireEvent.change(screen.getByLabelText("โมเดลฝังเวกเตอร์ SGLang"), {
      target: { value: "embed" },
    });
    fireEvent.change(screen.getByLabelText("ชื่อโมเดลฝังเวกเตอร์"), {
      target: { value: "nomic" },
    });
    fireEvent.change(screen.getByLabelText("หมดเวลารอ (วินาที)"), { target: { value: "" } });

    fireEvent.change(screen.getByLabelText("โหมด"), { target: { value: "cloud" } });
    fireEvent.change(screen.getByLabelText("โมเดลแชท"), { target: { value: "openai" } });
    fireEvent.change(screen.getByLabelText("ฝังเวกเตอร์"), { target: { value: "openai" } });
    fireEvent.change(screen.getByLabelText("OpenAI API key"), { target: { value: "sk-oai" } });
    fireEvent.change(screen.getByLabelText("โมเดล OpenAI แชท"), { target: { value: "gpt-4o" } });
    fireEvent.change(screen.getByLabelText("โมเดลฝังเวกเตอร์ OpenAI"), {
      target: { value: "text-embedding-3-large" },
    });
    fireEvent.change(screen.getByLabelText("โมเดลฝังเวกเตอร์ Gemini"), {
      target: { value: "text-embedding-004" },
    });

    fireEvent.change(screen.getByLabelText("โมเดลแชท"), { target: { value: "bedrock" } });
    fireEvent.change(screen.getByLabelText("ฝังเวกเตอร์"), { target: { value: "bedrock" } });
    fireEvent.change(screen.getByLabelText("รหัสโมเดลฝังเวกเตอร์"), {
      target: { value: "amazon.titan-embed" },
    });
    fireEvent.change(screen.getByLabelText("AWS access key (เว้นว่างได้ถ้าใช้ IAM role)"), {
      target: { value: "AKIA" },
    });
    fireEvent.change(screen.getByLabelText("AWS secret"), { target: { value: "secret" } });

    fireEvent.change(screen.getByLabelText("โมเดลแชท"), { target: { value: "azure_foundry" } });
    fireEvent.change(screen.getByLabelText("ฝังเวกเตอร์"), { target: { value: "azure_foundry" } });
    fireEvent.change(screen.getByLabelText("Deployment (แชท)"), { target: { value: "chat-dep" } });
    fireEvent.change(screen.getByLabelText("ชื่อดีพลอยเมนต์ฝังเวกเตอร์"), {
      target: { value: "embed-dep" },
    });

    fireEvent.change(screen.getByLabelText("โมเดลแชท"), { target: { value: "openai_compatible" } });
    fireEvent.change(screen.getByLabelText("ฝังเวกเตอร์"), { target: { value: "openai_compatible" } });
    fireEvent.change(document.getElementById("compat-url") as HTMLInputElement, {
      target: { value: "https://compat.example/v1" },
    });
    fireEvent.change(document.getElementById("compat-key") as HTMLInputElement, {
      target: { value: "compat-key" },
    });
    fireEvent.change(document.getElementById("compat-model") as HTMLInputElement, {
      target: { value: "local-chat" },
    });
    fireEvent.change(document.getElementById("compat-embed-model") as HTMLInputElement, {
      target: { value: "local-embed" },
    });

    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.change(document.getElementById("custom-rag-url") as HTMLInputElement, {
      target: { value: "https://rag.example.com" },
    });
    fireEvent.change(document.getElementById("custom-rag-key") as HTMLInputElement, {
      target: { value: "rag-key" },
    });
    fireEvent.change(screen.getByLabelText("top_k"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText("ถาม-ตอบ top_k"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText("ชิ้นบริบทสูงสุด"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText("ร่าง/ตรวจ TOR top_k"), { target: { value: "" } });

    fireEvent.click(screen.getByTestId("ai-settings-test"));
    expect(await screen.findByTestId("ai-settings-status")).toHaveTextContent("เชื่อมต่อได้");
  });
});
