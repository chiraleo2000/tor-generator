"use client";

import { useRef } from "react";

let keySeq = 0;

function newKey(): string {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }
  keySeq += 1;
  return `row-${Date.now()}-${keySeq}`;
}

/** Stable React keys for editable lists, independent of array index. */
export function useRowKeys(length: number): {
  keys: string[];
  removeAt: (index: number) => void;
} {
  const keysRef = useRef<string[]>([]);
  while (keysRef.current.length < length) {
    keysRef.current.push(newKey());
  }
  if (keysRef.current.length > length) {
    keysRef.current = keysRef.current.slice(0, length);
  }
  return {
    keys: keysRef.current,
    removeAt: (index: number) => {
      keysRef.current.splice(index, 1);
    },
  };
}
