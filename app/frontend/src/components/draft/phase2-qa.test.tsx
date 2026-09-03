import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { Phase2Qa } from "@/components/draft/phase2-qa";
import { apiClient } from "@/lib/api-client";

vi.mock("@/components/draft/draft-conversation", () => ({
  DraftConversation: ({
    onCoverage,
  }: {
    onCoverage?: (
      rows: { key: string; label: string; status: string; filled: boolean; fact_required: boolean }[]
    ) => void;
  }) => (
    <button
      type="button"
      data-testid="draft-conversation"
      onClick={() =>
        onCoverage?.([
          { key: "s1", label: "ชื่อโครงการ", status: "filled", filled: true, fact_required: true },
        ])
      }
    >
      conversation
    </button>
  ),
}));

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

const coverage = [
  {
    key: "s1",
    label: "ความเป็นมา",
    status: "filled",
    filled: true,
    fact_required: true,
    preview: "กรมบัญชีกลางจัดซื้อระบบบริหารสัญญา",
  },
  {
    key: "s10",
    label: "อัตราค่าปรับ",
    status: "gap",
    filled: false,
    fact_required: false,
  },
];

const baseProps = {
  projectId: "p1",
  ready: false,
  busy: false,
  message: null as string | null,
  isError: false,
  apiBase: "/api/v1",
  onConfirmReady: vi.fn(),
  onChatReady: vi.fn(),
};

describe("Phase2Qa", () => {
  it("keeps confirm disabled until required facts are filled", () => {
    render(
      <Phase2Qa
        {...baseProps}
        coverage={[
          {
            key: "s1",
            label: "ชื่อโครงการ",
            status: "gap",
            filled: false,
            fact_required: true,
          },
        ]}
      />
    );
    expect(screen.getByTestId("intake-confirm-ready")).toBeDisabled();
    expect(screen.getByText(/ยังขาด ชื่อโครงการ/)).toBeInTheDocument();
    expect(screen.getByText("รายละเอียดที่จัดเข้าช่อง")).toBeInTheDocument();
    expect(screen.getByTestId("draft-conversation")).toBeInTheDocument();
  });

  it("shows the coverage table and confirms without a fill-reference button", () => {
    const onConfirmReady = vi.fn();
    render(
      <Phase2Qa
        {...baseProps}
        coverage={coverage}
        ready
        message="พร้อมไปร่าง"
        onConfirmReady={onConfirmReady}
      />
    );
    expect(screen.getByTestId("coverage-row-s1")).toHaveAttribute("data-status", "filled");
    expect(screen.getByTestId("coverage-row-s1")).toHaveTextContent("กรมบัญชีกลาง");
    expect(screen.queryByText("ดึงอ้างอิงกฎหมาย")).not.toBeInTheDocument();
    expect(screen.queryByTestId("intake-ref-chips")).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId("intake-confirm-ready"));
    expect(onConfirmReady).toHaveBeenCalledTimes(1);
    expect(screen.getByText("ยืนยันพร้อมร่างแล้ว")).toBeInTheDocument();
  });

  it("shows an error alert", () => {
    render(
      <Phase2Qa
        {...baseProps}
        coverage={[]}
        message="ยังไม่ครบช่องข้อเท็จจริงที่บังคับ"
        isError
      />
    );
    expect(screen.getByRole("alert")).toHaveTextContent("ยังไม่ครบช่องข้อเท็จจริงที่บังคับ");
  });

  it("reports a fill-references failure", async () => {
    vi.mocked(apiClient.post).mockRejectedValue({
      response: { data: { error: { message: "ดึงมาตรฐานกลางไม่สำเร็จ" } } },
    });
    render(<Phase2Qa {...baseProps} coverage={coverage} onCoverage={vi.fn()} />);
    fireEvent.click(screen.getByTestId("phase2-apply-standards"));
    expect(await screen.findByText("ดึงมาตรฐานกลางไม่สำเร็จ")).toBeInTheDocument();
  });

  it("forwards coverage updates from the conversation into onCoverage and onChatReady", () => {
    const onCoverage = vi.fn();
    const onChatReady = vi.fn();
    render(
      <Phase2Qa {...baseProps} coverage={coverage} onCoverage={onCoverage} onChatReady={onChatReady} />
    );
    fireEvent.click(screen.getByTestId("draft-conversation"));
    expect(onCoverage).toHaveBeenCalled();
    expect(onChatReady).toHaveBeenCalled();
  });
});
