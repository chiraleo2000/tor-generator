import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { Phase4Export } from "@/components/draft/phase4-export";

describe("Phase4Export", () => {
  it("exports Word and PDF", async () => {
    const onExport = vi.fn().mockResolvedValue(undefined);
    render(
      <Phase4Export exporting={false} error={null} info={null} onExport={onExport} />
    );
    fireEvent.click(screen.getByTestId("export-docx"));
    fireEvent.click(screen.getByTestId("export-pdf"));
    expect(onExport).toHaveBeenCalledWith("docx");
    expect(onExport).toHaveBeenCalledWith("pdf");
  });

  it("shows progress, success, and error states", () => {
    const { rerender } = render(
      <Phase4Export
        exporting
        error={null}
        info="กำลังสร้างเอกสาร Word"
        onExport={vi.fn().mockResolvedValue(undefined)}
      />
    );
    expect(screen.getByText("กำลังสร้างเอกสาร Word")).toBeInTheDocument();
    expect(screen.getByTestId("export-docx")).toBeDisabled();
    rerender(
      <Phase4Export
        exporting={false}
        error="ส่งออกไม่สำเร็จ"
        info={null}
        onExport={vi.fn().mockResolvedValue(undefined)}
      />
    );
    expect(screen.getByRole("alert")).toHaveTextContent("ส่งออกไม่สำเร็จ");
    rerender(
      <Phase4Export
        exporting={false}
        error={null}
        info="สร้างไฟล์แล้ว"
        onExport={vi.fn().mockResolvedValue(undefined)}
      />
    );
    expect(screen.getByText("สร้างไฟล์แล้ว")).toBeInTheDocument();
  });
});
