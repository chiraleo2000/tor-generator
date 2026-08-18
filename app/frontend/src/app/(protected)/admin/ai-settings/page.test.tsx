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

  it("loads local defaults then switches to cloud key fields", async () => {
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
    fireEvent.change(screen.getByLabelText("llama.cpp / custom URL"), {
      target: { value: "http://127.0.0.1:8080/v1" },
    });
    fireEvent.change(screen.getByLabelText("ชื่อโมเดลแชท"), { target: { value: "google/gemma-4-e4b" } });
    fireEvent.change(screen.getByLabelText("Timeout (วินาที)"), { target: { value: "120" } });

    fireEvent.change(screen.getByLabelText("โหมด"), { target: { value: "cloud" } });
    expect(screen.getByLabelText("โมเดลแชท")).toHaveValue("claude");
    expect(screen.queryByLabelText("LM Studio URL")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Anthropic API key")).toBeInTheDocument();
    expect(screen.getByLabelText("OpenAI API key")).toBeInTheDocument();
    expect(screen.getByLabelText("Gemini API key")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Anthropic API key"), { target: { value: "sk-ant" } });
    fireEvent.change(screen.getByLabelText("OpenAI API key"), { target: { value: "sk-openai" } });
    fireEvent.change(screen.getByLabelText("Gemini API key"), { target: { value: "gem" } });
    fireEvent.change(screen.getByLabelText("โมเดล OpenAI"), { target: { value: "gpt-4o-mini" } });
    fireEvent.change(screen.getByLabelText("โมเดล Gemini"), { target: { value: "gemini-2.0-flash" } });
    expect(screen.queryByRole("option", { name: "LM Studio" })).not.toBeInTheDocument();
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
});
