import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useRowKeys } from "./use-row-keys";

describe("useRowKeys", () => {
  it("grows keys when the list length increases", () => {
    const { result, rerender } = renderHook(
      ({ length }: { length: number }) => useRowKeys(length),
      { initialProps: { length: 2 } }
    );
    expect(result.current.keys).toHaveLength(2);
    const first = result.current.keys[0];
    rerender({ length: 3 });
    expect(result.current.keys).toHaveLength(3);
    expect(result.current.keys[0]).toBe(first);
  });

  it("keeps remaining keys after removeAt", () => {
    const { result } = renderHook(() => useRowKeys(3));
    const kept = result.current.keys[1];
    act(() => {
      result.current.removeAt(0);
    });
    expect(result.current.keys[0]).toBe(kept);
  });

  it("shrinks keys when the list length decreases", () => {
    const { result, rerender } = renderHook(
      ({ length }: { length: number }) => useRowKeys(length),
      { initialProps: { length: 4 } }
    );
    expect(result.current.keys).toHaveLength(4);
    rerender({ length: 2 });
    expect(result.current.keys).toHaveLength(2);
  });
});
