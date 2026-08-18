import { describe, expect, it } from "vitest";
import type { InternalAxiosRequestConfig } from "axios";
import { applyRequestAuth, shouldRedirectToLogin } from "./api-client";

function config(overrides: Partial<InternalAxiosRequestConfig> = {}): InternalAxiosRequestConfig {
  return {
    headers: { "Content-Type": "application/json" },
    ...overrides,
  } as InternalAxiosRequestConfig;
}

describe("api-client interceptors", () => {
  it("adds a Bearer header when a token is present", () => {
    const next = applyRequestAuth(config(), "tok-123");
    expect(next.headers.Authorization).toBe("Bearer tok-123");
  });

  it("does not add Authorization when the token is missing", () => {
    const next = applyRequestAuth(config(), null);
    expect(next.headers.Authorization).toBeUndefined();
  });

  it("drops Content-Type for FormData bodies", () => {
    const next = applyRequestAuth(config({ data: new FormData() }), "tok-123");
    expect(next.headers["Content-Type"]).toBeUndefined();
    expect(next.headers.Authorization).toBe("Bearer tok-123");
  });

  it("redirects 401 away from login and register", () => {
    expect(shouldRedirectToLogin(401, "/projects")).toBe(true);
    expect(shouldRedirectToLogin(401, "/login")).toBe(false);
    expect(shouldRedirectToLogin(401, "/register")).toBe(false);
    expect(shouldRedirectToLogin(403, "/projects")).toBe(false);
  });
});
