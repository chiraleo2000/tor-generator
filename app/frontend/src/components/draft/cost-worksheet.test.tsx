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

describe("CostWorksheetEditor", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        ok: true,
        data: {
          license: 1000,
          labor: 2000,
          maintenance: 300,
          training: 700,
          total: 4000,
          is_announced_price: false,
          label: "ใบประมาณการ — ไม่ใช่ราคากลาง",
        },
      },
    } as never);
    vi.mocked(apiClient.put).mockResolvedValue({
      data: {
        ok: true,
        data: {
          license: 1500,
          labor: 2000,
          maintenance: 300,
          training: 700,
          total: 4500,
          is_announced_price: false,
        },
      },
    } as never);
  });

  it("loads officer-editable lines and never labels them as ราคากลาง", async () => {
    render(<CostWorksheetEditor projectId="p1" />);
    expect(await screen.findByTestId("cost-worksheet")).toBeInTheDocument();
    expect(screen.getByTestId("cost-worksheet-disclaimer")).toHaveTextContent("ไม่ใช่ราคากลาง");
    expect(screen.getByTestId("cost-worksheet-disclaimer")).not.toHaveTextContent(/^ราคากลาง$/);
    expect(screen.getByTestId("cost-worksheet-license")).toHaveValue("1,000");
    expect(screen.getByTestId("cost-worksheet-labor")).toHaveValue("2,000");
    expect(screen.getByTestId("cost-worksheet-maintenance")).toHaveValue("300");
    expect(screen.getByTestId("cost-worksheet-training")).toHaveValue("700");
    expect(screen.getByTestId("cost-worksheet-total")).toHaveTextContent("ไม่ใช่ราคากลาง");
  });

  it("saves edited license without treating the total as official median price", async () => {
    render(<CostWorksheetEditor projectId="p1" />);
    const license = await screen.findByTestId("cost-worksheet-license");
    fireEvent.change(license, { target: { value: "1500" } });
    fireEvent.click(screen.getByTestId("cost-worksheet-save"));
    await waitFor(() => expect(apiClient.put).toHaveBeenCalled());
    expect(vi.mocked(apiClient.put).mock.calls[0][0]).toContain("/cost-worksheet");
    expect(vi.mocked(apiClient.put).mock.calls[0][1]).toMatchObject({
      license: 1500,
      labor: 2000,
    });
    expect(await screen.findByTestId("cost-worksheet-info")).toHaveTextContent("ไม่ใช่ราคากลาง");
  });
});
