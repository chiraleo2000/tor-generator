import { describe, expect, it } from "vitest";
import { navItemIsActive } from "./nav-active";

describe("navItemIsActive", () => {
  it("highlights dashboard only on the project list", () => {
    expect(navItemIsActive("/projects", "/projects")).toBe(true);
    expect(navItemIsActive("/projects/", "/projects")).toBe(true);
    expect(navItemIsActive("/projects/abc/draft", "/projects")).toBe(false);
    expect(navItemIsActive("/projects/abc/wizard/1", "/projects")).toBe(false);
    expect(navItemIsActive("/draft", "/projects")).toBe(false);
  });

  it("highlights ร่าง TOR on draft and wizard routes", () => {
    expect(navItemIsActive("/draft", "/draft")).toBe(true);
    expect(navItemIsActive("/projects/abc/draft", "/draft")).toBe(true);
    expect(navItemIsActive("/projects/abc/wizard/0", "/draft")).toBe(true);
    expect(navItemIsActive("/wizard/1", "/draft")).toBe(true);
    expect(navItemIsActive("/projects", "/draft")).toBe(false);
    expect(navItemIsActive("/review", "/draft")).toBe(false);
  });

  it("highlights other work items by prefix", () => {
    expect(navItemIsActive("/chat", "/chat")).toBe(true);
    expect(navItemIsActive("/chat/room", "/chat")).toBe(true);
    expect(navItemIsActive("/review", "/review")).toBe(true);
    expect(navItemIsActive("/help", "/help")).toBe(true);
    expect(navItemIsActive("/admin/users", "/admin/users")).toBe(true);
    expect(navItemIsActive("/admin/users", "/admin/templates")).toBe(false);
  });
});
