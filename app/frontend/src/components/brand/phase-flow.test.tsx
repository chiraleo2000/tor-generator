import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PhaseFlow } from "@/components/brand/phase-flow";

describe("PhaseFlow", () => {
  it("does not select phase 2 when intake is still locked", () => {
    const onSelect = vi.fn();
    render(<PhaseFlow current={0} unlocked={0} onSelect={onSelect} />);
    fireEvent.click(screen.getByTestId("phase-2"));
    expect(onSelect).not.toHaveBeenCalled();
    expect(screen.getByTestId("phase-2")).toHaveAttribute("aria-disabled", "true");
  });
});
