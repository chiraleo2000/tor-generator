import { beforeAll, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { ConfirmPhaseDialog } from "@/components/draft/confirm-phase-dialog";

beforeAll(() => {
  if (typeof HTMLDialogElement === "undefined") {
    return;
  }
  HTMLDialogElement.prototype.showModal = function showModal() {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function close() {
    this.removeAttribute("open");
  };
});

describe("ConfirmPhaseDialog", () => {
  it("confirms and cancels without extra side effects", () => {
    const onConfirm = vi.fn();
    const onOpenChange = vi.fn();
    render(
      <ConfirmPhaseDialog
        open
        title="ยืนยันเริ่มวิเคราะห์เอกสาร?"
        onOpenChange={onOpenChange}
        onConfirm={onConfirm}
      />
    );
    expect(screen.getByTestId("confirm-phase-dialog")).toHaveTextContent(
      "ยืนยันเริ่มวิเคราะห์เอกสาร?"
    );
    fireEvent.click(screen.getByTestId("confirm-phase-ok"));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByTestId("confirm-phase-cancel"));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
