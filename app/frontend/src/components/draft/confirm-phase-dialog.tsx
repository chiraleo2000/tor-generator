"use client";

import { useCallback, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export const PHASE_FORWARD_CONFIRM: Record<number, string> = {
  1: "ยืนยันเริ่มวิเคราะห์เอกสาร?",
  3: "ข้อมูลครบถ้วนแล้ว ยืนยันเริ่มร่าง TOR?",
  4: "ยืนยันส่งเข้าทบทวน?",
};

export function ConfirmPhaseDialog({
  open,
  title,
  onOpenChange,
  onConfirm,
}: Readonly<{
  open: boolean;
  title: string;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
}>) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <div data-testid="confirm-phase-dialog">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            data-testid="confirm-phase-cancel"
            onClick={() => onOpenChange(false)}
          >
            ยกเลิก
          </Button>
          <Button type="button" data-testid="confirm-phase-ok" onClick={onConfirm}>
            ยืนยัน
          </Button>
        </DialogFooter>
      </div>
    </Dialog>
  );
}

export function useConfirmPhase() {
  const [message, setMessage] = useState<string | null>(null);
  const resolver = useRef<((ok: boolean) => void) | null>(null);

  const close = useCallback((ok: boolean) => {
    resolver.current?.(ok);
    resolver.current = null;
    setMessage(null);
  }, []);

  const ask = useCallback((text: string) => {
    return new Promise<boolean>((resolve) => {
      resolver.current = resolve;
      setMessage(text);
    });
  }, []);

  const dialog = (
    <ConfirmPhaseDialog
      open={message !== null}
      title={message || ""}
      onOpenChange={(open) => {
        if (!open) close(false);
      }}
      onConfirm={() => close(true)}
    />
  );

  return { ask, dialog };
}
