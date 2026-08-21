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

  it("warns when sections and HITL are incomplete", async () => {
    render(
      <Phase4Review
        projectId="p1"
        filledCount={10}
        total={13}
        hitlReady={false}
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
    expect(screen.getByText("ยังไม่ได้ยืนยันหมวดที่เจ้าหน้าที่ต้องตรวจ")).toBeInTheDocument();
    expect(screen.getByText("ส่งขออนุมัติ / สร้าง TOR")).toBeDisabled();
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
        hitlReady
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
    expect(screen.getByText("คะแนนคุณภาพจาก Rule Engine 82/100")).toBeInTheDocument();
    expect(screen.getByText("วงเงินไม่สอดคล้อง")).toBeInTheDocument();
    expect(screen.getByText("ความชัดเจน: ระบุหน่วยงานให้ชัด")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("run-review"));
    expect(onReview).toHaveBeenCalled();
    fireEvent.click(screen.getByText("ส่งขออนุมัติ / สร้าง TOR"));
    expect(onSubmit).toHaveBeenCalled();
    fireEvent.click(screen.getByTestId("phase3-back"));
    expect(onBack).toHaveBeenCalled();
  });

  it("shows a review error and busy label", async () => {
    render(
      <Phase4Review
        projectId="p1"
        filledCount={13}
        total={13}
        hitlReady
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
        hitlReady
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
        hitlReady
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
});
