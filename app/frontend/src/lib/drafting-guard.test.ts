import { afterEach, describe, expect, it, vi } from "vitest";
import {
  clearDraftingProject,
  decideArchiveProject,
  isCurrentlyDrafting,
  markDraftingProject,
} from "./drafting-guard";

afterEach(() => {
  sessionStorage.clear();
});

describe("drafting-guard", () => {
  it("marks the open draft so dashboard cannot archive it", () => {
    markDraftingProject("p-live");
    expect(isCurrentlyDrafting("p-live")).toBe(true);
    expect(decideArchiveProject("p-live", "E2E", () => true)).toBe("blocked");
  });

  it("clears only the matching project id", () => {
    markDraftingProject("p-live");
    clearDraftingProject("other");
    expect(isCurrentlyDrafting("p-live")).toBe(true);
    clearDraftingProject("p-live");
    expect(isCurrentlyDrafting("p-live")).toBe(false);
  });

  it("asks for confirmation before archiving another project", () => {
    const confirmFn = vi.fn().mockReturnValue(false);
    expect(decideArchiveProject("p2", "อื่น", confirmFn)).toBe("cancelled");
    expect(confirmFn).toHaveBeenCalledWith("ลบโครงการ «อื่น» ?");
    confirmFn.mockReturnValue(true);
    expect(decideArchiveProject("p2", "อื่น", confirmFn)).toBe("proceed");
  });
});
