import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
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
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
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
        ready
      />
    );
    expect(screen.getByTestId("phase1-ready-banner")).toHaveTextContent("ข้อมูลข้อเท็จจริงครบแล้ว");
    expect(screen.getByTestId("coverage-row-s1")).toHaveAttribute("data-status", "filled");
    expect(screen.getByTestId("phase1-fact-summary")).toHaveTextContent(
      "โครงการจัดซื้อระบบบริหารสัญญา"
    );
  });

  it("does not treat a partial fact set as ready", () => {
    render(
      <Phase1Coverage
        {...emptyHandlers}
        coverage={[
          {
            key: "s1",
            label: "ความเป็นมา",
            status: "filled",
            filled: true,
            fact_required: true,
          },
          {
            key: "s2",
            label: "วัตถุประสงค์",
            status: "gap",
            filled: false,
            fact_required: true,
          },
        ]}
      />
    );
    expect(screen.getByText(/ช่องข้อเท็จจริงบังคับที่ยังไม่ครบ/)).toBeInTheDocument();
  });

  it("lets the officer continue to Phase 2 to fill gaps", () => {
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
        message="ดูผลใน Phase 1"
        isError={false}
      />
    );
    fireEvent.click(screen.getByTestId("phase1-skip"));
    expect(emptyHandlers.onEnterQa).toHaveBeenCalled();
  });

  it("does not auto-enter Phase 2; officer must click continue", () => {
    const onEnterQa = vi.fn();
    render(
      <Phase1Coverage
        {...emptyHandlers}
        onEnterQa={onEnterQa}
        coverage={[
          {
            key: "s1",
            label: "ชื่อโครงการ",
            status: "filled",
            filled: true,
            fact_required: true,
          },
        ]}
      />
    );
    expect(screen.queryByTestId("phase1-countdown")).not.toBeInTheDocument();
    expect(onEnterQa).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId("phase1-skip"));
    expect(onEnterQa).toHaveBeenCalled();
  });

  it("does not auto-enter Phase 2 while required topics are still gaps", () => {
    const onEnterQa = vi.fn();
    render(
      <Phase1Coverage
        {...emptyHandlers}
        onEnterQa={onEnterQa}
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
    expect(onEnterQa).not.toHaveBeenCalled();
  });
});
