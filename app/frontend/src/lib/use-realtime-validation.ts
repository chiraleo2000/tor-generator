"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { ValidationFinding, ValidationResult } from "@/types";
import { unwrapData } from "@/lib/api-unwrap";

const VALIDATION_DEBOUNCE_MS = 3000;

export interface RealtimeValidationState {
  /** Whether validation is currently in progress */
  isValidating: boolean;
  /** The latest validation result (null if not yet validated) */
  result: ValidationResult | null;
  /** Findings grouped by the section being edited */
  findings: ValidationFinding[];
  /** Quality score from last validation */
  qualityScore: number | null;
  /** Whether the last validation showed the content as valid */
  isValid: boolean | null;
  /** Error message if validation request failed */
  error: string | null;
}

/**
 * Custom hook that provides real-time validation feedback with 3-second debounce.
 *
 * After 3 seconds of no input changes, calls POST /api/v1/projects/{id}/validate
 * with the section_key and content being edited.
 *
 * Returns validation findings that can be displayed inline with the section.
 *
 * Requirements: 10.6
 */
export function useRealtimeValidation(projectId: string | null) {
  const [state, setState] = useState<RealtimeValidationState>({
    isValidating: false,
    result: null,
    findings: [],
    qualityScore: null,
    isValid: null,
    error: null,
  });

  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const isMountedRef = useRef(true);

  // Track the latest request to avoid stale updates
  const requestIdRef = useRef(0);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      // Cleanup pending timers and requests
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  /**
   * Perform the actual validation API call.
   */
  const performValidation = useCallback(
    async (sectionKey: string, content: string, reqId: number) => {
      if (!projectId || !isMountedRef.current) return;

      // Abort any previous in-flight request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      const controller = new AbortController();
      abortControllerRef.current = controller;

      setState((prev) => ({ ...prev, isValidating: true, error: null }));

      try {
        const response = await apiClient.post<ValidationResult>(
          `/projects/${projectId}/validate`,
          { section_key: sectionKey, content },
          { signal: controller.signal }
        );

        // Ignore stale responses
        if (!isMountedRef.current || reqId !== requestIdRef.current) return;

        const data = unwrapData<ValidationResult>(response);
        setState({
          isValidating: false,
          result: data,
          findings: data.findings || [],
          qualityScore: data.quality_score,
          isValid: data.is_valid,
          error: null,
        });
      } catch (err: unknown) {
        // Ignore aborted requests
        if (err instanceof Error && err.name === "AbortError") return;
        if (!isMountedRef.current || reqId !== requestIdRef.current) return;

        setState((prev) => ({
          ...prev,
          isValidating: false,
          error: "ไม่สามารถตรวจสอบเนื้อหาได้ กรุณาลองใหม่",
        }));
      }
    },
    [projectId]
  );

  /**
   * Trigger debounced validation for a section.
   * Call this whenever the user edits section content.
   *
   * @param sectionKey - The TOR section key being edited (e.g., "s1", "s2")
   * @param content - The current content of the section
   */
  const validate = useCallback(
    (sectionKey: string, content: string) => {
      // Clear any pending debounce timer
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }

      // Increment request ID to track latest
      const reqId = ++requestIdRef.current;

      // Set new 3-second debounce timer
      debounceTimerRef.current = setTimeout(() => {
        performValidation(sectionKey, content, reqId);
      }, VALIDATION_DEBOUNCE_MS);
    },
    [performValidation]
  );

  /**
   * Cancel any pending validation (e.g., when user navigates away).
   */
  const cancelValidation = useCallback(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setState((prev) => ({ ...prev, isValidating: false }));
  }, []);

  /**
   * Clear all validation state (e.g., when switching sections).
   */
  const clearValidation = useCallback(() => {
    cancelValidation();
    setState({
      isValidating: false,
      result: null,
      findings: [],
      qualityScore: null,
      isValid: null,
      error: null,
    });
  }, [cancelValidation]);

  return {
    ...state,
    validate,
    cancelValidation,
    clearValidation,
  };
}
