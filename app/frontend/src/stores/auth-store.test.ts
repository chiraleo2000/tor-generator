import { beforeEach, describe, expect, it, vi } from "vitest";
import axios from "axios";
import { apiClient } from "@/lib/api-client";
import { useAuthStore } from "./auth-store";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("auth-store", () => {
  beforeEach(() => {
    useAuthStore.setState({
      token: null,
      user: null,
      isAuthenticated: false,
      isLoading: true,
    });
    vi.restoreAllMocks();
  });

  it("login stores token and user from the envelope", async () => {
    vi.spyOn(axios, "post").mockResolvedValue({
      data: {
        ok: true,
        data: {
          token: "jwt-token",
          user: {
            id: "u1",
            name: "สมชาย",
            email: "officer@example.go.th",
            organization: "กระทรวง",
            role: "officer",
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
        },
      },
    });

    await useAuthStore.getState().login("officer@example.go.th", "Passw0rd!");
    const state = useAuthStore.getState();
    expect(state.token).toBe("jwt-token");
    expect(state.isAuthenticated).toBe(true);
    expect(state.user?.email).toBe("officer@example.go.th");
    expect(state.user?.name).toBe("สมชาย");
  });

  it("restoreSession hydrates the user from /auth/me", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        ok: true,
        data: {
          id: "u1",
          name: "ผู้ดูแล",
          email: "admin@example.go.th",
          organization: "กระทรวง",
          role: "admin",
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
      },
    });

    useAuthStore.getState().restoreSession();
    await vi.waitFor(() => {
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
    });
    expect(useAuthStore.getState().user?.role).toBe("admin");
  });

  it("restoreSession clears state when /auth/me fails", async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error("unauthorized"));
    useAuthStore.setState({ token: "stale", isAuthenticated: true });
    useAuthStore.getState().restoreSession();
    await vi.waitFor(() => {
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
    });
    expect(useAuthStore.getState().token).toBeNull();
  });

  it("clearSession drops credentials", () => {
    useAuthStore.setState({
      token: "jwt",
      user: {
        id: "u1",
        name: "x",
        email: "x@example.go.th",
        organization: "o",
        role: "officer",
        createdAt: "",
        updatedAt: "",
      },
      isAuthenticated: true,
      isLoading: false,
    });
    useAuthStore.getState().clearSession();
    expect(useAuthStore.getState().token).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it("login failure clears loading", async () => {
    vi.spyOn(axios, "post").mockRejectedValue(new Error("bad-credentials"));
    await expect(useAuthStore.getState().login("a@example.go.th", "x")).rejects.toThrow(
      "bad-credentials"
    );
    expect(useAuthStore.getState().isLoading).toBe(false);
  });

  it("logout posts then clears credentials", () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error("offline"));
    const assign = vi.fn();
    vi.stubGlobal("window", {
      ...window,
      location: { ...window.location, assign },
    });
    useAuthStore.setState({
      token: "jwt",
      isAuthenticated: true,
      isLoading: false,
      user: null,
    });
    useAuthStore.getState().logout();
    expect(useAuthStore.getState().token).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(assign).toHaveBeenCalledWith("/login");
  });
});
