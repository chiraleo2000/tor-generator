"use client";

import { useEffect, useState } from "react";

/** In-progress sentence plus a rising elapsed count, so a long wait is visibly alive. */
export function elapsedStatusText(base: string, seconds: number): string {
  const stem = base.replace(/\s*\.{3}\s*$/, "").replace(/…\s*$/, "").trim();
  if (seconds < 1) return base;
  return `${stem}... ผ่านมา ${seconds} วินาที`;
}

export function useElapsedStatus(active: boolean, base: string): string {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    if (!active) {
      setSeconds(0);
      return undefined;
    }
    const started = Date.now();
    const id = window.setInterval(() => {
      setSeconds(Math.max(1, Math.round((Date.now() - started) / 1000)));
    }, 1000);
    return () => window.clearInterval(id);
  }, [active, base]);

  if (!active) return base;
  return elapsedStatusText(base, seconds);
}
