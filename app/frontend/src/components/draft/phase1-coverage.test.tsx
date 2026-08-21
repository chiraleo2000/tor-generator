import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { Phase1Coverage } from "@/components/draft/phase1-coverage";

const emptyHandlers = {
  coverage: [
    { key: "s1", label: "ชื่อโครงการ", status: "filled", filled: true, fact_required: true },
  ],
  gaps: [],
  busy: false,
  message: null,
  isError: false,
  onEnterQa: vi.fn(),
};

describe("Phase1Coverage", () => {
  it("shows fill-reference progress while loading", () => {
    render(<Phase1Coverage {...emptyHandlers} fillingRefs />);
    expect(screen.getByTestId("phase1-filling-refs")).toHaveTextContent(
      "กำลังดึงกฎระเบียบที่เกี่ยวข้อง"
    );
  });

  it("shows a ready banner when coverage is complete", () => {
    render(
      <Phase1Coverage
        {...emptyHandlers}
        coverage={[
          {
            key: "s1",
            label: "ชื่อโครงการ",
            status: "filled",
            filled: true,
            fact_required: true,
            preview: "โครงการจัดซื้อระบบบริหารสัญญา",
          },
        ]}
        fillingRefs={false}
        ready
      />
    );
    expect(screen.getByTestId("phase1-ready-banner")).toHaveTextContent(
      "ข้อมูลครบถ้วนแล้ว"
    );
    expect(screen.getByTestId("coverage-row-s1")).toHaveAttribute("data-status", "filled");
    expect(screen.getByTestId("phase1-fact-summary")).toHaveTextContent("โครงการจัดซื้อระบบบริหารสัญญา");
  });

  it("asks to complete fact slots when they are still empty", () => {
    render(
      <Phase1Coverage
        {...emptyHandlers}
        coverage={[
          {
            key: "s1",
            label: "ชื่อโครงการ",
            status: "gap",
            filled: false,
            fact_required: true,
          },
        ]}
        fillingRefs={false}
        message="ดูผลใน Phase 1"
        isError={false}
      />
    );
    expect(screen.getByText(/ช่องข้อเท็จจริงบังคับครบ/)).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("intake-enter-qa"));
    expect(emptyHandlers.onEnterQa).toHaveBeenCalled();
  });
});
