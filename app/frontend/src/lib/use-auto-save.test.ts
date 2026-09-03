import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import {
  clearAllBackups,
  clearBackup,
  getBackupKey,
  getProjectBackupKeys,
  restoreBackup,
  useAutoSave,
} from "./use-auto-save";
import { useWizardStore } from "@/stores/wizard-store";
import { apiClient } from "@/lib/api-client";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    put: vi.fn(),
  },
}));

describe("use-auto-save helpers", () => {
  afterEach(() => {
    localStorage.clear();
  });

  it("builds backup keys and restores valid objects", () => {
    const key = getBackupKey("p1", 2);
    expect(key).toBe("tor_wizard_backup_p1_2");
    localStorage.setItem(key, JSON.stringify({ description: "กู้คืน" }));
    localStorage.setItem("other", "x");
    expect(getProjectBackupKeys("p1")).toContain(key);
    expect(restoreBackup("p1", 2)).toEqual({ description: "กู้คืน" });
    expect(restoreBackup("p1", 3)).toBeNull();
    localStorage.setItem(getBackupKey("p1", 3), "not-json");
    expect(restoreBackup("p1", 3)).toBeNull();
    clearBackup("p1", 2);
    expect(restoreBackup("p1", 2)).toBeNull();
    localStorage.setItem(getBackupKey("p1", 4), JSON.stringify({ a: 1 }));
    clearAllBackups("p1");
    expect(getProjectBackupKeys("p1")).toEqual([]);
  });
});

describe("useAutoSave", () => {
  afterEach(() => {
    vi.useRealTimers();
    localStorage.clear();
    useWizardStore.getState().reset();
    vi.clearAllMocks();
  });

  it("debounces API save and retries the current step", async () => {
    vi.useFakeTimers();
    vi.mocked(apiClient.put).mockResolvedValue({ data: { ok: true } });
    useWizardStore.setState({ projectId: "p1", currentStep: 2, formData: { 2: { description: "ร่าง" } } });

    const { result } = renderHook(() => useAutoSave());
    act(() => {
      result.current.triggerAutoSave(2, { description: "ร่าง" });
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(apiClient.put).toHaveBeenCalled();

    await act(async () => {
      result.current.retrySave();
    });
    expect(apiClient.put).toHaveBeenCalledTimes(2);
  });

  it("writes a local backup when the API save fails", async () => {
    vi.useFakeTimers();
    vi.mocked(apiClient.put).mockRejectedValue(new Error("offline"));
    useWizardStore.setState({ projectId: "p1", currentStep: 2, formData: {} });

    const { result } = renderHook(() => useAutoSave());
    act(() => {
      result.current.triggerAutoSave(2, { description: "ค้างไว้" });
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(restoreBackup("p1", 2)).toEqual({ description: "ค้างไว้" });
    expect(useWizardStore.getState().autoSaveError).toContain("บันทึกไม่สำเร็จ");
  });

  it("restores a backup on mount and skips save without a project", async () => {
    vi.mocked(apiClient.put).mockResolvedValue({ data: { ok: true } });
    localStorage.setItem(
      getBackupKey("p-restore", 2),
      JSON.stringify({ description: "จากเครื่อง" })
    );
    useWizardStore.setState({
      projectId: "p-restore",
      currentStep: 2,
      formData: {},
    });
    const { result } = renderHook(() => useAutoSave());
    await act(async () => {
      await Promise.resolve();
    });
    expect(useWizardStore.getState().formData[2]).toEqual({ description: "จากเครื่อง" });
    useWizardStore.setState({ projectId: null });
    act(() => {
      result.current.triggerAutoSave(2, { description: "noop" });
      result.current.retrySave();
    });
  });
});
