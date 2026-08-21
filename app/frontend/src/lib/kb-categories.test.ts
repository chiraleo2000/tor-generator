import { describe, expect, it } from "vitest";
import { kbProcessingBadgeClass, uniqueById } from "@/lib/kb-categories";

describe("uniqueById", () => {
  it("keeps a single row when the same id appears twice", () => {
    const rows = [
      { id: "b", name: "ของฉัน.pdf" },
      { id: "a", name: "พรบ.pdf" },
      { id: "b", name: "ของฉัน.pdf" },
    ];
    expect(uniqueById(rows)).toEqual([
      { id: "b", name: "ของฉัน.pdf" },
      { id: "a", name: "พรบ.pdf" },
    ]);
  });
});

describe("kbProcessingBadgeClass", () => {
  it("uses a destructive tone for failed status", () => {
    expect(kbProcessingBadgeClass("failed")).toContain("text-red-800");
    expect(kbProcessingBadgeClass("completed")).toContain("text-green-800");
    expect(kbProcessingBadgeClass("processing")).toContain("text-amber-800");
    expect(kbProcessingBadgeClass("pending")).toContain("text-gray-700");
  });
});
