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
    expect(apiClient.post).toHaveBeenCalledWith(
      "/analyze",
      {
        text: "ร่าง TOR ทดสอบ Oracle โดยไม่มีหรือเทียบเท่า",
        project_id: undefined,
      },
      { timeout: 60_000 }
    );
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
      expect(apiClient.post).toHaveBeenCalledWith(
        "/analyze",
        {
          text: undefined,
          project_id: "p1",
        },
        { timeout: 60_000 }
      )
    );
  });

  it("shows กำลังวิเคราะห์ immediately and keeps the in-tool nav usable", async () => {
    let resolvePost: (value: unknown) => void = () => undefined;
    vi.mocked(apiClient.post).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolvePost = resolve;
        })
    );
    render(<AnalyzePage />);
    fireEvent.change(screen.getByTestId("analyze-text"), {
      target: { value: "ร่าง TOR เพื่อดูสถานะ" },
    });
    fireEvent.click(screen.getByTestId("analyze-run"));
    expect(screen.getByTestId("analyze-status")).toHaveTextContent("กำลังวิเคราะห์");
    expect(screen.getByTestId("analyze-tab-bidder_risk")).toBeEnabled();
    expect(screen.getByTestId("analyze-tab-legal")).toBeEnabled();
    resolvePost({ data: { ok: true, data: ANALYSIS } });
    await waitFor(() =>
      expect(screen.getByTestId("analyze-status")).toHaveTextContent("วิเคราะห์เสร็จ")
    );
    expect(screen.getByTestId("analyze-run")).toBeEnabled();
  });

  it("asks for text when nothing is selected and shows a failed analysis", async () => {
    render(<AnalyzePage />);
    fireEvent.click(screen.getByTestId("analyze-run"));
    expect(screen.getByRole("alert")).toHaveTextContent("วางข้อความ TOR");

    fireEvent.change(screen.getByTestId("analyze-text"), {
      target: { value: "ร่างที่วิเคราะห์ไม่สำเร็จ" },
    });
    vi.mocked(apiClient.post).mockRejectedValue(new Error("เซิร์ฟเวอร์ไม่ตอบ"));
    fireEvent.click(screen.getByTestId("analyze-run"));
    expect(await screen.findByRole("alert")).toHaveTextContent("วิเคราะห์ TOR ไม่สำเร็จ");
    expect(screen.getByTestId("analyze-status")).toHaveTextContent("วิเคราะห์ TOR ไม่สำเร็จ");
  });

  it("rejects a malformed payload and shows the empty risk slot", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { ok: true, data: { summary: "ไม่ครบ" } },
    } as never);
    render(<AnalyzePage />);
    fireEvent.change(screen.getByTestId("analyze-text"), {
      target: { value: "ร่างที่รูปแบบผิด" },
    });
    fireEvent.click(screen.getByTestId("analyze-run"));
    expect(await screen.findByRole("alert")).toHaveTextContent("วิเคราะห์ TOR ไม่สำเร็จ");

    vi.mocked(apiClient.post).mockResolvedValue({
      data: { ok: true, data: ANALYSIS },
    } as never);
    fireEvent.click(screen.getByTestId("analyze-run"));
    await screen.findByTestId("analyze-summary");
    fireEvent.click(screen.getByTestId("analyze-tab-bidder_risk"));
    expect(screen.getByTestId("bidder-risk-panel")).toHaveTextContent("ยังไม่มีรายงานความเสี่ยง");
    fireEvent.click(screen.getByTestId("analyze-tab-lock_in"));
    expect(screen.getByTestId("analyze-panel-lock_in")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("analyze-tab-project"));
    expect(screen.getByTestId("analyze-panel-project")).toBeInTheDocument();
  });

  it("leaves the copy key unset when the clipboard rejects the text", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { ok: true, data: ANALYSIS },
    } as never);
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockRejectedValue(new Error("denied")) },
    });
    render(<AnalyzePage />);
    fireEvent.change(screen.getByTestId("analyze-text"), {
      target: { value: "ร่างสำหรับคัดลอก" },
    });
    fireEvent.click(screen.getByTestId("analyze-run"));
    await screen.findByTestId("analyze-summary");
    fireEvent.click(screen.getByTestId("analyze-tab-recommendations"));
    fireEvent.click(screen.getByTestId("analyze-copy-s4-0"));
    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalled());
    expect(screen.queryByText("คัดลอกแล้ว")).not.toBeInTheDocument();
  });

  it("opens the pre-bid risk panel with the table and recommendation", async () => {
    const risk = {
      ...ANALYSIS,
      bidder_risk: {
        recommendation: "ไม่ควรยื่นในสถานะข้อมูลปัจจุบัน",
        disclaimer: "เป็นความเห็นเชิงบริหารโครงการจากข้อความ TOR",
        gates: ["ย้ายข้อมูลได้จริง"],
        penalty: {
          base_label: "มูลค่าสัญญาทั้งหมด",
          baht_per_day: 27340,
          amount_30_days: 820200,
          amount_60_days: 1640400,
          amount_note: "27,340 บาท/วัน",
        },
        categories: [
          {
            key: "clarity",
            label: "ความชัดเจนและปริมาณงาน",
            rows: [
              {
                issue: "การย้ายข้อมูลยังไม่ชัด",
                requirement: "«ตามที่ผู้ว่าจ้างกำหนด» (ไม่พบเลขหน้า)",
                impact: "ประเมินปริมาณไม่ได้",
                level: "สูงมาก",
                mitigation: "ขอปริมาณข้อมูลก่อนยื่น",
              },
            ],
          },
          { key: "external", label: "ความร่วมมือกับหน่วยงานภายนอก", rows: [] },
          { key: "schedule", label: "ระยะเวลา × งานที่ต้องส่งมอบ", rows: [] },
          {
            key: "infrastructure",
            label: "รายการอุปกรณ์ / Infrastructure × กำหนดส่งงาน และการผูกกับเทคโนโลยี",
            rows: [],
          },
          { key: "penalty", label: "ความเสี่ยงค่าปรับพร้อมจำนวนเงิน", rows: [] },
          { key: "security", label: "ความปลอดภัย / กรรมสิทธิ์ / ต้นทุนอื่น", rows: [] },
        ],
        markdown: "# ความเสี่ยงก่อนตัดสินใจยื่น\n\nไม่ควรยื่นในสถานะข้อมูลปัจจุบัน",
      },
    };
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { ok: true, data: risk },
    } as never);
    render(<AnalyzePage />);
    fireEvent.change(screen.getByTestId("analyze-text"), {
      target: { value: "ร่างที่มีความเสี่ยงก่อนยื่น" },
    });
    fireEvent.click(screen.getByTestId("analyze-run"));
    await screen.findByTestId("analyze-summary");
    fireEvent.click(screen.getByTestId("analyze-tab-bidder_risk"));
    expect(screen.getByTestId("bidder-risk-recommendation")).toHaveTextContent("ไม่ควรยื่น");
    expect(screen.getByTestId("bidder-risk-table-clarity")).toHaveTextContent("การย้ายข้อมูลยังไม่ชัด");
    expect(screen.getByTestId("bidder-risk-penalty")).toHaveTextContent("27,340");
    expect(screen.getByTestId("analyze-tab-bidder_risk").compareDocumentPosition(
      screen.getByTestId("analyze-tab-recommendations")
    )).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    fireEvent.click(screen.getByTestId("bidder-risk-copy"));
    await waitFor(() =>
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        expect.stringContaining("ไม่ควรยื่นในสถานะข้อมูลปัจจุบัน")
      )
    );
  });
});
