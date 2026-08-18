import { describe, expect, it } from "vitest";
import { cn } from "./utils";

describe("cn", () => {
  it("merges class names and later tailwind utilities win", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
    expect(cn("text-navy", false && "hidden", "font-bold")).toBe("text-navy font-bold");
  });
});
