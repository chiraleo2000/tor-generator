import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { CostWorksheetEditor } from "@/components/draft/cost-worksheet";
import { apiClient } from "@/lib/api-client";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    put: vi.fn(),
  },
}));

const loaded = {
  personnel: 1000,
  equipment: 2000,
  procurement: 300,
  consultant: 700,
  training: 0,
  food: 0,
  snack: 0,
  documents: 0,
  venue: 0,
  total: 4000,
  is_announced_price: false,
  label: "ใบประมาณการ — ไม่ใช่ราคากลาง",
};

describe("CostWorksheetEditor", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { ok: true, data: loaded },
    } as never);
    vi.mocked(apiClient.put).mockResolvedValue({
      data: {
        ok: true,
        data: { ...loaded, personnel: 1500, total: 4500, is_announced_price: false },
      },
    } as never);
  });

  it("loads five officer-editable categories and never labels them as ราคากลาง", async () => {
    render(<CostWorksheetEditor projectId="p1" />);
    expect(await screen.findByTestId("cost-worksheet")).toBeInTheDocument();
    expect(screen.getByTestId("cost-worksheet-disclaimer")).toHaveTextContent("ไม่ใช่ราคากลาง");
    expect(screen.getByTestId("cost-worksheet-rules")).toHaveTextContent("ปริญญาโทแล้วปริญญาเอก");
    expect(screen.getByTestId("cost-worksheet-rules")).toHaveTextContent("ภาคเอกชน");
    expect(screen.getByTestId("cost-worksheet-rules")).toHaveTextContent("โรงแรมหรือสถานที่เอกชน");
    expect(screen.getByTestId("cost-worksheet-rules")).toHaveTextContent("2 ปี");
    expect(screen.getByTestId("cost-worksheet-rules")).toHaveTextContent("อาหาร 1 มื้อและอาหารว่าง 1 มื้อ");
    expect(screen.getByTestId("cost-worksheet-rules")).toHaveTextContent("อาหาร 2 มื้อและอาหารว่าง 2 มื้อ");
    expect(screen.getByTestId("cost-worksheet-rules")).toHaveTextContent("เอกสารคิดทุกครั้ง");
    expect(screen.getByTestId("cost-worksheet-personnel")).toHaveValue("1,000");
    expect(screen.getByTestId("cost-worksheet-equipment")).toHaveValue("2,000");
    expect(screen.getByTestId("cost-worksheet-procurement")).toHaveValue("300");
    expect(screen.getByTestId("cost-worksheet-consultant")).toHaveValue("700");
    expect(screen.getByTestId("cost-worksheet-training")).toHaveValue("");
    expect(screen.getByTestId("cost-worksheet-food")).toBeInTheDocument();
    expect(screen.getByTestId("cost-worksheet-total")).toHaveTextContent("ไม่ใช่ราคากลาง");
  });

  it("updates the training total locally when a part changes", async () => {
    render(<CostWorksheetEditor projectId="p1" />);
    const food = await screen.findByTestId("cost-worksheet-food");
    fireEvent.change(food, { target: { value: "100" } });
    expect(screen.getByTestId("cost-worksheet-training")).toHaveValue("100");
    expect(screen.getByTestId("cost-worksheet-total")).toHaveTextContent("4,100");
  });

  it("saves edited personnel without treating the total as official median price", async () => {
    render(<CostWorksheetEditor projectId="p1" />);
    const personnel = await screen.findByTestId("cost-worksheet-personnel");
    fireEvent.change(personnel, { target: { value: "1500" } });
    fireEvent.click(screen.getByTestId("cost-worksheet-save"));
    await waitFor(() => expect(apiClient.put).toHaveBeenCalled());
    expect(vi.mocked(apiClient.put).mock.calls[0][0]).toContain("/cost-worksheet");
    expect(vi.mocked(apiClient.put).mock.calls[0][1]).toMatchObject({
      personnel: 1500,
      equipment: 2000,
    });
    expect(await screen.findByTestId("cost-worksheet-info")).toHaveTextContent("ไม่ใช่ราคากลาง");
  });

  it("asks the server to apply calculated figures and clears the busy state", async () => {
    render(<CostWorksheetEditor projectId="p1" />);
    await screen.findByTestId("cost-worksheet-apply");
    fireEvent.click(screen.getByTestId("cost-worksheet-apply"));
    await waitFor(() => expect(apiClient.put).toHaveBeenCalled());
    expect(vi.mocked(apiClient.put).mock.calls[0][1]).toMatchObject({
      apply_calculated: true,
      team_size: 2,
      day_part: "full",
      years: null,
    });
    expect(await screen.findByTestId("cost-worksheet-info")).toHaveTextContent("ใช้ตัวเลขที่คำนวณแล้ว");
    expect(screen.getByTestId("cost-worksheet-apply")).not.toBeDisabled();
  });
});
