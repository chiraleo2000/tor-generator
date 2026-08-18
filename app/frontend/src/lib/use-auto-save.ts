"use client";

import { useCallback, useEffect, useRef } from "react";
import { apiClient } from "@/lib/api-client";
import { useWizardStore } from "@/stores/wizard-store";
import { useUIStore } from "@/stores/ui-store";
import { toWizardApiPayload } from "@/lib/wizard-api";

const AUTO_SAVE_DELAY_MS = 3000;

/**
 * localStorage key pattern for wizard backup data.
 * Used when API save fails so data isn't lost.
 */
export function getBackupKey(projectId: string, step: number): string {
  return `tor_wizard_backup_${projectId}_${step}`;
}

/**
 * Get all backup keys for a given project from localStorage.
 */
export function getProjectBackupKeys(projectId: string): string[] {
  const keys: string[] = [];
  if (typeof window === "undefined") return keys;
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key?.startsWith(`tor_wizard_backup_${projectId}_`)) {
      keys.push(key);
    }
  }
  return keys;
}

/**
 * Restore backup data from localStorage for a specific project and step.
 * Returns null if no backup exists.
 */
export function restoreBackup(
  projectId: string,
  step: number
): Record<string, unknown> | null {
  if (typeof window === "undefined") return null;
  try {
    const key = getBackupKey(projectId, step);
    const data = localStorage.getItem(key);
    if (data) {
      const parsed: unknown = JSON.parse(data);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        return parsed as Record<string, unknown>;
      }
    }
  } catch {
    // Ignore parse errors
  }
  return null;
}

/**
 * Clear backup data from localStorage for a specific project and step.
 */
export function clearBackup(projectId: string, step: number): void {
  if (typeof window === "undefined") return;
  try {
    const key = getBackupKey(projectId, step);
    localStorage.removeItem(key);
  } catch {
    // Ignore errors
  }
}

/**
 * Clear all backup data for a given project.
 */
export function clearAllBackups(projectId: string): void {
  if (typeof window === "undefined") return;
  const keys = getProjectBackupKeys(projectId);
  keys.forEach((key) => {
    try {
      localStorage.removeItem(key);
    } catch {
      // Ignore
    }
  });
}

/**
 * Custom hook that implements auto-save with 3-second debounce.
 *
 * Behavior:
 * - After 3 seconds of no changes, persists step data to the API via PUT
 * - On API failure: saves to localStorage and shows a retry notification
 * - On reconnection/mount: restores from localStorage if backup exists
 * - Exposes isDirty and isAutoSaving states through the wizard store
 *
 * Requirements: 4.2, 4.6, 4.8
 */
export function useAutoSave() {
  const projectId = useWizardStore((s) => s.projectId);
  const currentStep = useWizardStore((s) => s.currentStep);
  const formData = useWizardStore((s) => s.formData);
  const isDirty = useWizardStore((s) => s.isDirty);
  const isAutoSaving = useWizardStore((s) => s.isAutoSaving);
  const autoSaveError = useWizardStore((s) => s.autoSaveError);
  const setAutoSaving = useWizardStore((s) => s.setAutoSaving);
  const setAutoSaveError = useWizardStore((s) => s.setAutoSaveError);
  const markSaved = useWizardStore((s) => s.markSaved);
  const setFormData = useWizardStore((s) => s.setFormData);
  const setAutoSaveListener = useWizardStore((s) => s.setAutoSaveListener);

  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);

  // Clean up on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  /**
   * Attempt to save step data to the API.
   * On success: clear localStorage backup, mark saved.
   * On failure: persist to localStorage, show error toast.
   */
  const syncToApi = useCallback(
    async (pId: string, step: number, data: unknown) => {
      if (!isMountedRef.current) return;

      setAutoSaving(true);
      setAutoSaveError(null);

      try {
        await apiClient.put(`/projects/${pId}/steps/${step}`, {
          data: toWizardApiPayload(step, data),
        });

        if (!isMountedRef.current) return;

        // Success: clear backup and mark as saved
        clearBackup(pId, step);
        markSaved();
      } catch {
        if (!isMountedRef.current) return;

        // Failure: persist to localStorage
        try {
          const key = getBackupKey(pId, step);
          localStorage.setItem(key, JSON.stringify(data));
        } catch {
          // localStorage may be full or unavailable
        }

        const errorMessage = "บันทึกไม่สำเร็จ กรุณาลองใหม่";
        setAutoSaveError(errorMessage);
        setAutoSaving(false);

        useUIStore.getState().addToast({
          type: "error",
          title: errorMessage,
          message: "ข้อมูลถูกบันทึกไว้ในเครื่อง จะพยายามซิงค์อีกครั้งเมื่อเชื่อมต่อได้",
          duration: 7000,
        });
      }
    },
    [setAutoSaving, setAutoSaveError, markSaved]
  );

  /**
   * Trigger debounced auto-save. Called by the wizard store on form data changes.
   */
  const triggerAutoSave = useCallback(
    (step: number, data: unknown) => {
      const pId = useWizardStore.getState().projectId;
      if (!pId) return;

      // Clear any existing timer
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }

      // Set new 3-second debounce timer
      debounceTimerRef.current = setTimeout(() => {
        syncToApi(pId, step, data);
      }, AUTO_SAVE_DELAY_MS);
    },
    [syncToApi]
  );

  // Register the auto-save listener on the wizard store
  useEffect(() => {
    setAutoSaveListener(triggerAutoSave);
    return () => {
      setAutoSaveListener(null);
    };
  }, [triggerAutoSave, setAutoSaveListener]);

  // Restore from localStorage on mount or project/step change
  useEffect(() => {
    if (!projectId) return;

    const backup = restoreBackup(projectId, currentStep);
    if (backup !== null) {
      // Restore data from localStorage backup without triggering auto-save loop
      setFormData(currentStep, backup, { skipAutoSave: true });
      // Show info notification that data was restored
      useUIStore.getState().addToast({
        type: "info",
        title: "กู้คืนข้อมูลสำเร็จ",
        message: "ข้อมูลที่บันทึกไว้ในเครื่องถูกกู้คืนแล้ว กำลังซิงค์กับเซิร์ฟเวอร์...",
        duration: 4000,
      });
      // Attempt to sync restored data to server
      syncToApi(projectId, currentStep, backup);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, currentStep]);

  /**
   * Manually retry saving the current step (used by retry button in UI).
   */
  const retrySave = useCallback(() => {
    if (!projectId) return;
    const data = formData[currentStep];
    if (data !== undefined) {
      syncToApi(projectId, currentStep, data);
    }
  }, [projectId, currentStep, formData, syncToApi]);

  return {
    isDirty,
    isAutoSaving,
    autoSaveError,
    triggerAutoSave,
    retrySave,
  };
}
