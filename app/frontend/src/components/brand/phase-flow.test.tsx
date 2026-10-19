import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PhaseFlow } from "@/components/brand/phase-flow";

describe("PhaseFlow", () => {
  it("keeps later steps open and colored by progress while viewing an earlier step", () => {
    const onSelect = vi.fn();
    render(<PhaseFlow current={1} unlocked={4} reached={4} onSelect={onSelect} />);
    expect(screen.getByTestId("phase-1")).toHaveAttribute("data-status", "done");
    expect(screen.getByTestId("phase-1")).toHaveAttribute("data-viewing", "true");
    expect(screen.getByTestId("phase-4")).toHaveAttribute("data-status", "current");
    expect(screen.getByTestId("phase-3")).toHaveAttribute("aria-disabled", "false");
    fireEvent.click(screen.getByTestId("phase-4"));
    expect(onSelect).toHaveBeenCalledWith(4);
  });

  it("does not select phase 2 when intake is still locked", () => {
    const onSelect = vi.fn();
    render(<PhaseFlow current={0} unlocked={0} onSelect={onSelect} />);
    fireEvent.click(screen.getByTestId("phase-2"));
    expect(onSelect).not.toHaveBeenCalled();
    expect(screen.getByTestId("phase-2")).toHaveAttribute("aria-disabled", "true");
  });
});
