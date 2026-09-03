import { describe, expect, it, vi } from "vitest";
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

  it("response interceptor clears session and assigns login on 401", async () => {
    const { apiClient } = await import("./api-client");
    const { useAuthStore } = await import("@/stores/auth-store");
    useAuthStore.setState({
      token: "jwt",
      isAuthenticated: true,
      user: null,
      isLoading: false,
    });
    const assign = vi.fn();
    vi.stubGlobal("window", {
      ...window,
      location: { ...window.location, pathname: "/projects", assign },
    });
    const rejected = apiClient.interceptors.response.handlers[0]?.rejected;
    expect(rejected).toBeTypeOf("function");
    await expect(
      rejected?.({ response: { status: 401 } } as never)
    ).rejects.toBeTruthy();
    expect(useAuthStore.getState().token).toBeNull();
    expect(assign).toHaveBeenCalledWith("/login");
  });

  it("does not redirect when a 401 happens on the login page", async () => {
    const { apiClient } = await import("./api-client");
    const { useAuthStore } = await import("@/stores/auth-store");
    useAuthStore.setState({
      token: "jwt",
      isAuthenticated: true,
      user: null,
      isLoading: false,
    });
    const assign = vi.fn();
    vi.stubGlobal("window", {
      ...window,
      location: { ...window.location, pathname: "/login", assign },
    });
    const rejected = apiClient.interceptors.response.handlers[0]?.rejected;
    await expect(
      rejected?.({ response: { status: 401 } } as never)
    ).rejects.toBeTruthy();
    expect(assign).not.toHaveBeenCalled();
    expect(useAuthStore.getState().token).toBe("jwt");
  });

  it("rejects request interceptor errors and returns successful responses", async () => {
    const { apiClient } = await import("./api-client");
    const reqRejected = apiClient.interceptors.request.handlers[0]?.rejected;
    await expect(reqRejected?.(new Error("offline"))).rejects.toThrow("offline");
    const resFulfilled = apiClient.interceptors.response.handlers[0]?.fulfilled;
    const payload = { data: { ok: true } };
    expect(resFulfilled?.(payload as never)).toEqual(payload);
  });
});
