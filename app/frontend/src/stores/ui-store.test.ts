import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useUIStore } from "./ui-store";

describe("ui-store", () => {
  beforeEach(() => {
    useUIStore.setState({
      theme: "light",
      sidebarOpen: true,
      isLoading: false,
      toasts: [],
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("toggles theme, sidebar, and loading", () => {
    useUIStore.getState().toggleTheme();
    expect(useUIStore.getState().theme).toBe("dark");
    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarOpen).toBe(false);
    useUIStore.getState().setSidebarOpen(true);
    expect(useUIStore.getState().sidebarOpen).toBe(true);
    useUIStore.getState().setLoading(true);
    expect(useUIStore.getState().isLoading).toBe(true);
  });

  it("adds and removes toasts, including auto-dismiss", () => {
    vi.useFakeTimers();
    useUIStore.getState().addToast({ type: "info", title: "บันทึกแล้ว", duration: 1000 });
    expect(useUIStore.getState().toasts).toHaveLength(1);
    const id = useUIStore.getState().toasts[0].id;
    useUIStore.getState().removeToast(id);
    expect(useUIStore.getState().toasts).toHaveLength(0);

    useUIStore.getState().addToast({ type: "error", title: "ผิดพลาด", duration: 0 });
    expect(useUIStore.getState().toasts).toHaveLength(1);
    useUIStore.getState().addToast({ type: "info", title: "หมดเวลา", duration: 50 });
    expect(useUIStore.getState().toasts).toHaveLength(2);
    vi.advanceTimersByTime(60);
    expect(useUIStore.getState().toasts).toHaveLength(1);
  });
});
