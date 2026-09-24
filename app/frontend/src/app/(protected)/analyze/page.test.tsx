import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import AnalyzePage from "./page";
import { apiClient } from "@/lib/api-client";
import { useProjectStore } from "@/stores/project-store";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

const PROJECT = {
  id: "p1",
  ownerId: "u1",
  name: "ร่างระบบจัดซื้อ",
  ministry: "กระทรวงทดสอบ",
  budget: 1000000,
  projectType: "hire_develop" as const,
  status: "draft" as const,
  currentStep: 1,
  currentPhase: 3,
  analysisJson: {},
  extractedFields: {},
  qualityScore: null,
  templateId: null,
  createdAt: "",
  updatedAt: "",
};

const ANALYSIS = {
  legal: {
    key: "legal",
    label: "ส่วนที่คาดว่าผิดกฎหมาย",
    score: 70,
    explanation: "หักจากค่าปรับ",
    findings: [{ reason: "อัตราค่าปรับสูงเกิน", suggested_text: "กำหนดค่าปรับร้อยละ 0.10 ต่อวัน" }],
  },
  lock_in: {
    key: "lock_in",
    label: "ความเสี่ยง lock specs",
    score: 60,
    explanation: "หักจาก Oracle",
    findings: [{ reason: "เจาะจง Oracle", suggested_text: "เพิ่มหรือเทียบเท่า" }],
  },
  project: {
    key: "project",
    label: "ความเสี่ยงบริหารโครงการ",
    score: 80,
    explanation: "ไม่พบประเด็นเข้างาน",
    findings: [],
  },
  total: 70,
  summary: "ความเสี่ยง lock specs ดึงคะแนนลง",
  recommendations: [
    {
      section_key: "s4",
      section_label: "ขอบเขตของงาน",
      source_count: 7,
      source_count_note: "พบ 7 แหล่งออนไลน์ประกอบหมวดนี้",
      legal_corpus_note: "แหล่งออนไลน์เป็นข้อมูลประกอบ หากถ้อยคำขัดกับคลังกฎหมาย ให้ยึดคลังกฎหมายก่อน",
      suggestions: [
        {
          part: "lock_in",
          part_label: "ความเสี่ยง lock specs",
          suggested_text: "ระบุความต้องการเชิงหน้าที่ หรือเพิ่มข้อความ หรือเทียบเท่า",
          reason: "การเจาะจงผลิตภัณฑ์",
          sources: [
            { title: "แหล่ง 1", url: "https://example.go.th/1", snippet: "แนวทาง TOR" },
          ],
        },
      ],
    },
  ],
};

describe("AnalyzePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useProjectStore.setState({
      projects: [PROJECT],
      isLoading: false,
      fetchProjects: vi.fn().mockResolvedValue(undefined),
    } as never);
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });

  it("switches four in-tool panels without leaving the page", () => {
    render(<AnalyzePage />);
    expect(screen.getByTestId("analyze-page")).toBeInTheDocument();
    expect(screen.getByTestId("analyze-tab-legal")).toHaveTextContent("ส่วนที่คาดว่าผิดกฎหมาย");
    expect(screen.getByTestId("analyze-tab-lock_in")).toHaveTextContent("lock specs");
    expect(screen.getByTestId("analyze-tab-project")).toHaveTextContent("บริหารโครงการ");
    expect(screen.getByTestId("analyze-tab-recommendations")).toHaveTextContent("ข้อเสนอแนะ");

    fireEvent.click(screen.getByTestId("analyze-tab-recommendations"));
    expect(screen.getByTestId("analyze-tab-recommendations").className).toContain("bg-brand-orange");
    fireEvent.click(screen.getByTestId("analyze-tab-project"));
    expect(screen.getByTestId("analyze-tab-project").className).toContain("bg-brand-orange");
  });

  it("posts pasted text and copies suggested TOR text without writing a draft", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { ok: true, data: ANALYSIS },
    } as never);
    render(<AnalyzePage />);
    fireEvent.change(screen.getByTestId("analyze-text"), {
      target: { value: "ร่าง TOR ทดสอบ Oracle โดยไม่มีหรือเทียบเท่า" },
    });
    fireEvent.click(screen.getByTestId("analyze-run"));
    await waitFor(() => expect(apiClient.post).toHaveBeenCalled());
    expect(apiClient.post).toHaveBeenCalledWith("/analyze", {
      text: "ร่าง TOR ทดสอบ Oracle โดยไม่มีหรือเทียบเท่า",
      project_id: undefined,
    });
    expect(await screen.findByTestId("analyze-summary")).toHaveTextContent("70/100");
    expect(screen.getByTestId("analyze-panel-legal")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("analyze-tab-recommendations"));
    expect(screen.getByTestId("analyze-source-count-s4")).toHaveTextContent("พบ 7 แหล่ง");
    fireEvent.click(screen.getByTestId("analyze-copy-s4-0"));
    await waitFor(() =>
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        "ระบุความต้องการเชิงหน้าที่ หรือเพิ่มข้อความ หรือเทียบเท่า"
      )
    );
    expect(apiClient.post).not.toHaveBeenCalledWith(
      expect.stringMatching(/sections/),
      expect.anything()
    );
  });

  it("sends a selected project id when no text is pasted", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { ok: true, data: ANALYSIS },
    } as never);
    render(<AnalyzePage />);
    fireEvent.change(screen.getByTestId("analyze-project"), {
      target: { value: "p1" },
    });
    fireEvent.click(screen.getByTestId("analyze-run"));
    await waitFor(() =>
      expect(apiClient.post).toHaveBeenCalledWith("/analyze", {
        text: undefined,
        project_id: "p1",
      })
    );
  });
});
