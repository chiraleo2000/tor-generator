import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Phase4Review } from "@/components/draft/phase4-review";
import { apiClient } from "@/lib/api-client";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

describe("Phase4Review", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { ok: true, data: { has_requirements: false } },
    } as never);
  });

  it("warns when sections are incomplete", async () => {
    render(
      <Phase4Review
        projectId="p1"
        filledCount={10}
        total={13}
        score={null}
        findings={[]}
        suggestions={[]}
        busy={false}
        error={null}
        onBack={vi.fn()}
        onReview={vi.fn().mockResolvedValue(undefined)}
        onSubmit={vi.fn().mockResolvedValue(undefined)}
      />
    );
    expect(await screen.findByTestId("phase4-review")).toHaveTextContent(
      "ยังกรอกไม่ครบทุกหมวด"
    );
    expect(screen.queryByText("ยังไม่ได้ยืนยันหมวดที่เจ้าหน้าที่ต้องตรวจ")).not.toBeInTheDocument();
    expect(screen.getByText("ส่งขออนุมัติ")).toBeDisabled();
    expect(screen.getByTestId("phase4-submit-hint")).toHaveTextContent(
      "กรอกให้ครบทุกหมวดตามประเภทงานก่อนส่งขออนุมัติ"
    );
  });

  it("shows score, findings, suggestions, and runs review", async () => {
    const onReview = vi.fn().mockResolvedValue(undefined);
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const onBack = vi.fn();
    render(
      <Phase4Review
        projectId="p1"
        filledCount={13}
        total={13}
        score={82}
        findings={[
          {
            severity: "warning",
            rule: "budget",
            section: "s6",
            message: "วงเงินไม่สอดคล้อง",
            recommendation: "ตรวจตัวเลข",
          },
        ]}
        suggestions={[
          {
            id: "sug-1",
            section_key: "s1",
            category: "ความชัดเจน",
            suggested_text: "ระบุหน่วยงานให้ชัด",
          },
        ]}
        busy={false}
        error={null}
        onBack={onBack}
        onReview={onReview}
        onSubmit={onSubmit}
      />
    );
    expect(await screen.findByText("ข้อมูลครบถ้วนทุกหมวด พร้อมส่งทบทวน")).toBeInTheDocument();
    expect(screen.getByText("คะแนนคุณภาพจากการตรวจกฎ 82/100")).toBeInTheDocument();
    expect(screen.queryByTestId("review-part-scores")).not.toBeInTheDocument();
    expect(screen.getByTestId("review-legal-findings")).toHaveTextContent("วงเงินไม่สอดคล้อง");
    expect(screen.getByTestId("review-risk-findings")).toHaveTextContent("ไม่พบรายการในกลุ่มนี้");
    expect(screen.getByText("ความชัดเจน: ระบุหน่วยงานให้ชัด")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("run-review"));
    expect(onReview).toHaveBeenCalled();
    expect(screen.queryByTestId("phase4-submit-hint")).toBeNull();
    fireEvent.click(screen.getByTestId("phase4-submit"));
    expect(onSubmit).toHaveBeenCalled();
    fireEvent.click(screen.getByTestId("phase3-back"));
    expect(onBack).toHaveBeenCalled();
  });

  it("shows three-part scores and the part that pulled the total down", async () => {
    render(
      <Phase4Review
        projectId="p1"
        filledCount={13}
        total={13}
        score={64}
        partScores={{
          legal: {
            key: "legal",
            label: "ส่วนที่คาดว่าผิดกฎหมาย",
            score: 80,
            explanation: "ตรวจตาม พ.ร.บ. แล้วไม่พบประเด็นในด้านกฎหมาย",
            findings: [],
          },
          lock_in: {
            key: "lock_in",
            label: "ความเสี่ยง lock specs",
            score: 40,
            explanation: "หักเพราะระบุ Oracle โดยไม่มีหรือเทียบเท่า",
            findings: [
              {
                source_quote: "ฐานข้อมูล Oracle Processor",
                reason: "เจาะจงผลิตภัณฑ์โดยไม่มีหรือเทียบเท่า",
                suggested_text: "ใช้คุณสมบัติเชิงหน้าที่ หรือเทียบเท่า",
              },
            ],
          },
          project: {
            key: "project",
            label: "ความเสี่ยงบริหารโครงการ",
            score: 70,
            explanation: "มีประเด็นระยะเวลา",
            findings: [],
          },
          total: 64,
          summary: "คะแนนรวมถูกดึงลงจากความเสี่ยง lock specs (40/100) มากที่สุด",
        }}
        findings={[]}
        suggestions={[]}
        busy={false}
        error={null}
        onBack={vi.fn()}
        onReview={vi.fn().mockResolvedValue(undefined)}
        onSubmit={vi.fn().mockResolvedValue(undefined)}
      />
    );
    expect(await screen.findByTestId("review-part-scores")).toHaveTextContent(
      "คะแนนรวมสามด้าน 64/100"
    );
    expect(screen.getByTestId("review-part-legal")).toHaveTextContent("ไม่พบประเด็นในด้านกฎหมาย");
    expect(screen.getByTestId("review-part-lock-in")).toHaveTextContent("Oracle");
    expect(screen.getByTestId("review-part-project")).toHaveTextContent("บริหารโครงการ");
    expect(screen.getByText(/ดึงลงจากความเสี่ยง lock specs/)).toBeInTheDocument();
  });

  it("shows a review error and busy label", async () => {
    render(
      <Phase4Review
        projectId="p1"
        filledCount={13}
        total={13}
        score={40}
        findings={[]}
        suggestions={[]}
        busy
        error="ตรวจไม่สำเร็จ"
        onBack={vi.fn()}
        onReview={vi.fn().mockResolvedValue(undefined)}
        onSubmit={vi.fn().mockResolvedValue(undefined)}
      />
    );
    await waitFor(() =>
      expect(screen.getByTestId("run-review")).toHaveTextContent("กำลังตรวจสอบ...")
    );
    expect(screen.getByRole("alert")).toHaveTextContent("ตรวจไม่สำเร็จ");
  });

  it("uploads extra requirements and clears them", async () => {
    vi.mocked(apiClient.get)
      .mockResolvedValueOnce({
        data: { ok: true, data: { has_requirements: false } },
      } as never)
      .mockResolvedValueOnce({
        data: { ok: true, data: { preview: "ข้อกำหนดเฉพาะโครงการจัดซื้อ" } },
      } as never);
    vi.mocked(apiClient.post).mockResolvedValue({ data: { ok: true } } as never);
    vi.mocked(apiClient.delete).mockResolvedValue({ data: { ok: true } } as never);
    const { container } = render(
      <Phase4Review
        projectId="p1"
        filledCount={13}
        total={13}
        score={70}
        findings={[]}
        suggestions={[]}
        busy={false}
        error={null}
        onBack={vi.fn()}
        onReview={vi.fn().mockResolvedValue(undefined)}
        onSubmit={vi.fn().mockResolvedValue(undefined)}
      />
    );
    await waitFor(() =>
      expect(container.querySelector('input[type="file"]')).toBeTruthy()
    );
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["spec"], "reqs.txt", { type: "text/plain" });
    fireEvent.change(input, { target: { files: [file] } });
    expect(await screen.findByText(/ข้อกำหนดเฉพาะโครงการจัดซื้อ/)).toBeInTheDocument();
    fireEvent.click(screen.getByText("ลบข้อกำหนด"));
    await waitFor(() => expect(apiClient.delete).toHaveBeenCalled());
  });

  it("shows a load error when requirements GET fails", async () => {
    vi.mocked(apiClient.get).mockRejectedValue({
      response: { status: 500, data: { error: { message: "โหลดข้อกำหนดไม่สำเร็จ" } } },
    });
    render(
      <Phase4Review
        projectId="p1"
        filledCount={13}
        total={13}
        score={null}
        findings={[]}
        suggestions={[]}
        busy={false}
        error={null}
        onBack={vi.fn()}
        onReview={vi.fn().mockResolvedValue(undefined)}
        onSubmit={vi.fn().mockResolvedValue(undefined)}
      />
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("โหลดข้อกำหนดไม่สำเร็จ");
  });

  it("ignores a missing requirements route and surfaces upload or delete errors", async () => {
    vi.mocked(apiClient.get).mockRejectedValue({ response: { status: 404 } });
    const { container } = render(
      <Phase4Review
        projectId="p1"
        filledCount={13}
        total={13}
        score={70}
        findings={[]}
        suggestions={[]}
        busy={false}
        error={null}
        onBack={vi.fn()}
        onReview={vi.fn().mockResolvedValue(undefined)}
        onSubmit={vi.fn().mockResolvedValue(undefined)}
      />
    );
    await waitFor(() =>
      expect(container.querySelector('input[type="file"]')).toBeTruthy()
    );
    vi.mocked(apiClient.post).mockRejectedValue({
      response: { data: { error: { message: "อัปโหลดข้อกำหนดไม่สำเร็จ" } } },
    });
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, {
      target: { files: [new File(["spec"], "reqs.txt", { type: "text/plain" })] },
    });
    expect(await screen.findByRole("alert")).toHaveTextContent("อัปโหลดข้อกำหนดไม่สำเร็จ");
  });

  it("surfaces a requirements delete error", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { ok: true, data: { has_requirements: true, preview: "ข้อกำหนดเดิม" } },
    } as never);
    vi.mocked(apiClient.delete).mockRejectedValue({
      response: { data: { error: { message: "ลบข้อกำหนดไม่สำเร็จ" } } },
    });
    render(
      <Phase4Review
        projectId="p1"
        filledCount={13}
        total={13}
        score={70}
        findings={[]}
        suggestions={[]}
        busy={false}
        error={null}
        onBack={vi.fn()}
        onReview={vi.fn().mockResolvedValue(undefined)}
        onSubmit={vi.fn().mockResolvedValue(undefined)}
      />
    );
    fireEvent.click(await screen.findByText("ลบข้อกำหนด"));
    expect(await screen.findByRole("alert")).toHaveTextContent("ลบข้อกำหนดไม่สำเร็จ");
  });

  it("assembles parent sections and 4.n subsections with tables", async () => {
    const table = [
      "| รายการ | รายละเอียด |",
      "| --- | --- |",
      "| งวดที่ ๑ | ส่งมอบรายงานวิเคราะห์ |",
    ].join("\n");
    render(
      <Phase4Review
        projectId="p1"
        sections={[
          {
            key: "s1",
            title: "ความเป็นมา",
            content: "กรมบัญชีกลางจัดซื้อระบบบริหารสัญญา",
            filled: true,
            human_confirmed: false,
            hitl: false,
            matchStatus: "matched",
          },
          {
            key: "s4",
            title: "ขอบเขตของงาน",
            content: "สรุปสั้น",
            filled: true,
            human_confirmed: false,
            hitl: false,
            matchStatus: "matched",
            subs: [
              { key: "s4.1", title: "สรุปขอบเขตงาน", content: "วิเคราะห์ความต้องการและพัฒนาโมดูล", filled: true },
              { key: "s4.8", title: "ผลงานส่งมอบ", content: table, filled: true },
            ],
          },
        ]}
        filledCount={13}
        total={13}
        score={null}
        findings={[]}
        suggestions={[]}
        busy={false}
        error={null}
        onBack={vi.fn()}
        onReview={vi.fn().mockResolvedValue(undefined)}
        onSubmit={vi.fn().mockResolvedValue(undefined)}
      />
    );
    const preview = await screen.findByTestId("phase4-merged-preview");
    expect(preview).toHaveTextContent("4.1");
    expect(preview).toHaveTextContent("4.8");
    expect(preview.querySelector("table")).toBeTruthy();
    expect(screen.queryByText("s4.s4.1")).not.toBeInTheDocument();
  });

  it("shows only the bid recommendation line, not the six risk tables", async () => {
    render(
      <Phase4Review
        projectId="p1"
        filledCount={13}
        total={13}
        score={80}
        partScores={{
          legal: {
            key: "legal",
            label: "ส่วนที่คาดว่าผิดกฎหมาย",
            score: 90,
            explanation: "ไม่พบประเด็น",
            findings: [],
          },
          lock_in: {
            key: "lock_in",
            label: "ความเสี่ยง lock specs",
            score: 90,
            explanation: "ไม่พบประเด็น",
            findings: [],
          },
          project: {
            key: "project",
            label: "ความเสี่ยงบริหารโครงการ",
            score: 90,
            explanation: "ไม่พบประเด็น",
            findings: [],
          },
          total: 90,
          summary: "ทั้งสามด้านได้คะแนนสูงใกล้เคียงกัน",
          bidder_risk: {
            recommendation: "ไม่ควรยื่นในสถานะข้อมูลปัจจุบัน",
            categories: [
              {
                key: "clarity",
                label: "ความชัดเจนและปริมาณงาน",
                rows: [{ issue: "ย้ายข้อมูล", requirement: "อ้างอิง", impact: "ค้าง", level: "สูงมาก", mitigation: "ถาม" }],
              },
            ],
          },
        }}
        findings={[]}
        suggestions={[]}
        busy={false}
        error={null}
        onBack={vi.fn()}
        onReview={vi.fn().mockResolvedValue(undefined)}
        onSubmit={vi.fn().mockResolvedValue(undefined)}
      />
    );
    expect(await screen.findByTestId("phase4-bid-recommendation")).toHaveTextContent(
      "ไม่ควรยื่นในสถานะข้อมูลปัจจุบัน"
    );
    expect(screen.queryByTestId("bidder-risk-table-clarity")).not.toBeInTheDocument();
    expect(screen.queryByTestId("bidder-risk-panel")).not.toBeInTheDocument();
  });
});
