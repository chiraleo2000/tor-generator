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
});
