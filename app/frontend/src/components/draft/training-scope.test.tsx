import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { TrainingScopeEditor } from "@/components/draft/training-scope";
import { apiClient } from "@/lib/api-client";
import { categoryHasTraining } from "@/lib/training-scope";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    put: vi.fn(),
  },
}));

describe("TrainingScopeEditor", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        ok: true,
        data: {
          enabled: true,
          fields: { cohorts: "2", hours: "12", attendees: "30", documents: "คู่มือผู้ใช้" },
          prose: "การฝึกอบรม",
        },
      },
    } as never);
    vi.mocked(apiClient.put).mockResolvedValue({
      data: {
        ok: true,
        data: {
          fields: { cohorts: "3", hours: "12", attendees: "30", documents: "คู่มือผู้ใช้" },
          prose: "3 รุ่น",
        },
      },
    } as never);
  });

  it("is available on hire_develop and buy_goods profiles only", () => {
    expect(categoryHasTraining("hire_develop")).toBe(true);
    expect(categoryHasTraining("buy_goods")).toBe(true);
    expect(categoryHasTraining("construction")).toBe(false);
  });

  it("edits cohorts hours attendees and deliverable documents", async () => {
    const onDraftChange = vi.fn();
    render(<TrainingScopeEditor projectId="p1" onDraftChange={onDraftChange} />);
    expect(await screen.findByTestId("training-scope")).toBeInTheDocument();
    expect(screen.getByTestId("training-scope-cohorts")).toHaveValue("2");
    expect(screen.getByTestId("training-scope-hours")).toHaveValue("12");
    expect(screen.getByTestId("training-scope-attendees")).toHaveValue("30");
    expect(screen.getByTestId("training-scope-documents")).toHaveValue("คู่มือผู้ใช้");
    fireEvent.change(screen.getByTestId("training-scope-cohorts"), { target: { value: "3" } });
    fireEvent.blur(screen.getByTestId("training-scope-cohorts"));
    await waitFor(() => expect(apiClient.put).toHaveBeenCalled());
    expect(vi.mocked(apiClient.put).mock.calls[0][1]).toMatchObject({ cohorts: "3" });
    expect(screen.getByTestId("training-scope-preview")).toHaveTextContent("รุ่น");
  });
});
