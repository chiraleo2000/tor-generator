import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { CostWorksheetEditor } from "@/components/draft/cost-worksheet";
import { TrainingScopeEditor } from "@/components/draft/training-scope";
import { apiClient } from "@/lib/api-client";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    put: vi.fn(),
  },
}));

describe("coverage edges for draft cost and training editors", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("keeps a local cost sheet when there is no project and when save fails", async () => {
    const onChange = vi.fn();
    const local = render(<CostWorksheetEditor onChange={onChange} />);
    fireEvent.change(screen.getByTestId("cost-worksheet-team-size"), {
      target: { value: "3" },
    });
    fireEvent.change(screen.getByTestId("cost-worksheet-months"), {
      target: { value: "6" },
    });
    fireEvent.change(screen.getByTestId("cost-worksheet-years"), {
      target: { value: "" },
    });
    fireEvent.change(screen.getByTestId("cost-worksheet-training-days"), {
      target: { value: "2" },
    });
    fireEvent.change(screen.getByTestId("cost-worksheet-day-part"), {
      target: { value: "half_morning" },
    });
    fireEvent.change(screen.getByTestId("cost-worksheet-attendees"), {
      target: { value: "10" },
    });
    fireEvent.click(screen.getByTestId("cost-worksheet-save"));
    expect(await screen.findByTestId("cost-worksheet-info")).toHaveTextContent(
      "เก็บในร่างหมวดวงเงินแล้ว"
    );
    local.unmount();

    vi.mocked(apiClient.get).mockRejectedValue(new Error("โหลดไม่ได้"));
    vi.mocked(apiClient.put).mockRejectedValue(new Error("บันทึกไม่ได้"));
    render(<CostWorksheetEditor projectId="p1" />);
    await waitFor(() => expect(apiClient.get).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId("cost-worksheet-apply"));
    expect(await screen.findByTestId("cost-worksheet-info")).toHaveTextContent(
      "ใช้ตัวเลขที่คำนวณไม่สำเร็จ"
    );
  });

  it("falls back to a local training save when the server rejects the scope", async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error("ไม่มีขอบเขต"));
    vi.mocked(apiClient.put).mockRejectedValue(new Error("บันทึกไม่ได้"));
    const onSave = vi.fn();
    render(<TrainingScopeEditor projectId="p1" hint="อบรม" onSave={onSave} />);
    await waitFor(() => expect(apiClient.get).toHaveBeenCalled());
    fireEvent.change(screen.getByTestId("training-scope-documents"), {
      target: { value: "คู่มือผู้ใช้" },
    });
    fireEvent.blur(screen.getByTestId("training-scope-documents"));
    await waitFor(() => expect(onSave).toHaveBeenCalled());
  });
});
