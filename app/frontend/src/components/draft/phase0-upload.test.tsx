import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { Phase0Upload } from "@/components/draft/phase0-upload";

describe("Phase0Upload", () => {
  it("disables analyze when there is no material", () => {
    const onAnalyze = vi.fn();
    render(
      <Phase0Upload
        draftText=""
        busy={false}
        canStart={false}
        uploadedNames={[]}
        message={null}
        isError={false}
        status="idle"
        onDraftText={vi.fn()}
        onBlurSave={vi.fn()}
        onUpload={vi.fn()}
        onAnalyze={onAnalyze}
      />
    );
    expect(screen.getByTestId("intake-start-analyze")).toBeDisabled();
    fireEvent.click(screen.getByTestId("intake-start-analyze"));
    expect(onAnalyze).not.toHaveBeenCalled();
  });

  it("lists uploaded files and starts analyze when allowed", () => {
    const onAnalyze = vi.fn();
    const onDraftText = vi.fn();
    const onBlurSave = vi.fn();
    const onUpload = vi.fn();
    render(
      <Phase0Upload
        draftText="โครงการจัดซื้อครุภัณฑ์คอมพิวเตอร์"
        busy={false}
        canStart
        uploadedNames={["pB0.pdf"]}
        message="อัปโหลดแล้ว — กดเริ่มวิเคราะห์เมื่อครบชุดเอกสาร"
        isError={false}
        status="idle"
        onDraftText={onDraftText}
        onBlurSave={onBlurSave}
        onUpload={onUpload}
        onAnalyze={onAnalyze}
      />
    );
    expect(screen.getByTestId("phase0-file-list")).toHaveTextContent("pB0.pdf");
    fireEvent.change(screen.getByTestId("intake-paste"), {
      target: { value: "ข้อความใหม่" },
    });
    expect(onDraftText).toHaveBeenCalledWith("ข้อความใหม่");
    fireEvent.blur(screen.getByTestId("intake-paste"));
    expect(onBlurSave).toHaveBeenCalled();
    fireEvent.click(screen.getByTestId("intake-start-analyze"));
    expect(onAnalyze).toHaveBeenCalledTimes(1);
  });

  it("replaces the form with analyzing progress", () => {
    render(
      <Phase0Upload
        draftText="โครงการทดสอบวางข้อความอย่างน้อยยี่สิบตัวอักษร"
        busy
        canStart
        uploadedNames={["pB0.pdf"]}
        message={null}
        isError={false}
        status="analyzing"
        onDraftText={vi.fn()}
        onBlurSave={vi.fn()}
        onUpload={vi.fn()}
        onAnalyze={vi.fn()}
      />
    );
    expect(screen.getByTestId("phase0-analyzing")).toHaveTextContent("อย่าปิดหน้านี้");
    expect(screen.getByTestId("phase0-file-list")).toHaveTextContent("pB0.pdf");
    expect(screen.queryByTestId("intake-paste")).not.toBeInTheDocument();
    expect(screen.queryByTestId("intake-start-analyze")).not.toBeInTheDocument();
  });

  it("shows an error alert and busy upload label with the file name", () => {
    render(
      <Phase0Upload
        draftText=""
        busy
        canStart={false}
        uploadedNames={["pB0.pdf"]}
        message="อัปโหลดไม่สำเร็จ"
        isError
        status="uploading"
        onDraftText={vi.fn()}
        onBlurSave={vi.fn()}
        onUpload={vi.fn()}
        onAnalyze={vi.fn()}
      />
    );
    expect(screen.getByTestId("phase0-uploading")).toHaveTextContent("กำลังอัปโหลด...");
    expect(screen.getByTestId("phase0-file-list")).toHaveTextContent("pB0.pdf");
    expect(screen.getByRole("alert")).toHaveTextContent("อัปโหลดไม่สำเร็จ");
  });
});
