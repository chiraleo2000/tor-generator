import { describe, expect, it } from "vitest";
import { pageMeta } from "./page-meta";

describe("pageMeta", () => {
  it("labels knowledge base, draft, review, help, and admin routes", () => {
    expect(pageMeta("/knowledge-base").title).toBe("ฐานความรู้");
    expect(pageMeta("/projects/abc/draft").title).toBe("ร่าง TOR");
    expect(pageMeta("/review").title).toBe("ตรวจสอบ TOR");
    expect(pageMeta("/help").title).toBe("คู่มือการใช้งาน");
    expect(pageMeta("/admin/ai-settings").title).toBe("การตั้งค่า AI");
    expect(pageMeta("/admin/users").title).toBe("ผู้ใช้");
    expect(pageMeta("/admin/templates").title).toBe("แม่แบบ");
    expect(pageMeta("/projects").title).toBe("แดชบอร์ด");
  });
});
