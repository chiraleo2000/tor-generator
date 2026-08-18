import { describe, it, expect } from "vitest";
import { unwrapData, snakeToCamelProject, asString } from "./api-unwrap";
import type { AxiosResponse } from "axios";

function asResponse(data: unknown): AxiosResponse<unknown> {
  return { data } as AxiosResponse<unknown>;
}

describe("unwrapData", () => {
  it("reads FastAPI SuccessResponse.data", () => {
    expect(unwrapData(asResponse({ ok: true, data: { id: "p1" } }))).toEqual({
      id: "p1",
    });
  });

  it("returns the body when there is no envelope", () => {
    expect(unwrapData(asResponse({ id: "raw" }))).toEqual({ id: "raw" });
  });
});

describe("snakeToCamelProject", () => {
  it("maps API snake_case fields used by the dashboard cards", () => {
    const project = snakeToCamelProject({
      id: "abc",
      owner_id: "u1",
      name: "โครงการทดสอบ",
      ministry: "กระทรวงดิจิทัลฯ",
      budget: 1000000,
      project_type: "it",
      status: "draft",
      current_step: 3,
      quality_score: 80,
      template_id: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-02T00:00:00Z",
    });
    expect(project.ownerId).toBe("u1");
    expect(project.projectType).toBe("it");
    expect(project.currentStep).toBe(3);
    expect(project.currentPhase).toBe(0);
    expect(project.qualityScore).toBe(80);
    expect(project.templateId).toBeNull();
  });

  it("does not stringify non-string objects into [object Object]", () => {
    const project = snakeToCamelProject({
      id: { nested: true },
      name: { bad: true },
      quality_score: "",
      created_at: { iso: "nope" },
    });
    expect(project.id).toBe("");
    expect(project.name).toBe("");
    expect(project.createdAt).toBe("");
    expect(project.qualityScore).toBeNull();
  });
});

describe("asString", () => {
  it("keeps strings and stringifies primitives", () => {
    expect(asString("hello")).toBe("hello");
    expect(asString(12)).toBe("12");
    expect(asString(true)).toBe("true");
  });

  it("does not stringify objects into [object Object]", () => {
    expect(asString({ nested: true })).toBe("");
    expect(asString(["x"])).toBe("");
    expect(asString(null)).toBe("");
    expect(asString(undefined)).toBe("");
  });
});
