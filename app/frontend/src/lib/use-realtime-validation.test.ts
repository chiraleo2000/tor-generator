import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useRealtimeValidation } from "./use-realtime-validation";

// Mock the api-client
vi.mock("@/lib/api-client", () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

import { apiClient } from "@/lib/api-client";

const mockPost = apiClient.post as ReturnType<typeof vi.fn>;

describe("useRealtimeValidation", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockPost.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("should initialize with default state", () => {
    const { result } = renderHook(() => useRealtimeValidation("project-1"));

    expect(result.current.isValidating).toBe(false);
    expect(result.current.result).toBeNull();
    expect(result.current.findings).toEqual([]);
    expect(result.current.qualityScore).toBeNull();
    expect(result.current.isValid).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("should not call API before 3 seconds debounce", () => {
    const { result } = renderHook(() => useRealtimeValidation("project-1"));

    act(() => {
      result.current.validate("s1", "test content");
    });

    // Advance timer by 2 seconds — should NOT have called API yet
    act(() => {
      vi.advanceTimersByTime(2000);
    });

    expect(mockPost).not.toHaveBeenCalled();
  });

  it("should call API after 3 seconds debounce", async () => {
    mockPost.mockResolvedValue({
      data: {
        quality_score: 85,
        is_valid: true,
        findings: [],
      },
    });

    const { result } = renderHook(() => useRealtimeValidation("project-1"));

    act(() => {
      result.current.validate("s2", "เนื้อหาทดสอบ");
    });

    // Advance timer past debounce
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });

    expect(mockPost).toHaveBeenCalledWith(
      "/projects/project-1/validate",
      { section_key: "s2", content: "เนื้อหาทดสอบ" },
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
  });

  it("should debounce multiple rapid calls (only last fires)", async () => {
    mockPost.mockResolvedValue({
      data: {
        quality_score: 75,
        is_valid: true,
        findings: [],
      },
    });

    const { result } = renderHook(() => useRealtimeValidation("project-1"));

    // Simulate rapid typing
    act(() => {
      result.current.validate("s1", "a");
    });
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    act(() => {
      result.current.validate("s1", "ab");
    });
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    act(() => {
      result.current.validate("s1", "abc");
    });

    // Advance past debounce from last call
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });

    // Should only have been called once with the last content
    expect(mockPost).toHaveBeenCalledTimes(1);
    expect(mockPost).toHaveBeenCalledWith(
      "/projects/project-1/validate",
      { section_key: "s1", content: "abc" },
      expect.anything()
    );
  });

  it("should update state with validation results", async () => {
    const mockFindings = [
      {
        severity: "warning" as const,
        rule_violated: "LEGAL_001",
        affected_section: "s2",
        message: "ควรอ้างอิง พ.ร.บ. 2560",
        recommended_correction: "เพิ่มการอ้างอิง พ.ร.บ. การจัดซื้อจัดจ้างฯ 2560",
      },
    ];

    mockPost.mockResolvedValue({
      data: {
        quality_score: 62,
        is_valid: false,
        findings: mockFindings,
      },
    });

    const { result } = renderHook(() => useRealtimeValidation("project-1"));

    act(() => {
      result.current.validate("s2", "เนื้อหาที่ต้องตรวจสอบ");
    });

    await act(async () => {
      vi.advanceTimersByTime(3000);
    });

    expect(result.current.qualityScore).toBe(62);
    expect(result.current.isValid).toBe(false);
    expect(result.current.findings).toEqual(mockFindings);
    expect(result.current.isValidating).toBe(false);
  });

  it("should handle API errors gracefully", async () => {
    mockPost.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useRealtimeValidation("project-1"));

    act(() => {
      result.current.validate("s1", "test");
    });

    await act(async () => {
      vi.advanceTimersByTime(3000);
    });

    expect(result.current.error).toBe("ไม่สามารถตรวจสอบเนื้อหาได้ กรุณาลองใหม่");
    expect(result.current.isValidating).toBe(false);
  });

  it("should not call API when projectId is null", () => {
    const { result } = renderHook(() => useRealtimeValidation(null));

    act(() => {
      result.current.validate("s1", "test content");
    });

    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(mockPost).not.toHaveBeenCalled();
  });

  it("should clear validation state when clearValidation is called", async () => {
    mockPost.mockResolvedValue({
      data: {
        quality_score: 80,
        is_valid: true,
        findings: [
          {
            severity: "suggestion",
            rule_violated: "FORMAT_001",
            affected_section: "s1",
            message: "ควรเพิ่มเลขลำดับ",
            recommended_correction: "ใช้เลขลำดับตามรูปแบบราชการ",
          },
        ],
      },
    });

    const { result } = renderHook(() => useRealtimeValidation("project-1"));

    act(() => {
      result.current.validate("s1", "some content");
    });

    await act(async () => {
      vi.advanceTimersByTime(3000);
    });

    // Verify we have results
    expect(result.current.findings).toHaveLength(1);

    // Clear
    act(() => {
      result.current.clearValidation();
    });

    expect(result.current.findings).toEqual([]);
    expect(result.current.qualityScore).toBeNull();
    expect(result.current.isValid).toBeNull();
    expect(result.current.result).toBeNull();
  });

  it("should cancel pending validation when cancelValidation is called", () => {
    const { result } = renderHook(() => useRealtimeValidation("project-1"));

    act(() => {
      result.current.validate("s1", "content");
    });

    act(() => {
      result.current.cancelValidation();
    });

    // Advance past debounce — should NOT call API since canceled
    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(mockPost).not.toHaveBeenCalled();
    expect(result.current.isValidating).toBe(false);
  });
});
