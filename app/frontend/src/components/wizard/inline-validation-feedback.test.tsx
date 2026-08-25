import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { InlineValidationFeedback } from "./inline-validation-feedback";
import { ValidationFinding } from "@/types";

describe("InlineValidationFeedback", () => {
  const sampleFindings: ValidationFinding[] = [
    {
      severity: "error",
      rule_violated: "LEGAL_001",
      affected_section: "s2",
      message: "ไม่พบการอ้างอิง พ.ร.บ. 2560",
      recommended_correction: "เพิ่มข้อความอ้างอิง พ.ร.บ. การจัดซื้อจัดจ้างฯ พ.ศ. 2560",
    },
    {
      severity: "warning",
      rule_violated: "COMPLETENESS_002",
      affected_section: "s4",
      message: "ขอบเขตงานไม่ครบถ้วน",
      recommended_correction: "เพิ่มรายละเอียดงวดงานทั้ง 14 หัวข้อ",
    },
    {
      severity: "suggestion",
      rule_violated: "FORMAT_003",
      affected_section: "s1",
      message: "ควรใช้รูปแบบเลขไทย",
      recommended_correction: "แปลงตัวเลขเป็น ๑, ๒, ๓",
    },
  ];

  it("renders nothing when there are no findings, not validating, and no result", () => {
    const { container } = render(
      <InlineValidationFeedback
        findings={[]}
        isValidating={false}
        qualityScore={null}
        isValid={null}
        error={null}
      />
    );

    expect(container.innerHTML).toBe("");
  });

  it("shows loading spinner when validating", () => {
    render(
      <InlineValidationFeedback
        findings={[]}
        isValidating={true}
        qualityScore={null}
        isValid={null}
        error={null}
      />
    );

    expect(screen.getByText("กำลังตรวจสอบ...")).toBeInTheDocument();
  });

  it("shows error message when validation fails", () => {
    render(
      <InlineValidationFeedback
        findings={[]}
        isValidating={false}
        qualityScore={null}
        isValid={null}
        error="ไม่สามารถตรวจสอบเนื้อหาได้ กรุณาลองใหม่"
      />
    );

    expect(screen.getByText("ไม่สามารถตรวจสอบเนื้อหาได้ กรุณาลองใหม่")).toBeInTheDocument();
  });

  it("shows quality score with green color when score >= 70", () => {
    render(
      <InlineValidationFeedback
        findings={[]}
        isValidating={false}
        qualityScore={85}
        isValid={true}
        error={null}
      />
    );

    expect(screen.getByText("85/100")).toBeInTheDocument();
    expect(screen.getByText("ผ่าน")).toBeInTheDocument();
  });

  it("shows quality score with amber color when score is 50-69", () => {
    render(
      <InlineValidationFeedback
        findings={[]}
        isValidating={false}
        qualityScore={60}
        isValid={true}
        error={null}
      />
    );
    expect(screen.getByText("60/100")).toBeInTheDocument();
  });

  it("shows quality score with red color when score < 50", () => {
    render(
      <InlineValidationFeedback
        findings={sampleFindings}
        isValidating={false}
        qualityScore={35}
        isValid={false}
        error={null}
      />
    );

    expect(screen.getByText("35/100")).toBeInTheDocument();
    expect(screen.getByText("ไม่ผ่าน")).toBeInTheDocument();
  });

  it("renders findings with correct severity icons", () => {
    render(
      <InlineValidationFeedback
        findings={sampleFindings}
        isValidating={false}
        qualityScore={45}
        isValid={false}
        error={null}
      />
    );

    // Check that findings are displayed
    expect(screen.getByText("ไม่พบการอ้างอิง พ.ร.บ. 2560")).toBeInTheDocument();
    expect(screen.getByText("ขอบเขตงานไม่ครบถ้วน")).toBeInTheDocument();
    expect(screen.getByText("ควรใช้รูปแบบเลขไทย")).toBeInTheDocument();

    // Check count display
    expect(screen.getByText("พบ 3 รายการ")).toBeInTheDocument();
  });

  it("shows recommended correction when expanded", () => {
    render(
      <InlineValidationFeedback
        findings={[sampleFindings[0]]}
        isValidating={false}
        qualityScore={50}
        isValid={false}
        error={null}
      />
    );

    // Initially, correction should not be visible
    expect(screen.queryByText("เพิ่มข้อความอ้างอิง พ.ร.บ. การจัดซื้อจัดจ้างฯ พ.ศ. 2560")).not.toBeInTheDocument();

    // Click to expand
    fireEvent.click(screen.getByText("ดูคำแนะนำการแก้ไข"));

    // Now the correction should be visible
    expect(screen.getByText("เพิ่มข้อความอ้างอิง พ.ร.บ. การจัดซื้อจัดจ้างฯ พ.ศ. 2560")).toBeInTheDocument();

    // Button text should change
    expect(screen.getByText("ซ่อนคำแนะนำการแก้ไข")).toBeInTheDocument();
  });

  it("shows all-clear message when valid with no findings", () => {
    render(
      <InlineValidationFeedback
        findings={[]}
        isValidating={false}
        qualityScore={90}
        isValid={true}
        error={null}
      />
    );

    expect(screen.getByText("เนื้อหาผ่านการตรวจสอบทั้งหมด")).toBeInTheDocument();
  });

  it("has proper accessibility attributes", () => {
    render(
      <InlineValidationFeedback
        findings={sampleFindings}
        isValidating={false}
        qualityScore={60}
        isValid={false}
        error={null}
      />
    );

    const region = screen.getByRole("region");
    expect(region).toHaveAttribute("aria-label", "ผลการตรวจสอบแบบเรียลไทม์");
    expect(region).toHaveAttribute("aria-live", "polite");
  });
});
